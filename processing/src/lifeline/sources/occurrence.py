"""How often each pixel of the area held water: JRC Global Surface Water occurrence 1984-2021 (share of the months
with water, 0-100 %; public COGs on Google Cloud Storage, no account), on the area grid.

The river channel holds water almost every month (95-100 %); the beds of lakes, bays and side channels that drain at
low water much less. At low water the radar cannot tell such a wet bed from open water (both read about -17 dB in
HH), so the route rule leaves it out then (analysis.water.low_water_route).

The layer never changes: `river-monitor occurrence` reads it once (it needs rasterio, the benchmark extra) and saves it
next to the area file as an 8-bit PNG; the worker only reads that PNG.
"""
import math
import os

import numpy as np
from PIL import Image

from lifeline.config import AREAS_DIR, log
from lifeline.geometry.area import area_transform

OCCURRENCE_URL = ("https://storage.googleapis.com/global-surface-water/downloads2021/occurrence/"
                  "occurrence_{tile}v1_4_2021.tif")
NO_DATA = 255


def occurrence_tiles(bbox):
    """JRC Global Surface Water tile names (10 x 10 degrees, named by the north-west corner, e.g. 70W_0N)."""
    lon0, lat0, lon1, lat1 = bbox
    tops = range(math.ceil(lat1 / 10) * 10, math.floor(lat0 / 10) * 10, -10)
    lefts = range(math.floor(lon0 / 10) * 10, math.ceil(lon1 / 10) * 10, 10)

    def name(lo, la):
        return f"{abs(lo)}{'E' if lo >= 0 else 'W'}_{abs(la)}{'N' if la >= 0 else 'S'}"
    return [name(lo, la) for la in tops for lo in lefts]


def read_layer(url, area, src_nodata, read_band=None):
    """One public COG on the area grid (nearest neighbour, NO_DATA outside it)."""
    if read_band is not None:
        return read_band(url, area)
    import rasterio
    from rasterio.warp import Resampling, reproject

    out = np.full((area["ny"], area["nx"]), NO_DATA, np.uint8)
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_MAX_RETRY="4", GDAL_HTTP_RETRY_DELAY="2"):
        with rasterio.open(url) as src:
            reproject(rasterio.band(src, 1), out, src_nodata=src_nodata, dst_nodata=NO_DATA,
                      dst_transform=area_transform(area), dst_crs="EPSG:4326", resampling=Resampling.nearest)
    return out


def first_valid(arrays):
    """Mosaic of uint8 layers: the first value that is not NO_DATA."""
    out = np.full(arrays[0].shape, NO_DATA, np.uint8)
    for a in arrays:
        take = (out == NO_DATA) & (a != NO_DATA)
        out[take] = a[take]
    return out


def fetch_occurrence(area, read_band=None):
    """The occurrence layer on the area grid, read from the JRC tiles (no data in the tiles is 255 too)."""
    return first_valid([read_layer(OCCURRENCE_URL.format(tile=t), area, NO_DATA, read_band)
                        for t in occurrence_tiles(area["bbox"])])


def occurrence_path(area, areas_dir=AREAS_DIR):
    return os.path.join(areas_dir, area.get("occurrence") or f"{area['id']}_occurrence.png")


def save_occurrence(area, occurrence, areas_dir=AREAS_DIR):
    path = occurrence_path(area, areas_dir)
    Image.fromarray(occurrence.astype(np.uint8)).save(path, optimize=True)
    return path


def load_occurrence(area, areas_dir=AREAS_DIR):
    """The saved layer, or None when the area has none or it does not fit the area grid (logged): the rules that
    need it are then skipped."""
    path = occurrence_path(area, areas_dir)
    if not os.path.exists(path):
        log(f"no water occurrence layer at {path} (river-monitor occurrence makes it)")
        return None
    with Image.open(path) as im:
        occ = np.asarray(im, dtype=np.uint8)
    if occ.shape != (area["ny"], area["nx"]):
        log(f"water occurrence layer {path} is {occ.shape}, the area grid {(area['ny'], area['nx'])}: ignored")
        return None
    return occ
