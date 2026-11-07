"""Areas of interest.

``SEARCH_BBOX`` is a generous lon/lat rectangle around the Tule (DWR basin 5-022.13) and Tulare Lake (5-022.12)
subbasins, used only to search for products. The official subbasin boundaries (DWR Bulletin 118) are loaded in the
support-layer step and are the ones used for clipping and aggregation.
"""

from __future__ import annotations

# (west, south, east, north), degrees, EPSG:4326
SEARCH_BBOX: tuple[float, float, float, float] = (-120.05, 35.75, -118.85, 36.45)


def bbox_to_wkt(bbox: tuple[float, float, float, float]) -> str:
    """Closed WKT polygon of a (west, south, east, north) bounding box."""
    west, south, east, north = bbox
    if not (west < east and south < north):
        raise ValueError(f"invalid bbox {bbox}: expected west < east and south < north")
    corners = [(west, south), (east, south), (east, north), (west, north), (west, south)]
    return "POLYGON((" + ",".join(f"{x} {y}" for x, y in corners) + "))"
