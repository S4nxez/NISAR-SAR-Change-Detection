"""Backscatter helpers and the read of one pass (all its frames) onto the area grid."""
import os
import warnings

import numpy as np

from lifeline import config
from lifeline.sources.remote import RemoteFile

GRID = "science/LSAR/GCOV/grids"
CACHED_BANDS = ("HHHH", "HVHV")   # every band a method may use, so a cached window is never read again
DEFAULT_SPECKLE_M = 100.0
DEFAULT_VALID_FLOOR_DB = -40.0   # below it a pixel is fill, not a measurement (ADR-001)
ROWS_PER_CHUNK = 256


def linear_to_db(a):
    """Linear power -> dB; zero, negative and non-finite values become NaN."""
    with np.errstate(divide="ignore", invalid="ignore"):
        db = 10.0 * np.log10(np.asarray(a, dtype=np.float32))
    db[~np.isfinite(db)] = np.nan
    return db


def mask_fill(db, floor_db):
    """Values below floor_db are not measurements: GCOV windows carry near-zero fill (down to -170 dB) at the
    edge of the imaged swath, far below NISAR's noise floor (about -25 dB). They become NaN (no data) so they are
    neither water nor averaged into their neighbours by the speckle filter. Works in place and returns db."""
    with np.errstate(invalid="ignore"):
        db[db < floor_db] = np.nan
    return db


def box_sum(a, k):
    """Sum over a k x k window (k odd) with cumulative sums; windows are clipped at the edges."""
    r = k // 2
    p = np.pad(a.astype(np.float64), ((r + 1, r), (r + 1, r)), mode="constant")
    s = p.cumsum(0).cumsum(1)
    return s[k:, k:] - s[:-k, k:] - s[k:, :-k] + s[:-k, :-k]


def speckle_filter(db, k):
    """Mean in linear power over a k x k window, ignoring NaN. Returns dB."""
    ok = np.isfinite(db)
    lin = np.where(ok, np.power(10.0, np.where(ok, db, 0) / 10.0), 0.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        out = 10.0 * np.log10(box_sum(lin, k) / box_sum(ok.astype(np.float64), k))
    out[~ok] = np.nan
    return out.astype(np.float32)


LEE_RADIUS = 3            # 7 x 7 window
LEE_CHUNK_ROWS = 512
LEE_MIN_PIXELS = 10       # fewer valid pixels in the chosen half window: keep the pixel as measured


def _lee_halves():
    """The eight edge-aligned half windows of a 7 x 7 window (28 pixels each, centre line included): west, east,
    north, south and the four triangles cut by the diagonals."""
    r = LEE_RADIUS
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    return [xx <= 0, xx >= 0, yy <= 0, yy >= 0, (xx + yy) <= 0, (xx + yy) >= 0, (yy - xx) <= 0, (yy - xx) >= 0]


LEE_HALVES = _lee_halves()


def _sub_means(lin, ok):
    """Mean of every 3 x 3 block (NaN ignored) of a padded chunk."""
    with np.errstate(invalid="ignore", divide="ignore"):
        return box_sum(np.where(ok, lin, 0.0), 3) / box_sum(ok.astype(np.float64), 3)


def _lee_chunk(lin, ok, cu2):
    """Refined Lee on a chunk padded with LEE_RADIUS rows and columns on every side; returns the unpadded result."""
    from scipy import ndimage
    r = LEE_RADIUS
    h, w = lin.shape[0] - 2 * r, lin.shape[1] - 2 * r
    m = _sub_means(lin, ok)
    s = {(dy, dx): m[r + dy:r + dy + h, r + dx:r + dx + w] for dy in (-2, 0, 2) for dx in (-2, 0, 2)}
    def side(*keys):   # mean of the blocks of one side that have data (image edges and gaps are NaN)
        with np.errstate(invalid="ignore"), warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            return np.nanmean(np.stack([s[k] for k in keys]), axis=0)

    # sub-means of each side of the four possible edges; the side closer to the centre block is the pixel's own
    sides = [
        (side((-2, -2), (0, -2), (2, -2)), side((-2, 2), (0, 2), (2, 2))),     # west | east
        (side((-2, -2), (-2, 0), (-2, 2)), side((2, -2), (2, 0), (2, 2))),     # north | south
        (side((-2, -2), (-2, 0), (0, -2)), side((0, 2), (2, 0), (2, 2))),      # north-west | south-east
        (side((-2, 0), (-2, 2), (0, 2)), side((0, -2), (2, -2), (2, 0))),      # north-east | south-west
    ]
    centre = s[0, 0]
    grads = np.stack([np.abs(b - a) for a, b in sides])
    direction = np.argmax(np.nan_to_num(grads, nan=-1.0), axis=0)
    first, second = np.stack([a for a, _ in sides]), np.stack([b for _, b in sides])
    pick = lambda arr: np.take_along_axis(arr, direction[None], 0)[0]   # noqa: E731
    d1, d2 = np.abs(pick(first) - centre), np.abs(pick(second) - centre)
    own_side = np.where(np.isnan(d1), 1, np.where(np.isnan(d2) | (d1 <= d2), 0, 1))   # a side without data loses
    choice = 2 * direction + own_side                    # index into LEE_HALVES
    lin0 = np.where(ok, lin, 0.0)
    okf = ok.astype(np.float64)
    mean = np.zeros((h, w))
    sq = np.zeros((h, w))
    cnt = np.zeros((h, w))
    for k, half in enumerate(LEE_HALVES):
        sel = choice == k
        if not sel.any():
            continue
        kern = half.astype(np.float64)
        mean[sel] = ndimage.correlate(lin0, kern, mode="constant")[r:r + h, r:r + w][sel]
        sq[sel] = ndimage.correlate(lin0 * lin0, kern, mode="constant")[r:r + h, r:r + w][sel]
        cnt[sel] = ndimage.correlate(okf, kern, mode="constant")[r:r + h, r:r + w][sel]
    with np.errstate(invalid="ignore", divide="ignore"):
        mu = mean / cnt
        var = np.maximum(sq / cnt - mu * mu, 0.0)
        var_x = (var - mu * mu * cu2) / (1.0 + cu2)
        k = np.clip(np.where(var > 0, var_x / var, 0.0), 0.0, 1.0)
    x = lin[r:r + h, r:r + w]
    out = mu + k * (x - mu)
    out = np.where(cnt >= LEE_MIN_PIXELS, out, x)
    out[~ok[r:r + h, r:r + w]] = np.nan
    return out


def refined_lee(db, looks):
    """Refined Lee speckle filter (Lee 1981; edge-aligned windows, Lee, Grunes and De Grandi 1999) in linear power.

    In a 7 x 7 window the strongest of four edge directions is found from the means of nine 3 x 3 blocks; the
    statistics are taken over the half window on the pixel's own side of that edge, so a channel pixel is averaged
    with water and not with the bright bank. Then x = mu + k (I - mu), k = var_x / var with
    var_x = (var - mu^2 Cu^2) / (1 + Cu^2) and Cu^2 = 1 / looks: homogeneous windows (variance of speckle only) are
    averaged, heterogeneous ones keep the pixel. NaN in, NaN out. Returns dB."""
    lin = np.where(np.isfinite(db), np.power(10.0, np.nan_to_num(db) / 10.0), np.nan)
    r = LEE_RADIUS
    pad = np.pad(lin, r, mode="constant", constant_values=np.nan)
    ok = np.isfinite(pad)
    out = np.empty(db.shape, np.float32)
    for a in range(0, db.shape[0], LEE_CHUNK_ROWS):
        b = min(db.shape[0], a + LEE_CHUNK_ROWS)
        out[a:b] = _lee_chunk(pad[a:b + 2 * r], ok[a:b + 2 * r], 1.0 / looks)
    with np.errstate(divide="ignore", invalid="ignore"):
        res = 10.0 * np.log10(out)
    res[~np.isfinite(res)] = np.nan
    return res.astype(np.float32)


def filter_db(area, db, spacing_m):
    """The area's speckle filter: "box" (mean over speckle_m) or "refined_lee" (with speckle_looks looks)."""
    kind = area.get("speckle_filter", "box")
    if kind == "box":
        return speckle_filter(db, speckle_window(area, spacing_m))
    if kind == "refined_lee":
        return refined_lee(db, float(area["speckle_looks"]))
    raise ValueError(f"unknown speckle_filter {kind!r}")


def block_mean(a, f):
    """Mean over f x f blocks, ignoring NaN (the rows and columns that do not fill a block are dropped)."""
    h, w = a.shape[0] // f * f, a.shape[1] // f * f
    b = a[:h, :w].reshape(h // f, f, w // f, f)
    with np.errstate(invalid="ignore"):
        cnt = np.isfinite(b).sum(axis=(1, 3))
        s = np.nansum(b, axis=(1, 3))
        return np.where(cnt > 0, s / np.maximum(cnt, 1), np.nan).astype(np.float32)


def speckle_window(area, spacing_m):
    """Odd window size (pixels, at least 3) of the speckle filter for the product's pixel spacing."""
    return max(3, int(round(area.get("speckle_m", DEFAULT_SPECKLE_M) / spacing_m)) | 1)


def area_edge(area, n=50):
    """lon, lat of n points per side along the edge of the area's bbox."""
    lon0, lat0, lon1, lat1 = area["bbox"]
    lon = np.concatenate([np.linspace(lon0, lon1, n), np.full(n, lon1), np.linspace(lon1, lon0, n), np.full(n, lon0)])
    lat = np.concatenate([np.full(n, lat0), np.linspace(lat0, lat1, n), np.full(n, lat1), np.linspace(lat1, lat0, n)])
    return lon, lat


def product_window(xs, ys, ex, ey, pad):
    """(r0, r1, c0, c1) of the product's grid that holds the edge points (ex, ey) plus pad metres."""
    dx, dy = float(xs[1] - xs[0]), float(ys[1] - ys[0])
    c0 = max(0, int(np.floor((min(ex) - pad - xs[0]) / dx)))
    c1 = min(len(xs), int(np.ceil((max(ex) + pad - xs[0]) / dx)) + 1)
    r0 = max(0, int(np.floor((max(ey) + pad - ys[0]) / dy)))
    r1 = min(len(ys), int(np.ceil((min(ey) - pad - ys[0]) / dy)) + 1)
    return r0, r1, c0, c1


def resample_into(out, db, area, transformer, x0, y0, dx, dy):
    """Fill the NaN pixels of `out` (area grid) with the nearest pixel of `db`, a product window whose
    first pixel centre is (x0, y0) in the product's projection."""
    ny, nx, step = area["ny"], area["nx"], area["step_deg"]
    lon0, _, _, lat1 = area["bbox"]
    lons = lon0 + (np.arange(nx) + 0.5) * step
    for a in range(0, ny, ROWS_PER_CHUNK):
        b = min(ny, a + ROWS_PER_CHUNK)
        lats = lat1 - (np.arange(a, b) + 0.5) * step
        lo, la = np.meshgrid(lons, lats)
        x, y = transformer.transform(lo, la)
        ci = np.rint((x - x0) / dx).astype(np.int64)
        ri = np.rint((y - y0) / dy).astype(np.int64)
        ok = (ci >= 0) & (ci < db.shape[1]) & (ri >= 0) & (ri < db.shape[0])
        v = np.full(ci.shape, np.nan, np.float32)
        v[ok] = db[ri[ok], ci[ok]]
        blk = out[a:b]
        fill = np.isnan(blk) & np.isfinite(v)
        blk[fill] = v[fill]


def read_window(area, granule, token, bands=("HHHH",), open_remote=RemoteFile):
    """The area's window of one granule: {epsg, x0, y0, dx, dy, mb, bands: {name: linear power}} with the
    bands of `bands` the product has, (x0, y0) the centre of its first pixel in the product's projection.
    None when the granule has no HH or does not reach the area."""
    import h5py
    from pyproj import Transformer

    edge_lon, edge_lat = area_edge(area)
    with open_remote(granule["url"], token) as rf:
        with h5py.File(rf, "r") as f:
            fa = f[GRID + "/frequencyA"]
            if "HHHH" not in fa:
                return None
            epsg = int(fa["projection"][()])
            xs, ys = fa["xCoordinates"][()], fa["yCoordinates"][()]
            dx, dy = float(xs[1] - xs[0]), float(ys[1] - ys[0])
            ex, ey = Transformer.from_crs(4326, epsg, always_xy=True).transform(edge_lon, edge_lat)
            r0, r1, c0, c1 = product_window(xs, ys, ex, ey, pad=8 * abs(dx))
            if c1 - c0 < 10 or r1 - r0 < 10:
                return None
            data = {b: fa[b][r0:r1, c0:c1] for b in bands if b in fa}
        return {"epsg": epsg, "x0": float(xs[c0]), "y0": float(ys[r0]), "dx": dx, "dy": dy,
                "mb": rf.bytes / 1e6, "bands": data}


def window_cache_path(area, granule, cache_dir):
    """Cache file of a granule's window for this area (the window depends on the area's bbox only)."""
    lon0, lat0, lon1, lat1 = area["bbox"]
    key = f"{area['id']}_{lon0:.5f}_{lat0:.5f}_{lon1:.5f}_{lat1:.5f}".replace("-", "m")
    name = os.path.basename(granule.get("name") or granule["url"]).removesuffix(".h5")
    return os.path.join(cache_dir, "windows", key, name + ".npz")


def save_window(path, window):
    """Store a window (None is stored too, so a granule that misses the area is not opened again)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp.npz"
    if window is None:
        np.savez(tmp, empty=np.array(True))
    else:
        meta = np.array([window["x0"], window["y0"], window["dx"], window["dy"]], np.float64)
        np.savez(tmp, empty=np.array(False), epsg=np.int32(window["epsg"]), meta=meta,
                 **{"band_" + b: a for b, a in window["bands"].items()})
    os.replace(tmp, path)


def load_window(path):
    """A window stored by save_window (mb = 0: nothing was downloaded)."""
    with np.load(path) as z:
        if bool(z["empty"]):
            return None
        x0, y0, dx, dy = (float(v) for v in z["meta"])
        bands = {k[5:]: z[k] for k in z.files if k.startswith("band_")}
        return {"epsg": int(z["epsg"]), "x0": x0, "y0": y0, "dx": dx, "dy": dy, "mb": 0.0, "bands": bands}


def granule_window(area, granule, token, bands=("HHHH",), open_remote=RemoteFile, cache_dir=None):
    """read_window, through the cache when cache_dir is given. The cache keeps every band the product
    has (HH and HV), whatever `bands` asks, so a method that needs another band reads nothing remote."""
    if not cache_dir:
        return read_window(area, granule, token, bands, open_remote)
    path = window_cache_path(area, granule, cache_dir)
    downloaded_mb = 0.0
    if not os.path.exists(path):
        fresh = read_window(area, granule, token, CACHED_BANDS, open_remote)
        save_window(path, fresh)
        downloaded_mb = fresh["mb"] if fresh else 0.0
    window = load_window(path)
    if window is not None:
        window["mb"] = downloaded_mb
    return window


def read_pass(area, ps, token, open_remote=RemoteFile, cache_dir=None):
    """HH backscatter (dB, speckle-filtered) of a pass on the area grid; NaN = no data.
    Returns (db, megabytes read, product pixel spacing in metres or None).
    cache_dir defaults to MONITOR_CACHE_DIR (no cache when unset)."""
    from pyproj import Transformer

    cache_dir = cache_dir if cache_dir is not None else config.cache_dir()
    out = np.full((area["ny"], area["nx"]), np.nan, np.float32)
    read_mb, spacing = 0.0, None
    for g in ps["granules"]:
        w = granule_window(area, g, token, ("HHHH",), open_remote, cache_dir)
        if w is None:
            continue
        read_mb += w["mb"]
        spacing = abs(w["dx"])
        db = mask_fill(linear_to_db(w["bands"]["HHHH"]), area.get("valid_floor_db", DEFAULT_VALID_FLOOR_DB))
        db = filter_db(area, db, spacing)
        tr = Transformer.from_crs(4326, w["epsg"], always_xy=True)
        resample_into(out, db, area, tr, w["x0"], w["y0"], w["dx"], w["dy"])
    return out, read_mb, spacing
