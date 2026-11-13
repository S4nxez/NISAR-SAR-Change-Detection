"""Sentinel-1 C-band radar water and land on the area grid: the second radar of the monitor (ADR-007).

NISAR (L band, 24 cm) and Sentinel-1 (C band, 5.6 cm) see different surfaces as rough. The wet, smooth bed of a lake
or side channel drained at low water is as smooth as open water at 24 cm, so NISAR reads it as water; at 5.6 cm the
same mud is rough and Sentinel-1 reads it about 10 dB brighter than water. Sentinel-1 is therefore the judge of
whether such a bed still holds water (analysis.water.low_water_route). Under trees and on wind-roughened water it is
the other way round, and NISAR is trusted there.

Scenes come from Microsoft Planetary Computer, collection sentinel-1-rtc: Sentinel-1 IW GRD with radiometric terrain
correction (gamma naught, linear power), 10 m pixels (20 x 22 m resolution, 4.4 looks), public with a short-lived
anonymous access token. Only VV is used: open water and mud separate best in VV. A date's tiles are averaged onto the
area grid (20 m, in linear power: about 4 more looks), filtered with the refined Lee filter and kept in the cache.

Classes of a filtered VV pixel: water (below water_db, or below weak_db and touching such water, as for NISAR), land
(at or above land_db) and undecided in between; no data where no scene covers it.
"""
import datetime as dt
import os

import numpy as np

from lifeline.analysis.radar import refined_lee
from lifeline.analysis.water import water_mask
from lifeline.config import log
from lifeline.geometry.area import area_transform
from lifeline.sources.gauge import level_on

STAC_SEARCH = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
COLLECTION = "sentinel-1-rtc"
SAS_TOKEN = f"https://planetarycomputer.microsoft.com/api/sas/v1/token/{COLLECTION}"
SOURCE = "Sentinel-1 RTC (Copernicus, ESA; terrain correction by Microsoft Planetary Computer)"
NO_DATA = -32768.0
LOOKS = 6.0    # 4.4 looks of the GRD, about 4 pixels of 10 m averaged per 20 m pixel, not independent


def search_scenes(area, day, max_days, post):
    """STAC items of the collection over the area within max_days of `day` (a date)."""
    a, b = day - dt.timedelta(days=max_days), day + dt.timedelta(days=max_days)
    body = {"collections": [COLLECTION], "bbox": area["bbox"], "limit": 100,
            "datetime": f"{a.isoformat()}T00:00:00Z/{b.isoformat()}T23:59:59Z"}
    r = post(STAC_SEARCH, json=body, timeout=120)
    r.raise_for_status()
    return r.json().get("features", [])


def by_date(items):
    """{acquisition date (ISO): [items with a VV asset]}."""
    out = {}
    for it in items:
        if "vv" in it.get("assets", {}):
            out.setdefault(it["properties"]["datetime"][:10], []).append(it)
    return out


def access_token(get):
    """The anonymous Planetary Computer token that signs the asset URLs (valid for about an hour)."""
    r = get(SAS_TOKEN, timeout=60)
    r.raise_for_status()
    return r.json()["token"]


def signed(href, token):
    return f"{href}{'&' if '?' in href else '?'}{token}"


def read_band(url, area):
    """One COG band averaged onto the area grid in linear power (float32, NaN = no data)."""
    import rasterio
    from rasterio.warp import Resampling, reproject

    out = np.full((area["ny"], area["nx"]), np.nan, np.float32)
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_MAX_RETRY="4", GDAL_HTTP_RETRY_DELAY="2"):
        with rasterio.open(url) as src:
            reproject(rasterio.band(src, 1), out, src_nodata=NO_DATA, dst_nodata=np.nan,
                      dst_transform=area_transform(area), dst_crs="EPSG:4326", resampling=Resampling.average)
    return out


def to_db(linear):
    """dB of linear power; NaN where the power is not positive."""
    out = np.full(linear.shape, np.nan, np.float32)
    ok = np.isfinite(linear) & (linear > 0)
    out[ok] = 10.0 * np.log10(linear[ok])
    return out


def mosaic_date(area, items, token, read=read_band):
    """VV (dB, unfiltered) of one date: its tiles on the area grid, the first tile with data wins."""
    vv = np.full((area["ny"], area["nx"]), np.nan, np.float32)
    for it in items:
        db = to_db(read(signed(it["assets"]["vv"]["href"], token), area))
        take = np.isnan(vv) & np.isfinite(db)
        vv[take] = db[take]
    return vv


def cache_path(area, date, cache_dir):
    return os.path.join(cache_dir, "sentinel1", area["id"], date + ".npz")


def filtered_date(area, date, items, cache_dir, token, read=read_band, looks=LOOKS):
    """Filtered VV (dB) of one date, through the cache when there is one (float16, about 0.01 dB steps)."""
    path = cache_path(area, date, cache_dir) if cache_dir else None
    if path and os.path.exists(path):
        with np.load(path) as z:
            return z["vv"].astype(np.float32)
    vv = refined_lee(mosaic_date(area, items, token(), read), looks)
    if path:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        np.savez_compressed(path + ".tmp.npz", vv=vv.astype(np.float16))
        os.replace(path + ".tmp.npz", path)
    return vv


def usable_dates(dates, pass_date, series, max_days, level_tolerance_cm):
    """The scene dates that may judge a pass, closest first (ties: the earlier one). A scene is only used when the
    river at the gauge was within level_tolerance_cm of its level on the pass day: a scene taken after the river
    fell further could show mud that was still water on the pass day, and one taken while it was much higher could
    show water over a bed that had drained by then. Without a gauge level, the date window alone decides."""
    day = dt.date.fromisoformat(pass_date)
    level = level_on(series, pass_date) if series else None
    out = []
    for d in dates:
        gap = (dt.date.fromisoformat(d) - day).days
        if abs(gap) > max_days:
            continue
        there = level_on(series, d) if series else None
        if level is not None and there is not None and abs(there - level) > level_tolerance_cm:
            continue
        out.append((abs(gap), gap, d))
    return [d for _, _, d in sorted(out)]


def classify(vv, cfg):
    """{"water", "land", "seen"} of a filtered VV mosaic (cfg: water_db, weak_db, land_db)."""
    water, seen = water_mask(vv, cfg["water_db"], cfg.get("weak_db"))
    with np.errstate(invalid="ignore"):
        land = seen & ~water & (vv >= cfg["land_db"])
    return {"water": water, "land": land, "seen": seen}


def pass_view(area, pass_date, cfg, cache_dir, series=None, post=None, get=None, read=read_band):
    """What Sentinel-1 saw around a pass: {"dates": scene dates used, closest first, "vv": the darkest filtered VV
    of those scenes on each pixel, "water", "land", "seen"}; None when no usable scene exists. Wind roughens open
    water in C band (Lake Tefe reads about -15.5 dB on a windy day, -20 dB on a calm one) for a day or two, while a
    drained bed stays bright on every date: so a pixel is land only when every scene that saw it is bright. cfg is
    the area's "sentinel1" block: max_days, level_tolerance_cm, water_db, weak_db, land_db."""
    import requests
    post, get = post or requests.post, get or requests.get
    day = dt.date.fromisoformat(pass_date)
    scenes = by_date(search_scenes(area, day, cfg["max_days"], post))
    dates = usable_dates(scenes, pass_date, series, cfg["max_days"], cfg.get("level_tolerance_cm", 0))
    if not dates:
        return None
    token_box = {}

    def token():
        if "t" not in token_box:
            token_box["t"] = access_token(get)
        return token_box["t"]
    vv = np.full((area["ny"], area["nx"]), np.nan, np.float32)
    for d in dates:
        f = filtered_date(area, d, scenes[d], cache_dir, token, read)
        vv = np.fmin(vv, f)                                   # NaN only where no scene saw the pixel
    log(f"Sentinel-1 for {pass_date}: {', '.join(dates)}")
    return {"dates": dates, "vv": vv, **classify(vv, cfg)}


def agreement(water, valid, view, px_m):
    """How a NISAR water mask and Sentinel-1 agree, over the pixels both judged (NISAR valid, Sentinel-1 water or
    land): the share that agrees and the area each one alone calls water."""
    both = valid & (view["water"] | view["land"])
    nisar, s1 = water & both, view["water"] & both
    n = int(both.sum())
    agree = int((nisar & s1).sum()) + int((both & ~nisar & ~s1).sum())
    km2 = (px_m / 1000.0) ** 2
    return {"dates": list(view["dates"]), "judged_km2": round(n * km2, 1),
            "agreement": round(agree / n, 4) if n else None,
            "both_water_km2": round(float((nisar & s1).sum()) * km2, 2),
            "nisar_only_km2": round(float((nisar & ~s1).sum()) * km2, 2),
            "sentinel1_only_km2": round(float((s1 & ~nisar).sum()) * km2, 2)}
