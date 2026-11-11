"""Water mask, channel widths and the water route between each community and the hub town."""
import math

import numpy as np
from scipy import ndimage

from lifeline.config import STATUS

MIN_WATER_PX = 25      # 1 ha at 20 m
MIN_HOLE_PX = 50       # 2 ha at 20 m
MIN_COVERAGE_AROUND = 0.8   # share of a community's surroundings a pass must cover to judge it
EIGHT_NEIGHBOURS = np.ones((3, 3))


def water_mask(db, water_db, weak_db=None):
    """
    Water = filtered backscatter below water_db. With weak_db (hysteresis), pixels below weak_db
    also count when they touch that water: wind-roughened stretches of a river or lake return a
    little more echo but stay attached to the calm water around them.
    Specks under MIN_WATER_PX are dropped and holes under MIN_HOLE_PX inside water are filled.
    Returns (water, valid).
    """
    valid = np.isfinite(db)
    water = valid & (db < water_db)
    if weak_db is not None and weak_db > water_db:
        lab, _ = ndimage.label(valid & (db < weak_db))
        keep = np.unique(lab[water])
        water = np.isin(lab, keep[keep > 0])
    lab, n = ndimage.label(water)
    if n:
        size = np.bincount(lab.ravel())
        water &= size[lab] >= MIN_WATER_PX
    holes, n = ndimage.label(~water & valid)
    if n:
        size = np.bincount(holes.ravel())
        small = size < MIN_HOLE_PX
        small[0] = False
        water |= small[holes]
    return water, valid


KI_RANGE_DB = (-35.0, 5.0)
KI_BINS = 400
MIXED_SHARE = (0.2, 0.8)   # a tile is mixed when this share of its pixels is below the prior threshold
MIN_TILE_VALID = 0.9
MAX_POOLED = 2_000_000


def ki_threshold(values, lo=KI_RANGE_DB[0], hi=KI_RANGE_DB[1], bins=KI_BINS):
    """Kittler-Illingworth minimum-error threshold of `values` (dB): each class is modelled as a Gaussian and the cut
    minimises J(t) = 1 + 2 (P1 ln s1 + P2 ln s2) - 2 (P1 ln P1 + P2 ln P2). NaN when no cut leaves two classes."""
    v = values[np.isfinite(values)]
    if v.size < 2:
        return float("nan")
    hist, edges = np.histogram(v, bins=bins, range=(lo, hi))
    x = (edges[:-1] + edges[1:]) / 2
    p = hist / max(1, hist.sum())
    p1 = np.cumsum(p)
    p2 = 1.0 - p1
    m1 = np.cumsum(p * x)
    s1_sq = np.cumsum(p * x * x)
    with np.errstate(divide="ignore", invalid="ignore"):
        mu1, mu2 = m1 / p1, (m1[-1] - m1) / p2
        var1 = s1_sq / p1 - mu1 ** 2
        var2 = (s1_sq[-1] - s1_sq) / p2 - mu2 ** 2
        j = 1 + p1 * np.log(var1) + p2 * np.log(var2) - 2 * (p1 * np.log(p1) + p2 * np.log(p2))
    j[~np.isfinite(j) | (var1 <= 0) | (var2 <= 0)] = np.inf
    if not np.isfinite(j).any():
        return float("nan")
    # an empty gap between the classes gives a plateau of equal J: take its middle, not the edge next to the water
    best = np.flatnonzero(j <= j.min() + 1e-9 * max(1.0, abs(j.min())))
    return float((edges[best[0] + 1] + edges[best[-1] + 1]) / 2)


def mixed_tiles(db, tile_px, prior_db):
    """Slices of the tiles that hold both water and land: valid on at least MIN_TILE_VALID of their pixels and with
    MIXED_SHARE of them below prior_db (their histogram is bimodal, so a threshold can be measured there)."""
    out = []
    for a in range(0, db.shape[0] - tile_px + 1, tile_px):
        for b in range(0, db.shape[1] - tile_px + 1, tile_px):
            t = db[a:a + tile_px, b:b + tile_px]
            ok = np.isfinite(t)
            if ok.mean() < MIN_TILE_VALID:
                continue
            share = float((t[ok] < prior_db).mean())
            if MIXED_SHARE[0] <= share <= MIXED_SHARE[1]:
                out.append((slice(a, a + tile_px), slice(b, b + tile_px)))
    return out


def pass_thresholds(area, db):
    """(strong_db, weak_db, info) of one pass. Fixed (water_db, water_db_weak) unless the area has
    "water_db_adaptive" {range_db, tile_m, min_tiles}: then the Kittler-Illingworth threshold of the pixels of the
    mixed tiles (split-based selection, Martinis et al. 2009), clamped to range_db, with the weak threshold kept at
    the same offset. Too few mixed tiles: the fixed threshold."""
    strong, weak = area["water_db"], area.get("water_db_weak")
    cfg = area.get("water_db_adaptive")
    if not cfg:
        return strong, weak, {"source": "fixed", "strong_db": strong, "weak_db": weak}
    tiles = mixed_tiles(db, max(8, int(round(cfg["tile_m"] / area["px_m"]))), strong)
    info = {"source": "fixed", "tiles": len(tiles)}
    if len(tiles) >= cfg["min_tiles"]:
        pooled = np.concatenate([db[t][np.isfinite(db[t])] for t in tiles])
        if pooled.size > MAX_POOLED:
            pooled = pooled[:: pooled.size // MAX_POOLED + 1]
        t = ki_threshold(pooled)
        if np.isfinite(t):
            lo, hi = cfg["range_db"]
            info.update(source="adaptive", measured_db=round(t, 2))
            offset = None if weak is None else weak - strong
            strong = float(np.clip(t, lo, hi))
            weak = None if offset is None else strong + offset
    info.update(strong_db=round(strong, 2), weak_db=None if weak is None else round(weak, 2))
    return strong, weak, info


def disk(radius_px):
    """Boolean disc of the given radius (pixels), centred in a (2r+1) x (2r+1) array."""
    r = int(math.ceil(radius_px))
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    return (yy * yy + xx * xx) <= radius_px * radius_px


def near_labels(labels, row, col, radius_px):
    """Non-zero labels within radius_px of (row, col)."""
    k = disk(radius_px)
    r = k.shape[0] // 2
    a0, b0 = max(0, row - r), max(0, col - r)
    a1, b1 = min(labels.shape[0], row + r + 1), min(labels.shape[1], col + r + 1)
    if a1 <= a0 or b1 <= b0:
        return set()
    win = labels[a0:a1, b0:b1]
    kk = k[a0 - (row - r):a1 - (row - r), b0 - (col - r):b1 - (col - r)]
    v = win[kk]
    return set(np.unique(v[v > 0]).tolist())


def width_mask(water, inside_m, width_m, px_m):
    """Pixels on the centre line of channels at least width_m wide (width 0: all water).
    A channel whose centre line is e pixels from the shore is at least (2e - 1) pixels wide."""
    return water if width_m == 0 else inside_m >= (width_m + px_m) / 2.0


def hub_labels(labels, hub, px_m):
    """Labels of the water around the hub; hub is (row, col, radius_m)."""
    row, col, radius_m = hub
    return near_labels(labels, row, col, radius_m / px_m)


def undetermined_targets(water, gaps, px_m, hub, targets, access_m):
    """Where the pass has gaps, a route might run through the missing part: the targets linked
    only when the gaps are assumed to be water cannot be called isolated."""
    if not gaps.any():
        return set()
    labels, _ = ndimage.label(water | gaps)
    hub_l = hub_labels(labels, hub, px_m)
    return {i for i, (r, c) in enumerate(targets) if near_labels(labels, r, c, access_m / px_m) & hub_l}


def bottlenecks(water, inside_m, px_m, hub, targets, widths, access_m):
    """For each target, the widest width in [0] + widths that still links it to the hub
    (-1 = not linked). A target can only pass a width if it passed the narrower one."""
    linked = [-1] * len(targets)
    prev = -1
    for w in [0] + list(widths):
        # one-pixel creeks often run diagonally: at the "any water" level, corner contacts count
        labels, _ = ndimage.label(width_mask(water, inside_m, w, px_m),
                                  structure=EIGHT_NEIGHBOURS if w == 0 else None)
        hub_l = hub_labels(labels, hub, px_m)
        if not hub_l:
            break   # the hub is off the water at this width: no wider level can link anything
        for i, (r, c) in enumerate(targets):
            if linked[i] == prev and near_labels(labels, r, c, access_m / px_m) & hub_l:
                linked[i] = w
        prev = w
    return linked


def coverage_around(valid, in_mask, row, col, win):
    """Share of valid pixels of the area within win pixels of (row, col); None outside the grid."""
    if not (0 <= row < valid.shape[0] and 0 <= col < valid.shape[1]):
        return None
    a0, b0 = max(0, row - win), max(0, col - win)
    window = (slice(a0, row + win + 1), slice(b0, col + win + 1))
    cover = valid[window][in_mask[window]]
    return float(cover.mean()) if cover.size else None


def route_status(bottleneck, distance_m, undetermined, access_m, safe_m):
    """[status, bottleneck_m, distance_to_water_m] of a target the pass covers."""
    d = int(round(distance_m))
    if bottleneck < 0 and undetermined and distance_m <= access_m:
        return [STATUS["no_data"], None, d]
    if bottleneck < 0 or distance_m > access_m:
        status = "isolated"
    elif bottleneck >= safe_m:
        status = "connected"
    else:
        status = "at_risk"
    return [STATUS[status], None if bottleneck < 0 else int(bottleneck), d]


def connectivity(water, valid, px_m, hub, targets, widths, access_m, safe_m, in_area_mask=None):
    """
    For each target (row, col): [status, bottleneck_m, distance_to_water_m].
    hub is (row, col, radius_m). bottleneck_m is the widest channel width in `widths` that still
    links the target to the hub (0 = linked only through channels narrower than widths[0],
    None = not linked). in_area_mask marks the pixels that belong to the area: pixels outside it
    (the corners of a circular area) are not data gaps.
    """
    in_mask = np.ones_like(valid) if in_area_mask is None else in_area_mask
    inside_m = ndimage.distance_transform_edt(water) * px_m
    to_water_m = ndimage.distance_transform_edt(~water) * px_m
    maybe = undetermined_targets(water, ~valid & in_mask, px_m, hub, targets, access_m)
    linked = bottlenecks(water, inside_m, px_m, hub, targets, widths, access_m)
    win = int(access_m / px_m)
    out = []
    for i, (r, c) in enumerate(targets):
        cover = coverage_around(valid, in_mask, r, c, win)
        if cover is None or cover < MIN_COVERAGE_AROUND:
            out.append([STATUS["no_data"], None, None])
        else:
            out.append(route_status(linked[i], float(to_water_m[r, c]), i in maybe, access_m, safe_m))
    return out


def wide_water(water, inside_m, safe_m, px_m):
    """Water pixels that belong to channels at least safe_m wide."""
    core = inside_m >= (safe_m + px_m) / 2.0
    return water & ndimage.binary_dilation(core, structure=disk(safe_m / 2.0 / px_m + 1))
