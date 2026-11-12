"""Sentinel-2 reference water for the benchmark: MNDWI of the clearest L2A date near a pass, on the area grid.

Scenes come from the Earth Search STAC catalogue (Element 84, public Sentinel-2 L2A COGs on AWS; no account).
MNDWI = (green - SWIR1) / (green + SWIR1) with B03 (read at its 20 m overview) and B11 (20 m). Water is MNDWI above
an Otsu threshold computed on the clear pixels of the area. Clouds, cirrus, cloud shadows, saturated and missing
pixels (scene classification, SCL) are masked, with a CLOUD_MARGIN_PX margin around clouds and shadows.
"""
import datetime as dt
import os

import numpy as np
from scipy import ndimage

STAC_SEARCH = "https://earth-search.aws.element84.com/v1/search"
COLLECTION = "sentinel-2-l2a"
CLEAR_SCL = (2, 4, 5, 6, 7)       # dark area, vegetation, bare soil, water, unclassified
CLOUDY_SCL = (3, 8, 9, 10)        # cloud shadow, cloud medium / high probability, thin cirrus
CLOUD_MARGIN_PX = 5               # 100 m at 20 m
OTSU_RANGE = (-0.2, 0.3)          # an Otsu threshold outside this range means the scene is not bimodal: clamp it
MIN_REF_WATER_PX = 5              # reference specks smaller than this are dropped


def search_scenes(area, day, max_days, post):
    """STAC items of Sentinel-2 L2A over the area within max_days of `day` (a date)."""
    lon0, lat0, lon1, lat1 = area["bbox"]
    a, b = day - dt.timedelta(days=max_days), day + dt.timedelta(days=max_days)
    body = {"collections": [COLLECTION], "bbox": [lon0, lat0, lon1, lat1], "limit": 100,
            "datetime": f"{a.isoformat()}T00:00:00Z/{b.isoformat()}T23:59:59Z"}
    r = post(STAC_SEARCH, json=body, timeout=120)
    r.raise_for_status()
    return r.json().get("features", [])


def by_date(items):
    """{acquisition date (ISO): [items]}."""
    out = {}
    for it in items:
        out.setdefault(it["properties"]["datetime"][:10], []).append(it)
    return out


def otsu_threshold(values, bins=256):
    """Threshold that maximises the between-class variance of `values` (Otsu, 1979)."""
    v = values[np.isfinite(values)]
    if v.size == 0:
        return float("nan")
    hist, edges = np.histogram(v, bins=bins)
    centres = (edges[:-1] + edges[1:]) / 2
    w0 = np.cumsum(hist)
    w1 = w0[-1] - w0
    m = np.cumsum(hist * centres)
    with np.errstate(divide="ignore", invalid="ignore"):
        mu0 = m / w0
        mu1 = (m[-1] - m) / w1
        between = w0 * w1 * (mu0 - mu1) ** 2
    between[~np.isfinite(between)] = -1
    if between.max() <= 0:
        return float("nan")   # a single value: no cut separates two classes
    # between two well separated classes every cut in the empty gap is equally good: take the middle of that plateau
    top = np.flatnonzero(between >= between.max() * (1 - 1e-9))
    return float((centres[top[0]] + centres[top[-1]]) / 2)


def clear_mask(scl):
    """Pixels fit for the reference: a clear scene class and away from clouds and shadows."""
    cloudy = np.isin(scl, CLOUDY_SCL)
    near = ndimage.binary_dilation(cloudy, iterations=CLOUD_MARGIN_PX) if cloudy.any() else cloudy
    return np.isin(scl, CLEAR_SCL) & ~near


def reference_water(mndwi, clear, in_area):
    """(water, valid, threshold) of a reference MNDWI: Otsu threshold on the clear pixels of the area, clamped to
    OTSU_RANGE, specks under MIN_REF_WATER_PX dropped."""
    valid = clear & in_area & np.isfinite(mndwi)
    t = otsu_threshold(mndwi[valid]) if valid.any() else float("nan")
    t = float(np.clip(t, *OTSU_RANGE)) if np.isfinite(t) else OTSU_RANGE[1]
    water = valid & (mndwi > t)
    lab, n = ndimage.label(water)
    if n:
        water &= np.bincount(lab.ravel())[lab] >= MIN_REF_WATER_PX
    return water, valid, round(t, 4)


def area_transform(area):
    from rasterio.transform import from_origin
    lon0, _, _, lat1 = area["bbox"]
    return from_origin(lon0, lat1, area["step_deg"], area["step_deg"])


def read_band(url, area, resampling, overview_level=None):
    """One COG band reprojected onto the area grid (float32, 0 = no data)."""
    import rasterio
    from rasterio.warp import Resampling, reproject

    out = np.zeros((area["ny"], area["nx"]), np.float32)
    kw = {} if overview_level is None else {"overview_level": overview_level}
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_MAX_RETRY="4", GDAL_HTTP_RETRY_DELAY="2"):
        with rasterio.open(url, **kw) as src:
            reproject(rasterio.band(src, 1), out, src_nodata=0, dst_nodata=0, dst_transform=area_transform(area),
                      dst_crs="EPSG:4326", resampling=getattr(Resampling, resampling))
    return out


def reflectance(dn, asset, offset_applied=False):
    """Surface reflectance from digital numbers with the asset's scale and offset (processing baseline 04.00 and
    later store reflectance with a -0.1 offset; ignoring it biases MNDWI). When the catalogue already removed that
    offset from the pixels (Earth Search item property earthsearch:boa_offset_applied), the band metadata still
    lists it and it must not be applied again: dark forest and water would go negative. Dark water can come out at
    or slightly below 0 in SWIR, which is kept: no data is decided on the digital numbers (0), not here."""
    band = (asset.get("raster:bands") or [{}])[0]
    scale = float(band.get("scale", 1e-4))
    offset = 0.0 if offset_applied else float(band.get("offset", 0.0))
    return (dn * scale + offset).astype(np.float32)


def mndwi_of(green, swir, ok):
    """MNDWI clipped to [-1, 1]; NaN outside `ok` or where green + SWIR is not positive."""
    with np.errstate(divide="ignore", invalid="ignore"):
        m = np.where(ok & ((green + swir) > 0), (green - swir) / (green + swir), np.nan)
    return np.clip(m, -1.0, 1.0).astype(np.float32)


def mosaic_scl(area, items, read=read_band):
    """Scene classification of one date mosaicked onto the area grid (first tile wins). Cheap: one 20 m byte band
    per tile, enough to rank the dates by clear share before reading the reflectance bands."""
    scl = np.zeros((area["ny"], area["nx"]), np.uint8)
    for it in items:
        s = read(it["assets"]["scl"]["href"], area, "nearest").astype(np.uint8)
        take = (scl == 0) & (s > 0)
        scl[take] = s[take]
    return scl


def mosaic_date(area, items, read=read_band):
    """(mndwi, scl) of one date: the tiles of that date mosaicked onto the area grid (first tile wins)."""
    green = np.zeros((area["ny"], area["nx"]), np.float32)
    swir = np.zeros_like(green)
    scl = np.zeros(green.shape, np.uint8)
    for it in items:
        a = it["assets"]
        s = read(a["scl"]["href"], area, "nearest").astype(np.uint8)
        g_dn = read(a["green"]["href"], area, "average", overview_level=0)
        w_dn = read(a["swir16"]["href"], area, "average")
        take = (scl == 0) & (s > 0) & (g_dn > 0) & (w_dn > 0)   # digital number 0 = no data
        applied = bool(it["properties"].get("earthsearch:boa_offset_applied", False))
        scl[take] = s[take]
        green[take] = reflectance(g_dn, a["green"], applied)[take]
        swir[take] = reflectance(w_dn, a["swir16"], applied)[take]
    return mndwi_of(green, swir, scl > 0), scl


def _cached(path, build):
    """The arrays stored at path, else build() stored there first ({name: array})."""
    if os.path.exists(path):
        with np.load(path) as z:
            return {k: z[k] for k in z.files}
    arrays = build()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    np.savez_compressed(path + ".tmp.npz", **arrays)
    os.replace(path + ".tmp.npz", path)
    return arrays


def cached_scl(area, date, items, cache_dir, read=read_band):
    path = os.path.join(cache_dir, "sentinel2", area["id"], date + "_scl.npz")
    return _cached(path, lambda: {"scl": mosaic_scl(area, items, read)})["scl"]


def cached_date(area, date, items, cache_dir, read=read_band):
    """mosaic_date through a cache file (cache_dir/sentinel2/<area>/<date>.npz)."""
    path = os.path.join(cache_dir, "sentinel2", area["id"], date + ".npz")

    def build():
        mndwi, scl = mosaic_date(area, items, read)
        return {"mndwi": mndwi.astype(np.float16), "scl": scl}
    z = _cached(path, build)
    return z["mndwi"].astype(np.float32), z["scl"]


def reference_for_pass(area, pass_date, in_area, cache_dir, max_days, min_clear, post, read=read_band):
    """The best Sentinel-2 reference near a pass: the date with the largest clear share of the area within
    max_days (ties: the closest date), ranked on the scene classification alone; only that date's reflectance is
    read. None when no date reaches min_clear. Returns {date, days_apart, clear_share, threshold, water, valid,
    cloudy}; `cloudy` marks the clouds, cirrus and shadows themselves (no margin)."""
    day = dt.date.fromisoformat(pass_date)
    n_area = max(1, int(in_area.sum()))
    ranked = []
    for date, items in sorted(by_date(search_scenes(area, day, max_days, post)).items()):
        share = float((clear_mask(cached_scl(area, date, items, cache_dir, read)) & in_area).sum() / n_area)
        ranked.append((share, -abs((dt.date.fromisoformat(date) - day).days), date, items))
    if not ranked:
        return None
    share, neg_gap, date, items = max(ranked, key=lambda r: (r[0], r[1]))
    if share < min_clear:
        return None
    mndwi, scl = cached_date(area, date, items, cache_dir, read)
    clear = clear_mask(scl)
    water, valid, t = reference_water(mndwi, clear, in_area)
    return {"date": date, "days_apart": -neg_gap, "clear_share": round(float((clear & in_area).sum() / n_area), 4),
            "threshold": t, "water": water, "valid": valid, "cloudy": np.isin(scl, CLOUDY_SCL) & in_area}
