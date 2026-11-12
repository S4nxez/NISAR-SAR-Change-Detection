import math
import unittest

import numpy as np

from lifeline.geometry.area import area_mask, area_wkt, circle_bbox, in_area, load_area, to_px
from lifeline.geometry.geo import fold, metres

from ..helpers import TempDirTest, small_area


class TestGeo(unittest.TestCase):
    def test_one_degree_of_latitude_is_about_110_km(self):
        self.assertAlmostEqual(metres(-64.0, -3.0, -64.0, -4.0), 110570.0, delta=1.0)

    def test_longitude_shrinks_with_latitude(self):
        at_equator = metres(0.0, 0.0, 1.0, 0.0)
        at_60 = metres(0.0, 60.0, 1.0, 60.0)
        self.assertAlmostEqual(at_60 / at_equator, 0.5, places=3)

    def test_fold_drops_accents_case_and_spaces(self):
        self.assertEqual(fold("  Alvarães "), "alvaraes")
        self.assertEqual(fold("São Francisco do Itauba"), "sao francisco do itauba")


class TestLoadArea(TempDirTest):
    def test_circle_gives_the_square_around_it_and_the_grid(self):
        self.write_json("c.json", {"id": "c", "circle": {"lon": -64.75, "lat": -3.40, "radius_km": 10},
                                   "step_deg": 0.002})
        area = load_area("c", self.tmp)
        lon0, lat0, lon1, lat1 = area["bbox"]
        self.assertAlmostEqual(lat1 - lat0, 2 * 10000 / 110570.0, places=4)
        self.assertAlmostEqual((lon0 + lon1) / 2, -64.75, places=4)
        self.assertEqual((area["nx"], area["ny"]), (90, 90))
        self.assertAlmostEqual(area["px_m"], 0.002 * 111320 * math.sqrt(math.cos(math.radians(-3.40))), places=3)

    def test_box_area_keeps_its_bbox(self):
        self.write_json("b.json", {"id": "b", "bbox": [-65.0, -4.0, -64.0, -3.0], "step_deg": 0.01})
        area = load_area("b", self.tmp)
        self.assertEqual(area["bbox"], [-65.0, -4.0, -64.0, -3.0])
        self.assertEqual((area["nx"], area["ny"]), (100, 100))

    def test_circle_bbox_is_rounded_to_five_decimals(self):
        bbox = circle_bbox({"lon": -64.75, "lat": -3.40, "radius_km": 55})
        self.assertTrue(all(round(v, 5) == v for v in bbox))


class TestGrid(unittest.TestCase):
    AREA = small_area()

    def test_north_west_corner_is_pixel_zero(self):
        self.assertEqual(to_px(self.AREA, -64.80 + 0.0001, -3.40 - 0.0001), (0, 0))

    def test_pixel_of_a_point_inside(self):
        self.assertEqual(to_px(self.AREA, -64.77 + 0.0001, -3.42 - 0.0001), (100, 150))

    def test_points_outside_the_grid_get_indices_outside_it(self):
        row, col = to_px(self.AREA, -64.80 - 0.0001, -3.40 + 0.0001)
        self.assertEqual((row, col), (-1, -1))   # not truncated to the edge pixel

    def test_wkt_is_the_closed_bbox(self):
        self.assertEqual(area_wkt(self.AREA), "POLYGON((-64.8 -3.44,-64.74 -3.44,-64.74 -3.4,-64.8 -3.4,-64.8 -3.44))")

    def test_box_area_mask_is_the_whole_grid(self):
        self.assertTrue(area_mask(self.AREA).all())
        self.assertTrue(in_area(self.AREA, -64.77, -3.42))
        self.assertFalse(in_area(self.AREA, -64.70, -3.42))


class TestCircularArea(unittest.TestCase):
    AREA = {"circle": {"lon": -64.75, "lat": -3.40, "radius_km": 10}, "bbox": [-64.84, -3.4905, -64.66, -3.3095],
            "step_deg": 0.002, "nx": 90, "ny": 90}

    def test_mask_is_a_disc_filling_about_pi_over_four_of_the_grid(self):
        m = area_mask(self.AREA)
        self.assertTrue(m[45, 45])
        self.assertFalse(m[0, 0])
        self.assertAlmostEqual(m.mean(), np.pi / 4, delta=0.03)

    def test_places_in_the_corner_of_the_grid_are_outside_the_area(self):
        self.assertTrue(in_area(self.AREA, -64.75, -3.40))
        self.assertFalse(in_area(self.AREA, -64.835, -3.485))   # inside the box, outside the disc


if __name__ == "__main__":
    unittest.main()
