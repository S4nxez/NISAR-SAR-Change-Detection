"""Synthetic part of the benchmark: radar scenes whose answer is known, run through the whole method.

The scene is a set of horizontal lanes on a 20 m UTM grid (like a GCOV product over Tefé). A wide river with the
hub runs along the west edge; in every lane a channel leaves the river eastwards and ends in a small lake with one
community. Each lane tests one thing (LANES). The backscatter of every surface (SURFACES, HH and HV in dB) is an
assumption taken from L-band literature for the Amazon floodplain (see docs/river-monitor-benchmark.md); speckle is
gamma distributed with the number of looks of the exam.

The scene is written as cached granule windows (analysis.radar.save_window) and the method runs through
pipeline.update as it would on a real pass: whatever the current checkout does (filter, threshold, classes,
routes) is what gets scored.
"""
import contextlib
import json
import os
import tempfile

import numpy as np

from lifeline import pipeline
from lifeline.analysis.radar import save_window, window_cache_path
from lifeline.benchmark.scoring import grade, unpack_layers
from lifeline.geometry.area import area_mask, load_area
from lifeline.output.catalog import pass_dir

EPSG = 32720                       # UTM 20S, the projection of the GCOV products over Tefé
PIXEL_M = 20.0
SURFACES = {                       # mean HH, HV backscatter (dB)
    "forest": (-7.0, -12.5),
    "water": (-23.0, -30.0),
    "wind": (-13.0, -26.0),        # wind-roughened open water
    "flooded_vegetation": (-1.0, -9.5),   # double bounce: brighter HH than dry forest, HV only a little brighter
    "mud": (-17.0, -27.0),         # smooth wet mud or sand bar
}
SURFACE_CODE = {name: i for i, name in enumerate(SURFACES)}
WATER_SURFACES = ("water", "wind")  # open water a boat can use
# name, expected status (scoring.grade), channel width (m), shape, obstacle across the channel or None
LANES = [
    ("channel_20m", "narrow", 20, "straight", None),
    ("channel_40m", "narrow", 40, "straight", None),
    ("channel_60m", "connected", 60, "straight", None),
    ("channel_100m", "connected", 100, "straight", None),
    ("channel_200m", "connected", 200, "straight", None),
    ("zigzag_100m", "connected", 100, "zigzag", None),
    ("vegetation_block", "isolated", 200, "straight", "flooded_vegetation"),
    ("mud_bar", "isolated", 200, "straight", "mud"),
    ("wind_stretch", "connected", 200, "straight", "wind"),
    ("channel_400m", "connected", 400, "straight", None),
]
LANE_M = 600.0
MARGIN_M = 300.0
RIVER = (100.0, 700.0)             # x range of the river from the west edge (m)
CHANNEL = (700.0, 3700.0)          # x range of every channel
LAKE = (3700.0, 4300.0, 200.0)     # x range and half height of every lake
COMMUNITY_X = 4000.0
OBSTACLES = {"flooded_vegetation": (1800.0, 2200.0), "mud": (1850.0, 2150.0), "wind": (1600.0, 2400.0)}
ZIGZAG_STEP = 300.0                # 45 degree legs of 300 m


def scene_size():
    """(width_m, height_m) of the scene."""
    return LAKE[1] + 300.0, 2 * MARGIN_M + LANE_M * len(LANES)


def lane_centre(i):
    """y of lane i, metres south of the north edge."""
    return MARGIN_M + LANE_M * (i + 0.5)


def segment_distance(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    t = np.clip(((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy), 0.0, 1.0)
    return np.hypot(px - (ax + t * dx), py - (ay + t * dy))


def zigzag_points(yc):
    xs = np.arange(CHANNEL[0], CHANNEL[1] + ZIGZAG_STEP, ZIGZAG_STEP)
    ys = yc + np.where(np.arange(len(xs)) % 2 == 0, -ZIGZAG_STEP / 2, ZIGZAG_STEP / 2)
    return list(zip(xs, ys, strict=True))


def surfaces_at(e, s):
    """Surface code at points e metres east of the west edge and s metres south of the north edge."""
    out = np.full(np.shape(e), SURFACE_CODE["forest"], np.uint8)
    out[(e >= RIVER[0]) & (e < RIVER[1])] = SURFACE_CODE["water"]
    for i, (_, _, width, shape, obstacle) in enumerate(LANES):
        yc = lane_centre(i)
        if shape == "straight":
            channel = (e >= CHANNEL[0] - PIXEL_M) & (e < CHANNEL[1]) & (np.abs(s - yc) <= width / 2)
        else:
            pts = zigzag_points(yc)
            d = np.min([segment_distance(e, s, *a, *b) for a, b in zip(pts[:-1], pts[1:], strict=True)], axis=0)
            channel = (d <= width / 2) & (e >= CHANNEL[0] - PIXEL_M) & (e < CHANNEL[1] + width)
        out[channel] = SURFACE_CODE["water"]
        out[(e >= LAKE[0]) & (e < LAKE[1]) & (np.abs(s - yc) <= LAKE[2])] = SURFACE_CODE["water"]
        if obstacle:
            a, b = OBSTACLES[obstacle]
            out[channel & (e >= a) & (e < b)] = SURFACE_CODE[obstacle]
    return out


def speckled(mean_db, looks, rng):
    """Linear power with gamma speckle of `looks` looks around the mean (dB)."""
    mean = np.power(10.0, mean_db / 10.0)
    return (rng.gamma(looks, 1.0 / looks, size=mean.shape) * mean).astype(np.float32)


def scene_area(base_area, origin_lonlat):
    """The synthetic area: the method parameters of base_area (thresholds, widths, filter, any rule the checkout
    reads from the area file) on a box that covers the scene, with its own hub, river and a short access radius
    (lanes are only LANE_M apart)."""
    from pyproj import Transformer
    to_ll = Transformer.from_crs(EPSG, 4326, always_xy=True)
    to_xy = Transformer.from_crs(4326, EPSG, always_xy=True)
    x0, y0 = to_xy.transform(*origin_lonlat)
    w, h = scene_size()
    lon0, lat1 = origin_lonlat
    lon1, _ = to_ll.transform(x0 + w, y0)
    _, lat0 = to_ll.transform(x0, y0 - h)
    hub_lon, hub_lat = to_ll.transform(x0 + sum(RIVER) / 2, y0 - h / 2)
    keep = {k: v for k, v in base_area.items() if k not in ("circle", "gauge", "nx", "ny", "px_m", "bbox")}
    keep.update(id="synthetic", name="Synthetic lanes", bbox=[lon0, round(lat0, 6), round(lon1, 6), lat1],
                hub={"name": "Hub", "lon": hub_lon, "lat": hub_lat, "radius_m": 250},
                river={"name": "River", "lon": hub_lon, "lat": hub_lat, "radius_m": 250},
                access_radius_m=150, access_snap_m={"default": 0}, communities="synthetic_communities.geojson")
    return keep, (x0, y0)


def communities_geojson(origin_xy):
    from pyproj import Transformer
    to_ll = Transformer.from_crs(EPSG, 4326, always_xy=True)
    x0, y0 = origin_xy
    feats = []
    for i, (name, *_rest) in enumerate(LANES):
        lon, lat = to_ll.transform(x0 + COMMUNITY_X, y0 - lane_centre(i))
        feats.append({"type": "Feature", "properties": {"id": name, "name": name, "place": "hamlet"},
                      "geometry": {"type": "Point", "coordinates": [lon, lat]}})
    return {"type": "FeatureCollection", "features": feats}


def product_window(origin_xy, looks, seed):
    """A cached-window dict of the scene with speckle, on a 20 m grid that covers the scene plus 1 km."""
    x0, y0 = origin_xy
    w, h = scene_size()
    pad = 1000.0
    xs = np.arange(x0 - pad, x0 + w + pad, PIXEL_M) + PIXEL_M / 2
    ys = np.arange(y0 + pad, y0 - h - pad, -PIXEL_M) - PIXEL_M / 2
    e, s = np.meshgrid(xs - x0, y0 - ys)
    codes = surfaces_at(e, s)
    hh_db = np.array([v[0] for v in SURFACES.values()], np.float32)[codes]
    hv_db = np.array([v[1] for v in SURFACES.values()], np.float32)[codes]
    rng = np.random.default_rng(seed)
    return {"epsg": EPSG, "x0": float(xs[0]), "y0": float(ys[0]), "dx": PIXEL_M, "dy": -PIXEL_M, "mb": 0.0,
            "bands": {"HHHH": speckled(hh_db, looks, rng), "HVHV": speckled(hv_db, looks, rng)}}


def truth_on_grid(area, origin_xy):
    """Surface code of every pixel of the area grid."""
    from pyproj import Transformer
    to_xy = Transformer.from_crs(4326, EPSG, always_xy=True)
    lon0, _, _, lat1 = area["bbox"]
    step = area["step_deg"]
    lon, lat = np.meshgrid(lon0 + (np.arange(area["nx"]) + 0.5) * step, lat1 - (np.arange(area["ny"]) + 0.5) * step)
    x, y = to_xy.transform(lon, lat)
    return surfaces_at(x - origin_xy[0], origin_xy[1] - y)


class InlineExecutor:
    """ProcessPoolExecutor stand-in that runs the jobs in this process (the scene is small)."""

    def __init__(self, max_workers=1):
        self.max_workers = max_workers

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def map(self, fn, jobs):
        return map(fn, jobs)


@contextlib.contextmanager
def environment(**values):
    old = {k: os.environ.get(k) for k in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def surface_scores(truth, layers, in_area):
    """Per surface: pixels, share mapped as water and, when the method has the layer, as vegetated water."""
    out = {}
    for name, code in SURFACE_CODE.items():
        m = in_area & (truth == code)
        n = int(m.sum())
        row = {"pixels": n, "as_water": round(float(layers["water"][m].mean()), 4) if n else None}
        if "vegetated" in layers:
            row["as_vegetated_water"] = round(float(layers["vegetated"][m].mean()), 4) if n else None
        out[name] = row
    return out


def run(base_area, looks, seeds, origin_lonlat=(-64.80, -3.40), workdir=None):
    """Run the method on the synthetic scene once per seed and grade it. Returns the synthetic section of the report."""
    with tempfile.TemporaryDirectory(prefix="lifeline-synthetic-", dir=workdir) as tmp:
        area_def, origin_xy = scene_area(base_area, origin_lonlat)
        areas, out, cache = (os.path.join(tmp, d) for d in ("areas", "out", "cache"))
        os.makedirs(areas)
        with open(os.path.join(areas, "synthetic.json"), "w", encoding="utf-8") as f:
            json.dump(area_def, f)
        with open(os.path.join(areas, area_def["communities"]), "w", encoding="utf-8") as f:
            json.dump(communities_geojson(origin_xy), f)
        area = load_area("synthetic", areas)
        passes = {}
        for k, seed in enumerate(seeds):
            pid = f"2026-01-{k + 1:02d}_t001A"
            g = {"name": f"SYNTHETIC_{seed}.h5", "url": f"synthetic://SYNTHETIC_{seed}.h5"}
            save_window(window_cache_path(area, g, cache), product_window(origin_xy, looks, seed))
            passes[pid] = {"id": pid, "date": pid[:10], "time_utc": "10:00", "track": 1, "direction": "ascending",
                           "frames": [1], "modes": ["synthetic"], "beta": False, "granules": [g]}
        with environment(MONITOR_CACHE_DIR=cache):
            cat = pipeline.update(area, workers=1, out_root=out, areas_dir=areas, search=lambda a: passes,
                                  token=lambda: "synthetic", executor=InlineExecutor)
        truth = truth_on_grid(area, origin_xy)
        in_area = area_mask(area)
        lanes = {name: {"expected": exp, "grades": {}} for name, exp, *_ in LANES}
        surfaces = []
        for p in cat["passes"]:
            layers = unpack_layers(os.path.join(pass_dir(area, p["id"], out), "water.npz"))
            surfaces.append(surface_scores(truth, layers, in_area))
            for name, exp, *_ in LANES:
                code = (p.get("status") or {}).get(name, [0])[0]
                g = grade(exp, code)
                lanes[name]["grades"][g] = lanes[name]["grades"].get(g, 0) + 1
    totals = {"correct": 0, "conservative": 0, "dangerous": 0, "no_data": 0}
    for lane in lanes.values():
        for g, n in lane["grades"].items():
            totals[g] += n
    graded = sum(totals.values())
    surface_mean = {}
    for name in SURFACES:
        rows = [s[name] for s in surfaces if s[name]["pixels"]]
        surface_mean[name] = ({k: round(float(np.mean([r[k] for r in rows])), 4) for k in rows[0] if k != "pixels"}
                              if rows else {})
    return {"looks": looks, "seeds": list(seeds), "surfaces_db": {k: list(v) for k, v in SURFACES.items()},
            "lanes": lanes, "totals": totals,
            "correct_share": round(totals["correct"] / graded, 4) if graded else None,
            "surfaces": surface_mean}


