"""Why the method and the reference disagree, and which disagreements a person has to look at.

Two levels:

- **Pixels**: every pixel where the NISAR water mask and the reference consensus disagree gets the first cause, in a
  fixed order, whose rule it meets (see CAUSES). Commission = NISAR water on reference land; omission = reference
  water NISAR misses.
- **Cases**: every community and pass whose status differs from the reference. The pixels responsible are the
  fewest disputed pixels a route has to cross (`bridge_pixels`): for a route the reference does not have, the NISAR
  water pixels the reference calls land that the cheapest route between the hub and the community uses; for a route
  NISAR misses, the reference water pixels NISAR calls land. The case takes the most common cause of those pixels,
  a location (their centre) and links to look at it in the Copernicus Browser.

The rules are evidence, not proof: the cases flagged `review` are the ones a person has to check (docs/
river-monitor-benchmark.md, "Manual review").
"""
import math

import numpy as np
from scipy import ndimage

from lifeline.analysis.water import EIGHT_NEIGHBOURS, disk, width_mask
from lifeline.benchmark.consensus import shore_band
from lifeline.benchmark.scoring import LINKED, width_strata
from lifeline.benchmark.static_layers import NO_DATA, optical_blind
from lifeline.config import STATUS

FOUR_NEIGHBOURS = ndimage.generate_binary_structure(2, 1)

FAMILIES = {
    "reference": "the reference itself may be wrong",
    "timing": "the river changed between the pass and the reference",
    "processing": "a step of our processing",
    "resolution": "the 20 m grid cannot resolve it",
    "radar_physics": "L-band radar sees the surface differently from optical sensors",
    "unexplained": "no rule explains it",
}

# (cause, family, needs a person, applies to commission, applies to omission, meaning); the order is the priority
CAUSES = [
    ("cloud_edge", "reference", True, True, True,
     "near a cloud or cloud shadow of the Sentinel-2 scene: the optical reference may be wrong"),
    ("river_level_change", "timing", False, True, True,
     "seasonal ground, and the river level changed between the pass and the reference date"),
    ("swath_edge", "processing", True, True, True,
     "near the edge of the NISAR swath or a data gap"),
    ("narrow_channel", "resolution", False, False, True,
     "reference channel narrower than 60 m"),
    ("shore_mixed_pixel", "resolution", False, True, True,
     "within one pixel of the shore: a 20 m pixel holds both water and land"),
    ("vegetation", "radar_physics", False, False, True,
     "plants on the water (NISAR vegetated class, DSWx-S1 inundated vegetation or a WorldCover wetland): "
     "L-band double bounce, not open water"),
    ("threshold", "processing", False, True, True,
     "backscatter within the margin of the water threshold: a small change of threshold flips it"),
    ("smooth_ground", "radar_physics", True, True, False,
     "seasonal ground (bank, mud, sand) clearly dark in L-band"),
    ("wind_roughness", "radar_physics", False, False, True,
     "permanent water clearly brighter than the threshold: wind or rain roughens it"),
    ("unexplained", "unexplained", True, True, True, "no rule explains it"),
]
CODE = {c[0]: i + 1 for i, c in enumerate(CAUSES)}
NAME = {i + 1: c[0] for i, c in enumerate(CAUSES)}
FAMILY = {c[0]: c[1] for c in CAUSES}
NEEDS_REVIEW = {c[0]: c[2] for c in CAUSES}
MEANING = {c[0]: c[5] for c in CAUSES}

COPERNICUS_BROWSER = "https://browser.dataspace.copernicus.eu/"
SITE_MERGE_M = 1500     # cases whose culprit pixels lie closer than this are one site to look at
DANGEROUS = ("false_route", "overconfident")


def _distance_m(mask, px_m):
    """Distance (m) of every pixel to the nearest pixel of mask (inf when mask is empty)."""
    if not mask.any():
        return np.full(mask.shape, np.inf)
    return ndimage.distance_transform_edt(~mask) * px_m


def conditions(ctx, rules, px_m):
    """Boolean maps of every rule (lazy: a rule whose inputs are missing is all False)."""
    shape = ctx["ref_water"].shape
    none = np.zeros(shape, bool)
    occ = ctx.get("occurrence")
    known_occ = none if occ is None else occ != NO_DATA
    s0, s1 = rules["seasonal_occurrence"]
    seasonal = none if occ is None else known_occ & (occ >= s0) & (occ < s1)
    permanent = none if occ is None else known_occ & (occ >= rules["permanent_occurrence"])
    cloudy = ctx.get("cloudy")
    level = ctx.get("level_change_cm")
    gaps = ~ctx["nisar_valid"] & ctx["in_area"]
    hh = ctx.get("hh")
    strong = ctx["strong_db"]
    weak = ctx.get("weak_db")
    weak = strong if weak is None else weak
    margin = rules["threshold_margin_db"]
    veg = none.copy()
    for k in ("vegetated", "s1_vegetated"):
        if ctx.get(k) is not None:
            veg |= ctx[k]
    if ctx.get("worldcover") is not None:
        veg |= optical_blind(ctx["worldcover"])
    with np.errstate(invalid="ignore"):
        return {
            "cloud_edge": none if cloudy is None else _distance_m(cloudy, px_m) <= rules["cloud_near_m"],
            "river_level_change": none if level is None or abs(level) < rules["level_change_cm"] else seasonal,
            "swath_edge": _distance_m(gaps, px_m) <= rules["swath_edge_m"],
            "shore_mixed_pixel": shore_band(ctx["ref_water"], ctx["ref_known"], rules["mixed_px"]),
            "narrow_channel": width_strata(ctx["ref_water"], px_m)["narrow_lt60m"],
            "vegetation": veg,
            "threshold_commission": none if hh is None else hh >= strong - margin,
            "threshold_omission": none if hh is None else hh < weak + margin,
            "smooth_ground": seasonal,
            "wind_roughness": none if hh is None else permanent & (hh >= weak + margin),
        }


def pixel_causes(kind, mask, cond):
    """Cause code of every pixel of `mask` (0 elsewhere). kind: "commission" or "omission"."""
    codes = np.zeros(mask.shape, np.uint8)
    left = mask.copy()
    for name, _, _, com, om, _ in CAUSES:
        if not left.any():
            break
        if (kind == "commission" and not com) or (kind == "omission" and not om):
            continue
        if name == "unexplained":
            rule = left
        elif name == "threshold":
            rule = cond["threshold_commission" if kind == "commission" else "threshold_omission"]
        else:
            rule = cond[name]
        hit = left & rule
        codes[hit] = CODE[name]
        left &= ~hit
    return codes


def cause_counts(codes):
    """{cause: pixels} of a code map, causes with no pixel left out."""
    n = np.bincount(codes.ravel(), minlength=len(CAUSES) + 1)
    return {NAME[i]: int(n[i]) for i in range(1, len(CAUSES) + 1) if n[i]}


def by_family(counts):
    out = {}
    for name, n in counts.items():
        out[FAMILY[name]] = out.get(FAMILY[name], 0) + n
    return out


def _box(mask, pad=1):
    rows = np.flatnonzero(mask.any(1))
    cols = np.flatnonzero(mask.any(0))
    return (slice(max(0, rows[0] - pad), min(mask.shape[0], rows[-1] + pad + 1)),
            slice(max(0, cols[0] - pad), min(mask.shape[1], cols[-1] + pad + 1)))


def _dilate(mask, structure):
    """Binary dilation computed only around the mask's pixels (the arrays are large, the fronts small)."""
    out = np.zeros_like(mask)
    if mask.any():
        box = _box(mask)
        out[box] = ndimage.binary_dilation(mask[box], structure)
    return out


def bridge_pixels(path, free, starts, ends, structure=EIGHT_NEIGHBOURS, max_px=250):
    """The fewest non-free pixels a route through `path` must cross from `starts` to `ends` (0-1 breadth-first
    search: free pixels cost nothing, the others one each). Returns that set of pixels (bool array; empty when a
    free route exists), or None when no route exists or it needs more than max_px of them."""
    st = np.asarray(structure, bool)
    free = free & path
    ends = ends & path
    frontier = starts & path
    if not ends.any() or not frontier.any():
        return None
    lab, _ = ndimage.label(free, st)
    level = np.full(path.shape, -1, np.int32)
    reached = np.zeros(path.shape, bool)
    k = 0
    while True:
        touch = (frontier | _dilate(frontier, st)) & free & ~reached
        ids = np.unique(lab[touch])
        ids = ids[ids > 0]
        if ids.size:
            frontier = frontier | (np.isin(lab, ids) & ~reached)
        level[frontier] = k
        reached |= frontier
        if (reached & ends).any():
            break
        k += 1
        if k > max_px:
            return None
        frontier = _dilate(frontier, st) & path & ~reached & ~free
        if not frontier.any():
            return None
    culprits = np.zeros(path.shape, bool)
    hit = np.flatnonzero((reached & ends).ravel())
    cur = np.unravel_index(hit[np.argmin(level.ravel()[hit])], path.shape)
    while level[cur] > 0:
        k = level[cur]
        same = level == k
        box = _box(same)
        lab_k, _ = ndimage.label(same[box], st)
        region = np.zeros(path.shape, bool)
        region[box] = lab_k == lab_k[cur[0] - box[0].start, cur[1] - box[1].start]
        seeds = region & ~free
        cand = seeds & _dilate(level == k - 1, st)
        pick = np.flatnonzero((cand if cand.any() else seeds).ravel())[0]
        s = np.unravel_index(pick, path.shape)
        culprits[s] = True
        r0, c0 = s
        nbr = None
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                r, c = r0 + dr, c0 + dc
                if (dr or dc) and st[dr + 1, dc + 1] and 0 <= r < path.shape[0] and 0 <= c < path.shape[1] \
                        and 0 <= level[r, c] < k and (nbr is None or level[r, c] > level[nbr]):
                    nbr = (r, c)
        if nbr is None:   # cannot happen for a pixel reached at level k > 0; stop rather than loop
            break
        cur = nbr
    return culprits


def disk_mask(shape, row, col, radius_px):
    out = np.zeros(shape, bool)
    k = disk(radius_px)
    r = k.shape[0] // 2
    a0, b0 = max(0, row - r), max(0, col - r)
    a1, b1 = min(shape[0], row + r + 1), min(shape[1], col + r + 1)
    if a1 > a0 and b1 > b0:
        out[a0:a1, b0:b1] = k[a0 - (row - r):a1 - (row - r), b0 - (col - r):b1 - (col - r)]
    return out


def case_kind(pred, ref):
    """Kind of a status disagreement (codes as in STATUS), or None when they agree."""
    if pred == ref:
        return None
    if pred in LINKED and ref == STATUS["isolated"]:
        return "false_route"
    if pred == STATUS["isolated"] and ref in LINKED:
        return "false_isolated"
    if pred == STATUS["connected"] and ref == STATUS["at_risk"]:
        return "overconfident"
    return "underconfident"


def case_masks(kind, nisar, ref, px_m, safe_m):
    """(path, free, structure, pixel kind) of the route search behind one kind of case."""
    if kind == "false_route":
        return nisar, nisar & ref, EIGHT_NEIGHBOURS, "commission"
    if kind == "false_isolated":
        return ref, ref & nisar, EIGHT_NEIGHBOURS, "omission"
    inside_n = ndimage.distance_transform_edt(nisar) * px_m
    inside_r = ndimage.distance_transform_edt(ref) * px_m
    wide_n, wide_r = width_mask(nisar, inside_n, safe_m, px_m), width_mask(ref, inside_r, safe_m, px_m)
    if kind == "overconfident":
        return wide_n, wide_n & wide_r, FOUR_NEIGHBOURS, "commission"
    return wide_r, wide_r & wide_n, FOUR_NEIGHBOURS, "omission"


def pixel_lonlat(area, row, col):
    lon0, _, _, lat1 = area["bbox"]
    return lon0 + (col + 0.5) * area["step_deg"], lat1 - (row + 0.5) * area["step_deg"]


def explain_case(kind, culprits, nisar, ref, cond):
    """(cause, {cause: pixels}) of one case from its culprit pixels."""
    if culprits is None:
        return "unexplained", {}
    if not culprits.any():
        # the route exists without disputed pixels at this width: the width rule decides it
        return "narrow_channel", {}
    pkind = "commission" if kind in ("false_route", "overconfident") else "omission"
    disputed = culprits & ((nisar & ~ref) if pkind == "commission" else (ref & ~nisar))
    if not disputed.any():
        return "narrow_channel", {"narrow_channel": int(culprits.sum())}
    counts = cause_counts(pixel_causes(pkind, disputed, cond))
    return max(counts.items(), key=lambda kv: (kv[1], -CODE[kv[0]]))[0], counts


def copernicus_link(lon, lat, date, dataset, layer=None, zoom=15):
    """Copernicus Browser (free; an account unlocks more tools) at a place and date."""
    url = (f"{COPERNICUS_BROWSER}?zoom={zoom}&lat={lat:.5f}&lng={lon:.5f}&themeId=DEFAULT-THEME"
           f"&datasetId={dataset}&fromTime={date}T00%3A00%3A00.000Z&toTime={date}T23%3A59%3A59.999Z")
    return url + (f"&layerId={layer}" if layer else "")


def review_links(lon, lat, s2_date, s1_date=None):
    links = {"sentinel2": copernicus_link(lon, lat, s2_date, "S2_L2A_CDAS", "1_TRUE_COLOR"),
             "openstreetmap": f"https://www.openstreetmap.org/?mlat={lat:.5f}&mlon={lon:.5f}#map=15/{lat:.5f}/{lon:.5f}"}
    if s1_date:
        links["sentinel1"] = copernicus_link(lon, lat, s1_date, "S1_CDAS_IW_VVVH")
    return links


def distance_m(lon0, lat0, lon1, lat1):
    """Ground distance (m) between two nearby points (equirectangular: exact enough within an area)."""
    kx = 111320.0 * math.cos(math.radians((lat0 + lat1) / 2))
    return math.hypot((lon1 - lon0) * kx, (lat1 - lat0) * 110540.0)


def nearest_community(lon, lat, communities):
    """(name, distance in m) of the community closest to a point."""
    best = None
    for c in communities:
        clon, clat = c.get("access") or (c["lon"], c["lat"])
        d = distance_m(lon, lat, clon, clat)
        if best is None or d < best[1]:
            best = (c.get("name", c["id"]), d)
    return best or (None, None)


def sites(found, communities, merge_m=SITE_MERGE_M):
    """Cases grouped into the places to look at: cases of the same side (dangerous: false route or overconfident;
    safe: false isolated or underconfident) whose culprit locations are within merge_m of one another (single
    linkage). Each site is named after the nearest community, lists every community and pass it explains and
    keeps the links of each pass. Sorted with the sites that need a person first, then by size."""
    groups = []
    for c in found:
        side = "dangerous" if c["kind"] in DANGEROUS else "safe"
        hits = [g for g in groups if g["side"] == side and
                any(distance_m(c["lon"], c["lat"], o["lon"], o["lat"]) <= merge_m for o in g["cases"])]
        merged = {"side": side, "cases": [c]}
        for g in hits:
            merged["cases"] += g["cases"]
            groups.remove(g)
        groups.append(merged)
    out = []
    for g in groups:
        cs = g["cases"]
        lon = sum(c["lon"] for c in cs) / len(cs)
        lat = sum(c["lat"] for c in cs) / len(cs)
        name, d = nearest_community(lon, lat, communities)
        cause_n = {}
        for c in cs:
            cause_n[c["cause"]] = cause_n.get(c["cause"], 0) + 1
        cause = max(cause_n.items(), key=lambda kv: (kv[1], -CODE.get(kv[0], 99)))[0]
        by_pass = {}
        for c in cs:
            by_pass.setdefault(c["pass"], c["links"])
        out.append({"near": name, "distance_km": None if d is None else round(d / 1000, 1),
                    "lon": round(lon, 5), "lat": round(lat, 5), "side": g["side"],
                    "kinds": sorted({c["kind"] for c in cs}), "cause": cause, "family": FAMILY.get(cause, "unexplained"),
                    "communities": sorted({c["community"] for c in cs}),
                    "community_ids": sorted({c["community_id"] for c in cs}),
                    "passes": sorted(by_pass), "links": by_pass, "cases": len(cs),
                    "review": any(c["review"] for c in cs),
                    "verdicts": sorted({(c.get("reviewed") or {}).get("verdict") for c in cs} - {None})})
    return sorted(out, key=lambda s: (not s["review"], s["side"] != "dangerous", -s["cases"]))


def cases(area, communities, pred, ref_status, nisar, ref_water, cond, targets, hub, s2_date, s1_date=None,
          max_px=250):
    """Every community whose decided reference status differs from the method's, explained."""
    out = []
    starts = disk_mask(nisar.shape, hub[0], hub[1], hub[2] / area["px_m"])
    access_px = area["access_radius_m"] / area["px_m"]
    masks = {}
    for c, (row, col) in zip(communities, targets, strict=True):
        a, b = pred.get(c["id"]), ref_status.get(c["id"])
        if not a or not b or STATUS["no_data"] in (a[0], b[0]):
            continue
        if all(r[2] is not None and r[2] > area["access_radius_m"] for r in (a, b)):
            continue   # inland in both
        kind = case_kind(a[0], b[0])
        if kind is None:
            continue
        if kind not in masks:
            masks[kind] = case_masks(kind, nisar, ref_water, area["px_m"], area["safe_width_m"])
        path, free, st, _ = masks[kind]
        culprits = bridge_pixels(path, free, starts, disk_mask(nisar.shape, row, col, access_px), st, max_px)
        cause, counts = explain_case(kind, culprits, nisar, ref_water, cond)
        if culprits is not None and culprits.any():
            rr, cc = np.nonzero(culprits)
            lon, lat = pixel_lonlat(area, int(round(rr.mean())), int(round(cc.mean())))
        else:
            lon, lat = c.get("access") or (c["lon"], c["lat"])
        out.append({"community_id": c["id"], "community": c.get("name", c["id"]), "kind": kind,
                    "status": a[0], "reference_status": b[0], "cause": cause, "family": FAMILY[cause],
                    "causes": counts, "culprit_px": None if culprits is None else int(culprits.sum()),
                    "lon": round(lon, 5), "lat": round(lat, 5),
                    "review": kind == "false_route" or NEEDS_REVIEW[cause],
                    "links": review_links(lon, lat, s2_date, s1_date)})
    return out
