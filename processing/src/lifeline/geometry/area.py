"""Area files (processing/areas/<id>.json), the lon/lat grid shared by all passes and the area mask."""
import json
import math
import os

import numpy as np

from lifeline.config import AREAS_DIR
from lifeline.geometry.geo import M_PER_DEG_LAT, M_PER_DEG_LON_EQUATOR, metres


def circle_bbox(circle):
    """[lon0, lat0, lon1, lat1] of the square around a circle {lon, lat, radius_km}."""
    r = circle["radius_km"] * 1000.0
    dlat = r / M_PER_DEG_LAT
    dlon = r / (M_PER_DEG_LON_EQUATOR * math.cos(math.radians(circle["lat"])))
    return [round(circle["lon"] - dlon, 5), round(circle["lat"] - dlat, 5),
            round(circle["lon"] + dlon, 5), round(circle["lat"] + dlat, 5)]


def load_area(area_id, areas_dir=AREAS_DIR):
    """Read an area file and add its grid: bbox (from the circle if there is one), nx, ny, px_m."""
    with open(os.path.join(areas_dir, area_id + ".json"), encoding="utf-8") as f:
        area = json.load(f)
    if area.get("circle"):
        # circular area: the grid is the square around it, pixels outside the circle are not part of it
        area["bbox"] = circle_bbox(area["circle"])
    lon0, lat0, lon1, lat1 = area["bbox"]
    step = area["step_deg"]
    area["nx"] = int(round((lon1 - lon0) / step))
    area["ny"] = int(round((lat1 - lat0) / step))
    lat_mid = math.radians((lat0 + lat1) / 2)
    area["px_m"] = step * M_PER_DEG_LON_EQUATOR * math.sqrt(math.cos(lat_mid))  # geometric mean of x and y size
    return area


def to_px(area, lon, lat):
    """lon/lat -> (row, col) on the area grid (row 0 at the north edge). Outside the grid gives
    negative or too large indices, never the edge pixel."""
    lon0, _, _, lat1 = area["bbox"]
    step = area["step_deg"]
    return math.floor((lat1 - lat) / step), math.floor((lon - lon0) / step)


def in_area(area, lon, lat):
    """True when the point is in the area: inside the bbox and, for a circular area, the circle."""
    lon0, lat0, lon1, lat1 = area["bbox"]
    if not (lon0 <= lon <= lon1 and lat0 <= lat <= lat1):
        return False
    c = area.get("circle")
    return not c or metres(lon, lat, c["lon"], c["lat"]) <= c["radius_km"] * 1000.0


def area_mask(area):
    """Grid pixels that belong to the area (all of them for a box, the disc for a circle)."""
    c = area.get("circle")
    if not c:
        return np.ones((area["ny"], area["nx"]), bool)
    lon0, _, _, lat1 = area["bbox"]
    step = area["step_deg"]
    k = math.cos(math.radians(c["lat"]))
    x = ((lon0 + (np.arange(area["nx"]) + 0.5) * step) - c["lon"]) * M_PER_DEG_LON_EQUATOR * k
    y = ((lat1 - (np.arange(area["ny"]) + 0.5) * step) - c["lat"]) * M_PER_DEG_LAT
    return (x[None, :] ** 2 + y[:, None] ** 2) <= (c["radius_km"] * 1000.0) ** 2


def area_wkt(area):
    """The area's bbox as a WKT polygon, for the ASF search."""
    lon0, lat0, lon1, lat1 = area["bbox"]
    return f"POLYGON(({lon0} {lat0},{lon1} {lat0},{lon1} {lat1},{lon0} {lat1},{lon0} {lat0}))"


def area_transform(area):
    """Affine transform of the area grid (rasterio; only the commands that read COGs need it)."""
    from rasterio.transform import from_origin
    lon0, _, _, lat1 = area["bbox"]
    return from_origin(lon0, lat1, area["step_deg"], area["step_deg"])
