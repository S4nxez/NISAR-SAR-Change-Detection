"""OPERA Dynamic Surface Water Extent (DSWx) water maps as extra references of the benchmark.

Two NASA/JPL products, free with an Earthdata account (the EARTHDATA_TOKEN the monitor already uses), found through
the CMR catalogue and read from their B01_WTR layer (30 m, UTM tiles of the MGRS grid):

  dswx_s1   OPERA_L3_DSWX-S1_V1    Sentinel-1 C-band radar: sees through clouds; shares the radar blind spots
                                   (smooth mud, wind) with NISAR, but not its processing
  dswx_hls  OPERA_L3_DSWX-HLS_V1   Landsat 8/9 and Sentinel-2 (Harmonized Landsat Sentinel-2) optical water,
                                   with its own cloud mask and classifier

B01_WTR classes used here: 0 not water, 1 open water, 2 partial surface water (HLS: a mixed pixel), 3 inundated
vegetation (S1). Every other value (HAND or layover masks, snow, cloud, ocean, fill) is no data.
Downloaded tiles and the per-date mosaics on the area grid are kept in the cache, so later runs read nothing remote.
"""
import datetime as dt
import os

import numpy as np

from lifeline.benchmark.optical import _cached, area_transform

CMR_GRANULES = "https://cmr.earthdata.nasa.gov/search/granules.umm_json"
PRODUCTS = {
    "dswx_s1": {"short_name": "OPERA_L3_DSWX-S1_V1", "family": "sar", "title": "OPERA DSWx-S1 (Sentinel-1)"},
    "dswx_hls": {"short_name": "OPERA_L3_DSWX-HLS_V1", "family": "optical",
                 "title": "OPERA DSWx-HLS (Landsat / Sentinel-2)"},
}
NOT_WATER, OPEN_WATER, PARTIAL_WATER, INUNDATED_VEGETATION = 0, 1, 2, 3
NO_DATA = 255
LAYER_SUFFIX = "_B01_WTR.tif"


def search_granules(short_name, area, day, max_days, get):
    """CMR granules of a product over the area within max_days of `day`: [{date, name, url}] (B01_WTR layer)."""
    lon0, lat0, lon1, lat1 = area["bbox"]
    a, b = day - dt.timedelta(days=max_days), day + dt.timedelta(days=max_days)
    r = get(CMR_GRANULES, params={"short_name": short_name, "bounding_box": f"{lon0},{lat0},{lon1},{lat1}",
                                  "temporal": f"{a.isoformat()}T00:00:00Z,{b.isoformat()}T23:59:59Z",
                                  "page_size": 200}, timeout=120)
    r.raise_for_status()
    return granules_from_umm(r.json().get("items", []))


def granules_from_umm(items):
    """[{date, name, url}] of the CMR UMM items that carry an https B01_WTR file."""
    out = []
    for it in items:
        u = it.get("umm", {})
        start = (u.get("TemporalExtent", {}).get("RangeDateTime", {}) or {}).get("BeginningDateTime", "")
        urls = [x["URL"] for x in u.get("RelatedUrls", [])
                if x.get("Type") == "GET DATA" and x.get("URL", "").startswith("https")
                and x["URL"].endswith(LAYER_SUFFIX)]
        if start and urls:
            out.append({"date": start[:10], "name": u.get("GranuleUR", ""), "url": urls[0]})
    return out


def by_date(granules):
    out = {}
    for g in granules:
        out.setdefault(g["date"], []).append(g)
    return out


def class_masks(wtr):
    """Masks of a B01_WTR array: water (open water), land (not water), partial (mixed pixel), vegetated (inundated
    vegetation, not open water: it votes land for boat routes) and valid (any of them)."""
    water = wtr == OPEN_WATER
    partial = wtr == PARTIAL_WATER
    vegetated = wtr == INUNDATED_VEGETATION
    land = (wtr == NOT_WATER) | vegetated
    return {"water": water, "land": land, "partial": partial, "vegetated": vegetated,
            "valid": water | land | partial}


def download(url, path, token, get):
    """Download one file to path (atomic), once. The Earthdata URL redirects to a signed location; requests drops the
    Authorization header on that redirect, as the signed location requires."""
    if os.path.exists(path):
        return path
    if not token:
        raise PermissionError(f"EARTHDATA_TOKEN is needed to download {os.path.basename(path)}")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    r = get(url, headers={"Authorization": "Bearer " + token}, timeout=300)
    if r.status_code in (401, 403):
        raise PermissionError(f"Earthdata refused the token (HTTP {r.status_code}) for {os.path.basename(path)}")
    r.raise_for_status()
    with open(path + ".part", "wb") as f:
        f.write(r.content)
    os.replace(path + ".part", path)
    return path


def read_classes(path, area):
    """One B01_WTR tile reprojected onto the area grid (nearest neighbour; NO_DATA outside the tile)."""
    import rasterio
    from rasterio.warp import Resampling, reproject

    out = np.full((area["ny"], area["nx"]), NO_DATA, np.uint8)
    with rasterio.open(path) as src:
        reproject(rasterio.band(src, 1), out, src_nodata=NO_DATA, dst_nodata=NO_DATA,
                  dst_transform=area_transform(area), dst_crs="EPSG:4326", resampling=Resampling.nearest)
    return out


def mosaic(arrays):
    """Mosaic of class arrays on the same grid: the first array with a class (not NO_DATA) wins."""
    out = None
    for a in arrays:
        if out is None:
            out = a.copy()
            continue
        take = (out == NO_DATA) & (a != NO_DATA)
        out[take] = a[take]
    return out


def mosaic_date(product, area, granules, cache_dir, token, get, read=read_classes):
    """B01_WTR of one date on the area grid, through the cache (tiles and mosaic)."""
    short = PRODUCTS[product]["short_name"]
    path = os.path.join(cache_dir, "opera", area["id"], f"{product}_{granules[0]['date']}.npz")

    def build():
        tiles = [download(g["url"], os.path.join(cache_dir, "opera", short, os.path.basename(g["url"])), token, get)
                 for g in granules]
        return {"wtr": mosaic([read(t, area) for t in tiles])}
    return _cached(path, build)["wtr"]


def reference_for_pass(product, area, pass_date, in_area, cache_dir, max_days, token, get, read=read_classes):
    """The best date of an OPERA product near a pass: the largest valid share of the area within max_days (ties:
    the closest). None when the product has no granule then. Returns {product, date, days_apart, coverage, masks}."""
    day = dt.date.fromisoformat(pass_date)
    dates = by_date(search_granules(PRODUCTS[product]["short_name"], area, day, max_days, get))
    n_area = max(1, int(in_area.sum()))
    best = None
    for date, granules in sorted(dates.items()):
        masks = class_masks(mosaic_date(product, area, granules, cache_dir, token, get, read))
        share = float((masks["valid"] & in_area).sum() / n_area)
        key = (share, -abs((dt.date.fromisoformat(date) - day).days))
        if share > 0 and (best is None or key > best[0]):
            best = (key, date, masks)
    if best is None:
        return None
    (share, neg_gap), date, masks = best
    return {"product": product, "date": date, "days_apart": -neg_gap, "coverage": round(share, 4),
            **{k: v & in_area for k, v in masks.items()}}
