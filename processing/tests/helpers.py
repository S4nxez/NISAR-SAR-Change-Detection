"""Shared fixtures of the processing tests (no network access, no real NISAR product)."""
import json
import os
import shutil
import tempfile
import unittest

import numpy as np

PX = 20.0
WIDTHS = [40, 60, 100, 200, 400]


def river_scene(channel_px=3):
    """200 x 300 px: a wide river (400 m) on the left with the hub, joined by a narrow channel
    to a lake on the right, plus a detached pond at the bottom."""
    water = np.zeros((200, 300), bool)
    water[:, 10:30] = True                      # river, 20 px = 400 m wide
    water[97:97 + channel_px, 30:200] = True    # channel
    water[60:140, 200:260] = True               # lake
    water[180:190, 100:110] = True              # detached pond
    return water, np.ones_like(water)


def small_area(**extra):
    """A 0.06 x 0.04 degree box area on a 0.0002 degree grid (300 x 200 px, about 22 m)."""
    area = {"id": "test", "name": "Test area", "bbox": [-64.80, -3.44, -64.74, -3.40], "step_deg": 0.0002,
            "nx": 300, "ny": 200, "px_m": 22.26, "hub": {"name": "Hub", "lon": -64.796, "lat": -3.42, "radius_m": 200},
            "river": {"name": "River", "lon": -64.796, "lat": -3.405, "radius_m": 200},
            "access_radius_m": 400, "safe_width_m": 60, "widths_m": WIDTHS, "water_db": -15.0,
            "min_coverage": 0.8, "min_coverage_shown": 0.05, "communities": "test_communities.geojson"}
    area.update(extra)
    return area


def scene_db(water, valid=None):
    """Backscatter (dB) of a water scene: -20 dB water, -5 dB land, NaN outside `valid`."""
    db = np.where(water, -20.0, -5.0).astype(np.float32)
    if valid is not None:
        db[~valid] = np.nan
    return db


class FakeResponse:
    """The parts of requests.Response the code uses."""

    def __init__(self, status_code=200, content=b"", json_data=None, headers=None, url="https://cdn.example/signed"):
        self.status_code, self.content, self._json = status_code, content, json_data
        self.headers, self.url = headers or {}, url

    def json(self):
        if self._json is None:
            raise ValueError("no JSON")
        return self._json

    def raise_for_status(self):
        import requests
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


class TempDirTest(unittest.TestCase):
    """A test case with a fresh temporary directory in self.tmp."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="lifeline-test-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def write_json(self, relpath, data):
        path = os.path.join(self.tmp, relpath)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return path

    def read_json(self, relpath):
        with open(os.path.join(self.tmp, relpath), encoding="utf-8") as f:
            return json.load(f)
