"""Small geographic and text helpers."""
import math
import unicodedata

M_PER_DEG_LON_EQUATOR = 111320.0
M_PER_DEG_LAT = 110570.0


def metres(lon_a, lat_a, lon_b, lat_b):
    """Distance in metres between two nearby points (equirectangular approximation)."""
    k = math.cos(math.radians((lat_a + lat_b) / 2))
    return math.hypot((lon_a - lon_b) * M_PER_DEG_LON_EQUATOR * k, (lat_a - lat_b) * M_PER_DEG_LAT)


def fold(name):
    """Place name without accents, lower case: 'Alvarães ' -> 'alvaraes'."""
    return unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower().strip()
