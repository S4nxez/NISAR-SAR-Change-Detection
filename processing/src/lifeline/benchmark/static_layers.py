"""Static maps that tell the benchmark where each reference can be trusted and why a disagreement happens.

  worldcover   ESA WorldCover 2021 v200, 10 m land cover (public COGs on AWS, no account). Herbaceous wetland (90)
               and mangroves (95): plants hide the water from optical sensors, so an optical "not water" there is
               not trusted.
  occurrence   JRC Global Surface Water 1984-2021, share of months with water (0-100 %; public COGs on Google
               Cloud Storage, no account). Seasonal ground (banks that dry out at low water) and permanent water
               explain mud and wind disagreements.

Both are read once onto the area grid and kept in the cache.
"""
import math
import os

import numpy as np

from lifeline.benchmark.optical import _cached
from lifeline.sources.occurrence import (  # noqa: F401  (shared with the worker; kept importable from here)
    NO_DATA,
    OCCURRENCE_URL,
    first_valid,
    occurrence_tiles,
    read_layer,
)

WORLDCOVER_URL = ("https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/"
                  "ESA_WorldCover_10m_2021_v200_{tile}_Map.tif")
WETLAND, MANGROVES = 90, 95


def _ns(lat):
    return f"{'N' if lat >= 0 else 'S'}{abs(lat):02d}"


def _ew(lon):
    return f"{'E' if lon >= 0 else 'W'}{abs(lon):03d}"


def worldcover_tiles(bbox):
    """WorldCover tile names (3 x 3 degrees, named by the south-west corner, e.g. S06W066) covering a bbox."""
    lon0, lat0, lon1, lat1 = bbox
    lats = range(math.floor(lat0 / 3) * 3, math.ceil(lat1 / 3) * 3, 3)
    lons = range(math.floor(lon0 / 3) * 3, math.ceil(lon1 / 3) * 3, 3)
    return [f"{_ns(la)}{_ew(lo)}" for la in lats for lo in lons]


def load(area, cache_dir, read_band=None):
    """{worldcover, occurrence} on the area grid (uint8, NO_DATA where unknown), through the cache."""
    path = os.path.join(cache_dir, "static", f"{area['id']}_layers.npz")

    def build():
        # WorldCover marks no data with 0; the occurrence tiles with 255
        wc = first_valid([read_layer(WORLDCOVER_URL.format(tile=t), area, 0, read_band)
                          for t in worldcover_tiles(area["bbox"])])
        occ = first_valid([read_layer(OCCURRENCE_URL.format(tile=t), area, NO_DATA, read_band)
                           for t in occurrence_tiles(area["bbox"])])
        return {"worldcover": wc, "occurrence": occ}
    return _cached(path, build)


def optical_blind(worldcover, classes=(WETLAND, MANGROVES)):
    """Pixels where plants hide the water from optical sensors: their "not water" is not trusted."""
    return np.isin(worldcover, classes)
