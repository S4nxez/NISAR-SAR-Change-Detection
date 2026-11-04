"""
River lifeline monitor.

Tracks, pass by pass, whether riverside communities keep a water connection to their hub
town, using NISAR L2 GCOV radar backscatter. Radar sees water through clouds and smoke,
and L-band reaches water under the forest canopy.

  python processing/river_monitor.py communities [--area tefe]   fetch places from OpenStreetMap
  python processing/river_monitor.py update [--area tefe] [--workers 2] [--limit N] [--redo]
  python processing/river_monitor.py reevaluate [--area tefe]   recompute status from stored masks
  python processing/river_monitor.py watch [--area tefe] [--hours 6]

Data access: NISAR GCOV products from the ASF DAAC. Searching needs no account; reading
needs a NASA Earthdata user token in the EARTHDATA_TOKEN environment variable (on Windows
the user-level variable is also read from the registry, so no restart is needed). Only the
area of interest is read from each remote product with HTTP range requests, never the
whole ~2 GB file.

Method, for every pass (all frames of one track on one day, mosaicked):
  1. HH backscatter is speckle-filtered (~100 m window) and resampled to a fixed lon/lat
     grid (~20 m) shared by all passes.
  2. Water = filtered HH below WATER_DB (smooth water reflects the radar pulse away).
     Specks under 1 ha are dropped and holes under 2 ha inside water are filled.
  3. For every channel width W in widths_m, the water mask is reduced to the pixels at
     least W/2 from the shore; a community is connected at width W when, within
     access_radius_m of it, one of those pixels belongs to the same component as the
     water around the hub. Its bottleneck is the widest W that still connects it.
  4. Status: connected (bottleneck >= safe_width_m), at_risk (connected, narrower),
     isolated (no water path, or no water within access_radius_m), no_data.

Output (frontend/public/data/monitor/<area>/):
  catalog.json               area, grid, communities and one entry per pass
  passes/<id>/radar.webp     HH backscatter preview (40 m)
  passes/<id>/water.png      water mask; channels narrower than safe_width_m in amber
  passes/<id>/change.png     water lost / gained since the previous pass of the same track
  passes/<id>/water.npz      packed water mask and validity (input of the change layer)
"""
import argparse
import concurrent.futures as cf
import datetime as dt
import io
import json
import math
import os
import sys
import time
import traceback

import numpy as np
import requests
from PIL import Image
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nisar_comun import filtrar_speckle, lineal_a_db, reducir  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
AREAS = os.path.join(HERE, "areas")
OUT_ROOT = os.path.join(ROOT, "frontend", "public", "data", "monitor")

ASF_SEARCH = "https://api.daac.asf.alaska.edu/services/search/param"
OVERPASS = "https://overpass-api.de/api/interpreter"
USER_AGENT = "nisar-river-monitor/0.1 (NASA Space Apps 2026 prototype)"
GRID = "science/LSAR/GCOV/grids"

STATUS = {"no_data": 0, "connected": 1, "at_risk": 2, "isolated": 3}
MIN_WATER_PX = 25      # 1 ha at 20 m
MIN_HOLE_PX = 50       # 2 ha at 20 m
BLOCK = 4 * 1024 * 1024


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


# ---------------------------------------------------------------- area and grid
def load_area(area_id):
    with open(os.path.join(AREAS, area_id + ".json"), encoding="utf-8") as f:
        area = json.load(f)
    lon0, lat0, lon1, lat1 = area["bbox"]
    step = area["step_deg"]
    area["nx"] = int(round((lon1 - lon0) / step))
    area["ny"] = int(round((lat1 - lat0) / step))
    lat_mid = math.radians((lat0 + lat1) / 2)
    area["px_m"] = step * 111320.0 * math.sqrt(math.cos(lat_mid))  # geometric mean of x and y size
    return area


def to_px(area, lon, lat):
    """lon/lat -> (row, col) on the area grid (row 0 at the north edge)."""
    lon0, _, _, lat1 = area["bbox"]
    return int((lat1 - lat) / area["step_deg"]), int((lon - lon0) / area["step_deg"])


def area_wkt(area):
    lon0, lat0, lon1, lat1 = area["bbox"]
    return f"POLYGON(({lon0} {lat0},{lon1} {lat0},{lon1} {lat1},{lon0} {lat1},{lon0} {lat0}))"


# ---------------------------------------------------------------- credentials and remote files
def earthdata_token():
    tok = os.environ.get("EARTHDATA_TOKEN", "").strip()
    if not tok and os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                tok = str(winreg.QueryValueEx(k, "EARTHDATA_TOKEN")[0]).strip()
        except OSError:
            tok = ""
    if not tok:
        raise SystemExit("EARTHDATA_TOKEN is not set: create a token at https://urs.earthdata.nasa.gov "
                         "(Generate Token) and store it in that environment variable.")
    return tok


class RemoteFile(io.RawIOBase):
    """Seekable read-only view of a remote file through HTTP range requests (block cache)."""

    def __init__(self, url, token):
        self.src, self.token = url, token
        self.s = requests.Session()
        self.s.headers["User-Agent"] = USER_AGENT
        self.pos, self.cache, self.bytes = 0, {}, 0
        self._sign()

    def _sign(self):
        r = self.s.get(self.src, headers={"Range": "bytes=0-0", "Authorization": "Bearer " + self.token},
                       timeout=90)
        if r.status_code in (401, 403):
            raise PermissionError(f"Earthdata refused the token (HTTP {r.status_code}); "
                                  "check that it has not expired.")
        r.raise_for_status()
        self.url = r.url  # signed CDN location of the product
        self.size = int(r.headers["Content-Range"].split("/")[1])

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else self.pos + off if whence == 1 else self.size + off
        return self.pos

    def _block(self, i):
        if i in self.cache:
            return self.cache[i]
        a, b = i * BLOCK, min(self.size, (i + 1) * BLOCK) - 1
        for attempt in range(5):
            try:
                r = self.s.get(self.url, headers={"Range": f"bytes={a}-{b}"}, timeout=180)
                if r.status_code in (401, 403):  # signed URL expired
                    self._sign()
                    continue
                r.raise_for_status()
                if len(r.content) != b - a + 1:
                    raise IOError("short read")
                self.cache[i] = r.content
                self.bytes += len(r.content)
                return r.content
            except (requests.RequestException, IOError):
                if attempt == 4:
                    raise
                time.sleep(2 + 3 * attempt)

    def readinto(self, buf):
        n = min(len(buf), self.size - self.pos)
        out, done = memoryview(buf), 0
        while done < n:
            i, off = divmod(self.pos + done, BLOCK)
            blk = self._block(i)
            k = min(n - done, len(blk) - off)
            out[done:done + k] = blk[off:off + k]
            done += k
        self.pos += n
        return n


# ---------------------------------------------------------------- search
def parse_name(name):
    """NISAR_L2_PR_GCOV_033_161_A_176_2005_DHDH_A_20261023T100258_... -> fields."""
    p = name.split("_")
    return {"cycle": int(p[4]), "track": int(p[5]), "direction": p[6], "frame": int(p[7]),
            "mode": p[8], "pol": p[9], "start": dt.datetime.strptime(p[11], "%Y%m%dT%H%M%S")}


def mode_rank(g):
    m = g["mode"]
    if m[:2] == "00":
        return None  # no 20/40 MHz frequency A: only the coarse 5 MHz band
    return (0 if g["collection"].endswith("PROVISIONAL_V1") else 1,
            {"20": 0, "40": 1}.get(m[:2], 2), 0 if g["pol"] in ("DHDH", "SHSH") else 1)


def search(area):
    """All GCOV passes over the area: {pass_id: {date, track, direction, granules[]}}."""
    params = {"dataset": "NISAR", "processingLevel": "GCOV", "output": "geojson",
              "maxResults": "5000", "intersectsWith": area_wkt(area)}
    r = requests.get(ASF_SEARCH, params=params, timeout=180, headers={"User-Agent": USER_AGENT})
    r.raise_for_status()
    best = {}
    for feat in r.json().get("features", []):
        p = feat["properties"]
        name = p["fileName"]
        if not name.endswith(".h5"):
            continue
        g = parse_name(name)
        g.update(name=name, url=p["url"], collection=p["collectionName"])
        rank = mode_rank(g)
        if rank is None:
            continue
        key = (g["start"].date(), g["track"], g["frame"])
        if key not in best or rank < best[key][0]:
            best[key] = (rank, g)
    passes = {}
    for (day, track, _), (_, g) in best.items():
        pid = f"{day.isoformat()}_t{track:03d}{g['direction']}"
        ps = passes.setdefault(pid, {"id": pid, "date": day.isoformat(), "track": track,
                                     "direction": "ascending" if g["direction"] == "A" else "descending",
                                     "granules": []})
        ps["granules"].append(g)
    for ps in passes.values():
        ps["granules"].sort(key=lambda g: g["frame"])
        ps["time_utc"] = ps["granules"][0]["start"].strftime("%H:%M")
        ps["frames"] = [g["frame"] for g in ps["granules"]]
        ps["modes"] = sorted({g["mode"] + "_" + g["pol"] for g in ps["granules"]})
        ps["beta"] = any("BETA" in g["collection"] for g in ps["granules"])
    return passes


# ---------------------------------------------------------------- reading one pass
def read_pass(area, ps, token):
    """HH backscatter (dB, speckle-filtered) of a pass on the area grid; NaN = no data."""
    from pyproj import Transformer
    import h5py

    ny, nx, step = area["ny"], area["nx"], area["step_deg"]
    lon0, lat0, lon1, lat1 = area["bbox"]
    out = np.full((ny, nx), np.nan, np.float32)
    lons = lon0 + (np.arange(nx) + 0.5) * step
    edge_lon = np.concatenate([np.linspace(lon0, lon1, 50), np.full(50, lon1), np.linspace(lon1, lon0, 50), np.full(50, lon0)])
    edge_lat = np.concatenate([np.full(50, lat0), np.linspace(lat0, lat1, 50), np.full(50, lat1), np.linspace(lat1, lat0, 50)])
    read_mb, spacing = 0.0, None
    for g in ps["granules"]:
        rf = RemoteFile(g["url"], token)
        with h5py.File(rf, "r") as f:
            fa = f[GRID + "/frequencyA"]
            if "HHHH" not in fa:
                continue
            epsg = int(fa["projection"][()])
            xs, ys = fa["xCoordinates"][()], fa["yCoordinates"][()]
            dx, dy = float(xs[1] - xs[0]), float(ys[1] - ys[0])
            tr = Transformer.from_crs(4326, epsg, always_xy=True)
            ex, ey = tr.transform(edge_lon, edge_lat)
            pad = 8 * abs(dx)
            c0 = max(0, int(np.floor((min(ex) - pad - xs[0]) / dx)))
            c1 = min(len(xs), int(np.ceil((max(ex) + pad - xs[0]) / dx)) + 1)
            r0 = max(0, int(np.floor((max(ey) + pad - ys[0]) / dy)))
            r1 = min(len(ys), int(np.ceil((min(ey) - pad - ys[0]) / dy)) + 1)
            if c1 - c0 < 10 or r1 - r0 < 10:
                continue
            hh = fa["HHHH"][r0:r1, c0:c1]
        read_mb += rf.bytes / 1e6
        spacing = abs(dx)
        k = max(3, int(round(area.get("speckle_m", 100.0) / abs(dx))) | 1)
        db = filtrar_speckle(lineal_a_db(hh), k)
        del hh
        for a in range(0, ny, 256):
            b = min(ny, a + 256)
            lats = lat1 - (np.arange(a, b) + 0.5) * step
            lo, la = np.meshgrid(lons, lats)
            x, y = tr.transform(lo, la)
            ci = np.rint((x - xs[c0]) / dx).astype(np.int64)
            ri = np.rint((y - ys[r0]) / dy).astype(np.int64)
            ok = (ci >= 0) & (ci < db.shape[1]) & (ri >= 0) & (ri < db.shape[0])
            v = np.full(ci.shape, np.nan, np.float32)
            v[ok] = db[ri[ok], ci[ok]]
            blk = out[a:b]
            fill = np.isnan(blk) & np.isfinite(v)
            blk[fill] = v[fill]
    return out, read_mb, spacing


# ---------------------------------------------------------------- water and connectivity
def water_mask(db, water_db, weak_db=None):
    """
    Water = filtered backscatter below water_db. With weak_db (hysteresis), pixels below weak_db
    also count when they touch that water: wind-roughened stretches of a river or lake return a
    little more echo but stay attached to the calm water around them.
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
        small = (size < MIN_HOLE_PX)
        small[0] = False
        water |= small[holes]
    return water, valid


def disk(radius_px):
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


def connectivity(water, valid, px_m, hub, targets, widths, access_m, safe_m):
    """
    For each target (row, col): [status, bottleneck_m, distance_to_water_m].
    bottleneck_m is the widest channel width in `widths` that still links the target to the
    hub (0 = linked only through channels narrower than widths[0], -1 = not linked).
    """
    inside = ndimage.distance_transform_edt(water) * px_m
    to_water = ndimage.distance_transform_edt(~water) * px_m
    hub_r, hub_c, hub_rad = hub
    # Where the pass has gaps, a route might run through the missing part: targets linked only
    # when the gaps are assumed to be water are undetermined, not isolated.
    maybe = set()
    if not valid.all():
        labels, _ = ndimage.label(water | ~valid)
        hub_l = near_labels(labels, hub_r, hub_c, hub_rad / px_m)
        maybe = {i for i, (r, c) in enumerate(targets) if near_labels(labels, r, c, access_m / px_m) & hub_l}
    linked = [-1] * len(targets)
    prev = -1
    for w in [0] + list(widths):
        # a channel whose centre line is e pixels from the shore is at least (2e - 1) pixels wide
        mask = water if w == 0 else inside >= (w + px_m) / 2.0
        labels, _ = ndimage.label(mask)
        hub_l = near_labels(labels, hub_r, hub_c, hub_rad / px_m)
        if not hub_l:
            break
        for i, (r, c) in enumerate(targets):
            # a target can only pass a width if it passed the narrower one
            if linked[i] == prev and near_labels(labels, r, c, access_m / px_m) & hub_l:
                linked[i] = w
        prev = w
    out = []
    win = int(access_m / px_m)
    for i, (r, c) in enumerate(targets):
        a0, b0 = max(0, r - win), max(0, c - win)
        cover = valid[a0:r + win + 1, b0:c + win + 1]
        if not (0 <= r < water.shape[0] and 0 <= c < water.shape[1]) or cover.size == 0 or cover.mean() < 0.8:
            out.append([STATUS["no_data"], None, None])
            continue
        d = float(to_water[r, c])
        b = linked[i]
        if b < 0 and i in maybe and d <= access_m:
            out.append([STATUS["no_data"], None, int(round(d))])
            continue
        if b < 0 or d > access_m:
            st = "isolated"
        elif b >= safe_m:
            st = "connected"
        else:
            st = "at_risk"
        out.append([STATUS[st], None if b < 0 else int(b), int(round(d))])
    return out


# ---------------------------------------------------------------- rendering
def save_radar(db, path):
    small = reducir(db, 2)
    ok = np.isfinite(small)
    g = (np.clip((np.nan_to_num(small, nan=-25.0) + 25.0) / 25.0, 0, 1) * 255).astype(np.uint8)
    Image.fromarray(np.dstack([g, ok.astype(np.uint8) * 255]), "LA").convert("RGBA").save(path, "WEBP", quality=78)


def wide_water(water, inside, safe_m, px_m):
    """Water pixels that belong to channels at least safe_m wide."""
    core = inside >= (safe_m + px_m) / 2.0
    return water & ndimage.binary_dilation(core, structure=disk(safe_m / 2.0 / px_m + 1))


def save_water(water, wide, path):
    idx = np.zeros(water.shape, np.uint8)
    idx[water] = 2
    idx[wide] = 1
    img = Image.fromarray(idx, "P")
    img.putpalette([0, 0, 0, 61, 139, 255, 255, 176, 32] + [0] * (256 * 3 - 9))
    img.save(path, transparency=0, optimize=True)


def save_change(prev, cur, path):
    pw, pv = prev
    cw, cv = cur
    both = pv & cv
    idx = np.zeros(cw.shape, np.uint8)
    idx[both & pw & ~cw] = 1   # water lost
    idx[both & ~pw & cw] = 2   # water gained
    img = Image.fromarray(idx, "P")
    img.putpalette([0, 0, 0, 228, 119, 89, 104, 214, 230] + [0] * (256 * 3 - 9))
    img.save(path, transparency=0, optimize=True)
    return int((idx == 1).sum()), int((idx == 2).sum())


def load_mask(path):
    z = np.load(path)
    shape = tuple(z["shape"])
    n = shape[0] * shape[1]
    return (np.unpackbits(z["water"])[:n].reshape(shape).astype(bool),
            np.unpackbits(z["valid"])[:n].reshape(shape).astype(bool))


# ---------------------------------------------------------------- one pass end to end
def process_pass(area, communities, ps, out_dir, token):
    t0 = time.time()
    db, read_mb, spacing = read_pass(area, ps, token)
    water, valid = water_mask(db, area["water_db"], area.get("water_db_weak"))
    px_m = area["px_m"]
    coverage = float(valid.mean())
    inside = ndimage.distance_transform_edt(water) * px_m
    wide = wide_water(water, inside, area["safe_width_m"], px_m)
    del inside
    pdir = os.path.join(out_dir, "passes", ps["id"])
    os.makedirs(pdir, exist_ok=True)
    save_radar(db, os.path.join(pdir, "radar.webp"))
    save_water(water, wide, os.path.join(pdir, "water.png"))
    np.savez_compressed(os.path.join(pdir, "water.npz"), shape=np.array(water.shape),
                        water=np.packbits(water), valid=np.packbits(valid))
    entry = {k: ps[k] for k in ("id", "date", "time_utc", "track", "direction", "frames", "modes", "beta")}
    entry.update(coverage=round(coverage, 4), read_mb=round(read_mb, 1), spacing_m=spacing,
                 files={"radar": "radar.webp", "water": "water.png"})
    evaluate(area, communities, water, valid, wide, entry)
    entry["seconds"] = round(time.time() - t0, 1)
    return entry


def evaluate(area, communities, water, valid, wide, entry):
    """Water statistics and community status of one pass (fills `entry`)."""
    px_m = area["px_m"]
    pix_km2 = (px_m / 1000.0) ** 2
    coverage = float(valid.mean())
    entry.update(water_km2=round(float(water.sum()) * pix_km2, 2),
                 narrow_km2=round(float((water & ~wide).sum()) * pix_km2, 2),
                 coverage=round(coverage, 4),
                 shown=coverage >= area.get("min_coverage_shown", 0.0),
                 evaluated=coverage >= area["min_coverage"])
    for k in ("status", "hub_link", "counts"):
        entry.pop(k, None)
    if not entry["evaluated"]:
        return
    hub, river = area["hub"], area["river"]
    hub_px = (*to_px(area, hub["lon"], hub["lat"]), hub["radius_m"])
    targets = [to_px(area, c["lon"], c["lat"]) for c in communities]
    res = connectivity(water, valid, px_m, hub_px, targets, area["widths_m"],
                       area["access_radius_m"], area["safe_width_m"])
    entry["hub_link"] = connectivity(water, valid, px_m, hub_px, [to_px(area, river["lon"], river["lat"])],
                                     area["widths_m"], river["radius_m"], area["safe_width_m"])[0]
    entry["status"] = {c["id"]: r for c, r in zip(communities, res)}
    names = {v: k for k, v in STATUS.items()}
    entry["counts"] = {k: 0 for k in STATUS}
    for r in res:
        entry["counts"][names[r[0]]] += 1


# ---------------------------------------------------------------- catalog
def catalog_path(area):
    return os.path.join(OUT_ROOT, area["id"], "catalog.json")


def load_catalog(area, communities):
    path = catalog_path(area)
    cat = {"passes": []}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            cat = json.load(f)
    lon0, lat0, lon1, lat1 = area["bbox"]
    cat.update(area={k: area[k] for k in ("id", "name", "country", "bbox", "hub", "river",
                                         "access_radius_m", "safe_width_m", "widths_m", "water_db")},
               grid={"nx": area["nx"], "ny": area["ny"], "step_deg": area["step_deg"],
                     "pixel_m": round(area["px_m"], 1), "bounds": [[lat0, lon0], [lat1, lon1]]},
               communities=communities,
               status_codes={str(v): k for k, v in STATUS.items()},
               sources={"radar": "NISAR L2 GCOV (NASA/ISRO), ASF DAAC",
                        "places": "© OpenStreetMap contributors (ODbL)"})
    return cat


def save_catalog(area, cat):
    cat["passes"].sort(key=lambda p: (p["date"], p["time_utc"]))
    path = catalog_path(area)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cat, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, path)


def classify_communities(area, cat):
    """
    Use the whole record to decide which communities the radar can actually monitor:
      inland      no water within access_radius_m on any pass (not river-dependent)
      unresolved  water nearby but never linked to the hub on any pass: its channels are
                  narrower than the radar resolves, so "isolated" would be a false alarm
      monitored   linked to the hub on at least one pass; isolation means a lost link
    Per-pass counts are then taken over monitored communities only.
    """
    evaluated = [p for p in cat["passes"] if p.get("evaluated") and p.get("status")]
    for c in cat["communities"]:
        rows = [p["status"].get(c["id"]) for p in evaluated]
        rows = [r for r in rows if r and r[0] != STATUS["no_data"]]
        if not rows:
            c["class"] = "no_data"
        elif min(r[2] for r in rows) > area["access_radius_m"]:
            c["class"] = "inland"
        elif not any(r[0] in (STATUS["connected"], STATUS["at_risk"]) for r in rows):
            c["class"] = "unresolved"
        else:
            c["class"] = "monitored"
    monitored = {c["id"] for c in cat["communities"] if c["class"] == "monitored"}
    names = {v: k for k, v in STATUS.items()}
    # A single image can be spoiled by wind or rain on the water, so isolation is only confirmed
    # when the previous evaluated pass with data for that community also showed it isolated.
    # Until then it counts as at risk and is listed in the pass's "unconfirmed".
    last = {}
    for p in sorted(evaluated, key=lambda p: (p["date"], p["time_utc"])):
        counts = {k: 0 for k in STATUS}
        p["unconfirmed"] = []
        for cid in sorted(monitored):
            code = p["status"][cid][0]
            if code == STATUS["isolated"] and last.get(cid) != STATUS["isolated"]:
                p["unconfirmed"].append(cid)
                counts["at_risk"] += 1
            else:
                counts[names[code]] += 1
            if code != STATUS["no_data"]:
                last[cid] = code
        p["counts"] = counts
    cat["community_classes"] = {k: sum(c["class"] == k for c in cat["communities"])
                                for k in ("monitored", "unresolved", "inland", "no_data")}


def refresh_changes(area, cat):
    """change.png for every pass against the previous pass of the same track."""
    out_dir = os.path.join(OUT_ROOT, area["id"])
    by_track = {}
    for p in sorted(cat["passes"], key=lambda p: p["date"]):
        if p.get("shown", True):
            by_track.setdefault(p["track"], []).append(p)
    pix_km2 = (area["px_m"] / 1000.0) ** 2
    for seq in by_track.values():
        for prev, cur in zip(seq, seq[1:]):
            if cur.get("change", {}).get("since") == prev["id"]:
                continue
            a = os.path.join(out_dir, "passes", prev["id"], "water.npz")
            b = os.path.join(out_dir, "passes", cur["id"], "water.npz")
            if not (os.path.exists(a) and os.path.exists(b)):
                continue
            lost, gained = save_change(load_mask(a), load_mask(b),
                                       os.path.join(out_dir, "passes", cur["id"], "change.png"))
            cur["files"]["change"] = "change.png"
            cur["change"] = {"since": prev["id"], "lost_km2": round(lost * pix_km2, 2),
                             "gained_km2": round(gained * pix_km2, 2)}


# ---------------------------------------------------------------- commands
def cmd_communities(area):
    lon0, lat0, lon1, lat1 = area["bbox"]
    q = (f'[out:json][timeout:90];(node["place"~"^(town|village|hamlet|isolated_dwelling|locality)$"]'
         f'({lat0},{lon0},{lat1},{lon1}););out body;')
    r = requests.post(OVERPASS, data={"data": q}, timeout=180, headers={"User-Agent": USER_AGENT})
    r.raise_for_status()
    hub = area["hub"]["name"].lower()
    feats = []
    for e in r.json().get("elements", []):
        t = e.get("tags", {})
        name = t.get("name")
        if not name or name.lower() == hub:
            continue
        props = {"id": f"osm{e['id']}", "name": name, "place": t.get("place")}
        if t.get("population", "").isdigit():
            props["population"] = int(t["population"])
        feats.append({"type": "Feature", "properties": props,
                      "geometry": {"type": "Point", "coordinates": [round(e["lon"], 6), round(e["lat"], 6)]}})
    feats.sort(key=lambda f: f["properties"]["name"])
    path = os.path.join(AREAS, area["communities"])
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "attribution": "© OpenStreetMap contributors (ODbL)",
                   "features": feats}, f, ensure_ascii=False, indent=1)
    log(f"{len(feats)} places saved to {os.path.relpath(path, ROOT)}")


def load_communities(area):
    path = os.path.join(AREAS, area["communities"])
    if not os.path.exists(path):
        raise SystemExit(f"Missing {os.path.relpath(path, ROOT)}: run `river_monitor.py communities` first.")
    with open(path, encoding="utf-8") as f:
        fc = json.load(f)
    out = []
    for feat in fc["features"]:
        p = feat["properties"]
        lon, lat = feat["geometry"]["coordinates"]
        lon0, lat0, lon1, lat1 = area["bbox"]
        if lon0 <= lon <= lon1 and lat0 <= lat <= lat1:
            out.append({**p, "lon": lon, "lat": lat})
    return out


def _worker(args):
    area, communities, ps, out_dir, token = args
    try:
        return ps["id"], process_pass(area, communities, ps, out_dir, token), None
    except Exception:  # keep the batch running; the pass is retried on the next update
        return ps["id"], None, traceback.format_exc(limit=3)


def cmd_update(area, workers=2, limit=None, redo=False):
    communities = load_communities(area)
    cat = load_catalog(area, communities)
    log(f"Searching ASF for NISAR GCOV over {area['name']} ...")
    passes = search(area)
    done = {p["id"] for p in cat["passes"]}
    todo = sorted((p for pid, p in passes.items() if redo or pid not in done), key=lambda p: p["date"])
    if limit:
        todo = todo[-limit:]
    log(f"{len(passes)} passes found, {len(todo)} to process")
    cat["last_search"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if todo:
        token = earthdata_token()
        out_dir = os.path.join(OUT_ROOT, area["id"])
        jobs = [(area, communities, ps, out_dir, token) for ps in todo]
        with cf.ProcessPoolExecutor(max_workers=max(1, workers)) as ex:
            for pid, entry, err in ex.map(_worker, jobs):
                if err:
                    log(f"FAILED {pid}:\n{err}")
                    continue
                cat["passes"] = [p for p in cat["passes"] if p["id"] != pid] + [entry]
                c = entry.get("counts")
                log(f"{pid}: coverage {entry['coverage'] * 100:.0f} %, water {entry['water_km2']} km², "
                    f"read {entry['read_mb']} MB in {entry['seconds']} s"
                    + (f", connected {c['connected']} / at risk {c['at_risk']} / isolated {c['isolated']}" if c else
                       ", not evaluated (partial coverage)"))
                save_catalog(area, cat)
    refresh_changes(area, cat)
    classify_communities(area, cat)
    save_catalog(area, cat)
    log(f"Catalog: {os.path.relpath(catalog_path(area), ROOT)} ({len(cat['passes'])} passes); "
        f"communities {cat['community_classes']}")


def cmd_reevaluate(area):
    """Recompute water layers and community status from the stored masks (no download)."""
    communities = load_communities(area)
    cat = load_catalog(area, communities)
    out_dir = os.path.join(OUT_ROOT, area["id"])
    for entry in cat["passes"]:
        path = os.path.join(out_dir, "passes", entry["id"], "water.npz")
        if not os.path.exists(path):
            continue
        water, valid = load_mask(path)
        inside = ndimage.distance_transform_edt(water) * area["px_m"]
        wide = wide_water(water, inside, area["safe_width_m"], area["px_m"])
        save_water(water, wide, os.path.join(out_dir, "passes", entry["id"], "water.png"))
        evaluate(area, communities, water, valid, wide, entry)
        log(f"{entry['id']}: re-evaluated")
    refresh_changes(area, cat)
    classify_communities(area, cat)
    save_catalog(area, cat)
    log(f"Catalog: {len(cat['passes'])} passes; communities {cat['community_classes']}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["communities", "update", "reevaluate", "watch"])
    ap.add_argument("--area", default="tefe")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--limit", type=int, help="process only the N most recent pending passes")
    ap.add_argument("--redo", action="store_true", help="reprocess passes already in the catalog")
    ap.add_argument("--hours", type=float, default=6.0, help="watch: hours between searches")
    a = ap.parse_args()
    area = load_area(a.area)
    if a.command == "communities":
        cmd_communities(area)
    elif a.command == "update":
        cmd_update(area, a.workers, a.limit, a.redo)
    elif a.command == "reevaluate":
        cmd_reevaluate(area)
    else:
        while True:
            try:
                cmd_update(area, a.workers)
            except Exception:
                log("update failed:\n" + traceback.format_exc(limit=3))
            log(f"next search in {a.hours} h")
            time.sleep(a.hours * 3600)


if __name__ == "__main__":
    main()
