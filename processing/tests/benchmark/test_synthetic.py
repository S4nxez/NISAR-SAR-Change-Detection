import json
import os
import unittest
from unittest import mock

import numpy as np

from lifeline.benchmark import synthetic
from lifeline.config import AREAS_DIR
from lifeline.geometry.area import load_area

CODE = synthetic.SURFACE_CODE


class TestScene(unittest.TestCase):
    def lane(self, name):
        return next(i for i, lane in enumerate(synthetic.LANES) if lane[0] == name)

    def at(self, e, s):
        return int(synthetic.surfaces_at(np.array([e]), np.array([s]))[0])

    def test_surfaces_follow_the_lane_layout(self):
        y = synthetic.lane_centre(self.lane("channel_200m"))
        self.assertEqual(self.at(400, y), CODE["water"])                     # river
        self.assertEqual(self.at(2000, y), CODE["water"])                    # channel
        self.assertEqual(self.at(2000, y + 150), CODE["forest"])             # beside the channel
        self.assertEqual(self.at(synthetic.COMMUNITY_X, y), CODE["water"])   # lake
        veg = synthetic.lane_centre(self.lane("vegetation_block"))
        self.assertEqual(self.at(2000, veg), CODE["flooded_vegetation"])
        self.assertEqual(self.at(1500, veg), CODE["water"])
        self.assertEqual(self.at(2000, synthetic.lane_centre(self.lane("mud_bar"))), CODE["mud"])

    def test_narrow_channels_have_their_width(self):
        y = synthetic.lane_centre(self.lane("channel_40m"))
        s = y + np.arange(-40, 41, 5.0)
        codes = synthetic.surfaces_at(np.full(s.shape, 2000.0), s)
        self.assertEqual(int((codes == CODE["water"]).sum()) * 5, 45)   # 40 m, both edges included at 5 m steps

    def test_speckle_has_the_mean_and_spread_of_its_looks(self):
        rng = np.random.default_rng(1)
        v = synthetic.speckled(np.full(200_000, -10.0, np.float32), 4, rng)
        self.assertAlmostEqual(float(v.mean()), 0.1, places=3)
        self.assertAlmostEqual(float(v.std() / v.mean()), 0.5, places=2)   # 1 / sqrt(looks)

    def test_the_scene_area_keeps_the_method_parameters(self):
        base = {"id": "tefe", "water_db": -14.0, "speckle_m": 60, "widths_m": [40, 60], "safe_width_m": 60,
                "circle": {"lon": 0, "lat": 0, "radius_km": 1}, "gauge": {"ana_code": "1"}, "step_deg": 0.00018,
                "new_rule": 3, "sentinel1": {"max_days": 4}}
        area, _ = synthetic.scene_area(base, (-64.80, -3.40))
        self.assertEqual((area["water_db"], area["new_rule"], area["id"]), (-14.0, 3, "synthetic"))
        self.assertNotIn("circle", area)
        self.assertNotIn("gauge", area)
        self.assertNotIn("sentinel1", area)      # no real scenes over simulated lanes (and no network in tests)


class TestRun(unittest.TestCase):
    @mock.patch("lifeline.pipeline.log")
    def test_run_grades_every_lane_once_per_seed(self, _log):
        out = synthetic.run(load_area("tefe", AREAS_DIR), looks=4, seeds=[7, 8])
        self.assertEqual(set(out["lanes"]), {lane[0] for lane in synthetic.LANES})
        self.assertEqual(sum(out["totals"].values()), 2 * len(synthetic.LANES))
        self.assertEqual(out["lanes"]["channel_400m"]["grades"], {"correct": 2})   # a wide channel is always found
        self.assertEqual(set(out["surfaces"]), set(synthetic.SURFACES))
        json.dumps(out)
        self.assertFalse(any(name.startswith("lifeline-synthetic-") for name in os.listdir(".")))


if __name__ == "__main__":
    unittest.main()
