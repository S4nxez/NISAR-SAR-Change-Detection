"""catalog.json, the record the backend serves to the web page (api/monitor/areas/<area>): schema
version, area, grid, communities and one entry per pass.

A pass entry holds its water statistics and, when the pass covers enough of the area, the status
of every community ([status code, bottleneck_m, distance_to_water_m]). Counts and the community
classes are then derived from the whole record (classify_communities).
"""
import json
import os
from itertools import pairwise

from scipy import ndimage

from lifeline.analysis.water import connectivity, wide_water
from lifeline.config import OUT_ROOT, SCHEMA_VERSION, STATUS, STATUS_NAME
from lifeline.geometry.area import area_mask, to_px
from lifeline.output.layers import load_mask, save_change

AREA_KEYS = ("id", "name", "country", "bbox", "circle", "hub", "river", "access_radius_m", "safe_width_m",
             "widths_m", "water_db", "vegetated_water", "low_water")
SOURCES = {"radar": "NISAR L2 GCOV (NASA/ISRO), ASF DAAC", "places": "© OpenStreetMap contributors (ODbL)"}
CLASSES = ("monitored", "unresolved", "inland", "no_data")
LINKED = (STATUS["connected"], STATUS["at_risk"])


def area_dir(area, out_root=OUT_ROOT):
    return os.path.join(out_root, area["id"])


def pass_dir(area, pass_id, out_root=OUT_ROOT):
    return os.path.join(area_dir(area, out_root), "passes", pass_id)


def catalog_path(area, out_root=OUT_ROOT):
    return os.path.join(area_dir(area, out_root), "catalog.json")


def load_catalog(area, communities, out_root=OUT_ROOT):
    """The stored catalog (or an empty one) with the area, grid and communities refreshed."""
    path = catalog_path(area, out_root)
    cat = {"passes": []}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            cat = json.load(f)
    lon0, lat0, lon1, lat1 = area["bbox"]
    cat.update(schema_version=SCHEMA_VERSION,
               area={k: area[k] for k in AREA_KEYS if k in area},
               grid={"nx": area["nx"], "ny": area["ny"], "step_deg": area["step_deg"],
                     "pixel_m": round(area["px_m"], 1), "bounds": [[lat0, lon0], [lat1, lon1]]},
               communities=communities,
               status_codes={str(code): name for code, name in STATUS_NAME.items()},
               sources=dict(SOURCES))
    return cat


def pass_order(p):
    return p["date"], p["time_utc"]


def save_catalog(area, cat, out_root=OUT_ROOT):
    """Write catalog.json atomically (the web page may read it at any time), passes in time order."""
    cat["passes"].sort(key=pass_order)
    path = catalog_path(area, out_root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cat, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, path)


def wide_water_of(area, water):
    """Water of the channels at least the area's safe width wide."""
    inside_m = ndimage.distance_transform_edt(water) * area["px_m"]
    return wide_water(water, inside_m, area["safe_width_m"], area["px_m"])


def hub_target(area):
    """(row, col, radius_m) of the hub town, at its water access when it has one."""
    hub = area["hub"]
    at = hub.get("access") or hub
    return (*to_px(area, at["lon"], at["lat"]), hub["radius_m"])


def hold_unverified(results, strict):
    """Statuses of routes that need unverified water (analysis.water.low_water_route): a community connected with
    that water but not without it is at risk, never connected. Returns (results, indices of the communities whose
    route needs the unverified water)."""
    out, held = [], []
    for i, (r, s) in enumerate(zip(results, strict, strict=True)):
        if r[0] in LINKED and s[0] != r[0]:
            held.append(i)
            if r[0] == STATUS["connected"]:
                r = [STATUS["at_risk"], *r[1:]]
        out.append(r)
    return out, held


def evaluate(area, communities, water, valid, wide, entry, route_water=None, unverified=None):
    """Water statistics and community status of one pass (fills `entry`). Routes run over `route_water` when given
    (the water left by the low-water rule, analysis.water.low_water_route), else over all the water. A route that
    needs `unverified` water is at most at risk; those communities are listed in entry["unverified_route"]."""
    px_m = area["px_m"]
    pix_km2 = (px_m / 1000.0) ** 2
    in_mask = area_mask(area)
    coverage = float(valid[in_mask].mean())
    entry.update(water_km2=round(float(water.sum()) * pix_km2, 2),
                 narrow_km2=round(float((water & ~wide).sum()) * pix_km2, 2),
                 coverage=round(coverage, 4),
                 shown=coverage >= area.get("min_coverage_shown", 0.0),
                 evaluated=coverage >= area["min_coverage"])
    for k in ("status", "hub_link", "counts", "unverified_route"):
        entry.pop(k, None)
    if not entry["evaluated"]:
        return
    hub, river = hub_target(area), area["river"]
    # route and distance to water are measured from where people reach the water (see places.assign_access)
    targets = [to_px(area, *(c.get("access") or (c["lon"], c["lat"]))) for c in communities]
    route = water if route_water is None else route_water
    res = connectivity(route, valid, px_m, hub, targets, area["widths_m"],
                       area["access_radius_m"], area["safe_width_m"], in_mask)
    if unverified is not None and unverified.any():
        strict = connectivity(route & ~unverified, valid, px_m, hub, targets, area["widths_m"],
                              area["access_radius_m"], area["safe_width_m"], in_mask)
        res, held = hold_unverified(res, strict)
        if held:
            entry["unverified_route"] = [communities[i]["id"] for i in held]
    entry["hub_link"] = connectivity(route, valid, px_m, hub, [to_px(area, river["lon"], river["lat"])],
                                     area["widths_m"], river["radius_m"], area["safe_width_m"], in_mask)[0]
    entry["status"] = {c["id"]: r for c, r in zip(communities, res, strict=True)}
    entry["counts"] = {k: 0 for k in STATUS}
    for r in res:
        entry["counts"][STATUS_NAME[r[0]]] += 1


def community_class(rows, access_radius_m):
    """Class of a community from its results on every evaluated pass (see classify_communities)."""
    rows = [r for r in rows if r and r[0] != STATUS["no_data"]]
    if not rows:
        return "no_data"
    if min(r[2] for r in rows) > access_radius_m:
        return "inland"
    # never linked through a channel the radar resolves (>= the narrowest width level):
    # one-pixel creeks come and go between passes, so they cannot carry an alarm
    if not any(r[0] in LINKED and r[1] for r in rows):
        return "unresolved"
    return "monitored"


def classify_communities(area, cat):
    """
    Use the whole record to decide which communities the radar can actually monitor:
      inland      no water within access_radius_m on any pass (not river-dependent)
      unresolved  water nearby but never linked to the hub through a channel of at least the
                  narrowest width level on any pass: its channels are narrower than the radar
                  resolves reliably, so "isolated" would be a false alarm
      monitored   linked to the hub that way on at least one pass; isolation means a lost link
    Per-pass counts are then taken over monitored communities only. A community missing from a
    pass (added to the list after the pass was processed) counts as no data on it.
    """
    evaluated = sorted((p for p in cat["passes"] if p.get("evaluated") and p.get("status")), key=pass_order)
    for c in cat["communities"]:
        c["class"] = community_class([p["status"].get(c["id"]) for p in evaluated], area["access_radius_m"])
    monitored = sorted(c["id"] for c in cat["communities"] if c["class"] == "monitored")
    # A single image can be spoiled by wind or rain on the water, so isolation is only confirmed
    # when the previous evaluated pass with data for that community also showed it isolated.
    # Until then it counts as at risk and is listed in the pass's "unconfirmed".
    last = {}
    for p in evaluated:
        counts = {k: 0 for k in STATUS}
        p["unconfirmed"] = []
        for cid in monitored:
            code = (p["status"].get(cid) or [STATUS["no_data"]])[0]
            if code == STATUS["isolated"] and last.get(cid) != STATUS["isolated"]:
                p["unconfirmed"].append(cid)
                counts["at_risk"] += 1
            else:
                counts[STATUS_NAME[code]] += 1
            if code != STATUS["no_data"]:
                last[cid] = code
        p["counts"] = counts
    cat["community_classes"] = {k: sum(c["class"] == k for c in cat["communities"]) for k in CLASSES}


def refresh_changes(area, cat, out_root=OUT_ROOT):
    """change.png for every shown pass against the previous shown pass of the same track."""
    by_track = {}
    for p in sorted(cat["passes"], key=lambda p: p["date"]):
        if p.get("shown", True):
            by_track.setdefault(p["track"], []).append(p)
    pix_km2 = (area["px_m"] / 1000.0) ** 2
    for seq in by_track.values():
        for prev, cur in pairwise(seq):
            if cur.get("change", {}).get("since") == prev["id"]:
                continue
            a = os.path.join(pass_dir(area, prev["id"], out_root), "water.npz")
            b = os.path.join(pass_dir(area, cur["id"], out_root), "water.npz")
            if not (os.path.exists(a) and os.path.exists(b)):
                continue
            lost, gained = save_change(load_mask(a), load_mask(b),
                                       os.path.join(pass_dir(area, cur["id"], out_root), "change.png"))
            cur["files"]["change"] = "change.png"
            cur["change"] = {"since": prev["id"], "lost_km2": round(lost * pix_km2, 2),
                             "gained_km2": round(gained * pix_km2, 2)}
