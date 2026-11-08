import unittest

import numpy as np

from lifeline.config import STATUS
from lifeline.water import (MIN_HOLE_PX, MIN_WATER_PX, connectivity, coverage_around, disk, near_labels,
                            route_status, water_mask, wide_water, width_mask)

from .helpers import PX, WIDTHS, river_scene


class TestConnectivity(unittest.TestCase):
    def run_scene(self, water, valid, targets):
        hub = (100, 20, 200)  # row, col, radius in metres
        return connectivity(water, valid, PX, hub, targets, WIDTHS, access_m=400, safe_m=60)

    def test_wide_river_is_connected(self):
        water, valid = river_scene()
        (st, b, d), = self.run_scene(water, valid, [(20, 31)])
        self.assertEqual(st, STATUS["connected"])
        self.assertEqual(b, 200)  # 400 m river, measured conservatively (one pixel less) -> 200-400 m class
        self.assertEqual(d, 2 * PX)  # the bank pixel next to the river is land; water is two pixels away

    def test_lake_behind_60_m_channel_takes_the_channel_width(self):
        water, valid = river_scene(channel_px=3)
        (st, b, _), = self.run_scene(water, valid, [(100, 262)])
        self.assertEqual(b, 60)
        self.assertEqual(st, STATUS["connected"])

    def test_lake_behind_40_m_channel_is_at_risk(self):
        water, valid = river_scene(channel_px=2)
        (st, b, _), = self.run_scene(water, valid, [(100, 262)])
        self.assertEqual(b, 0)  # even widths are rounded down one pixel: safer to warn early
        self.assertEqual(st, STATUS["at_risk"])

    def test_cut_channel_isolates_the_lake(self):
        water, valid = river_scene()
        water[:, 120:124] = False   # dry 80 m of channel
        water[:, 10:30] = True
        (st, b, _), = self.run_scene(water, valid, [(100, 262)])
        self.assertEqual(st, STATUS["isolated"])
        self.assertIsNone(b)

    def test_diagonal_one_pixel_creek_still_links_the_lake(self):
        water, valid = river_scene(channel_px=0)
        for i in range(170):  # staircase creek from the river to the lake, touching only at corners
            water[100 + (i % 2), 30 + i] = True
        (st, b, _), = self.run_scene(water, valid, [(100, 262)])
        self.assertEqual(st, STATUS["at_risk"])
        self.assertEqual(b, 0)

    def test_outside_a_circular_area_is_not_a_data_gap(self):
        water, valid = river_scene()
        yy, xx = np.mgrid[:200, :300]
        inside = (yy - 100) ** 2 + (xx - 150) ** 2 <= 160 ** 2   # disc holding river, channel and lake
        valid &= inside
        water &= inside
        (st, b, _), = connectivity(water, valid, PX, (100, 20, 200), [(100, 262)], WIDTHS, 400, 60, inside)
        self.assertEqual(st, STATUS["connected"])
        self.assertEqual(b, 60)

    def test_detached_pond_is_isolated_and_far_place_is_isolated(self):
        water, valid = river_scene()
        res = self.run_scene(water, valid, [(185, 105), (150, 150)])
        self.assertEqual(res[0][0], STATUS["isolated"])
        self.assertEqual(res[1][0], STATUS["isolated"])
        self.assertGreater(res[1][2], 200)

    def test_missing_data_is_not_called_isolated(self):
        water, valid = river_scene()
        valid[:, 190:] = False
        (st, b, d), = self.run_scene(water, valid, [(100, 262)])
        self.assertEqual((st, b, d), (STATUS["no_data"], None, None))

    def test_route_through_a_data_gap_is_undetermined(self):
        water, valid = river_scene()
        valid[:, 100:120] = False   # the pass misses a strip across the channel
        water[:, 100:120] = False
        (st, _, _), = self.run_scene(water, valid, [(100, 262)])
        self.assertEqual(st, STATUS["no_data"])

    def test_target_outside_the_grid_has_no_data(self):
        water, valid = river_scene()
        self.assertEqual(self.run_scene(water, valid, [(-5, 20), (100, 400)]),
                         [[STATUS["no_data"], None, None]] * 2)

    def test_hub_away_from_water_links_nothing(self):
        water, valid = river_scene()
        res = connectivity(water, valid, PX, (150, 150, 20), [(20, 31)], WIDTHS, 400, 60)   # hub on dry land
        self.assertEqual(res[0][0], STATUS["isolated"])


class TestRouteHelpers(unittest.TestCase):
    def test_route_status_rules(self):
        self.assertEqual(route_status(200, 40.0, False, 400, 60), [STATUS["connected"], 200, 40])
        self.assertEqual(route_status(60, 40.0, False, 400, 60), [STATUS["connected"], 60, 40])
        self.assertEqual(route_status(40, 40.0, False, 400, 60), [STATUS["at_risk"], 40, 40])
        self.assertEqual(route_status(0, 40.0, False, 400, 60), [STATUS["at_risk"], 0, 40])
        self.assertEqual(route_status(-1, 40.0, False, 400, 60), [STATUS["isolated"], None, 40])
        self.assertEqual(route_status(200, 500.0, False, 400, 60), [STATUS["isolated"], 200, 500])
        self.assertEqual(route_status(-1, 40.0, True, 400, 60), [STATUS["no_data"], None, 40])
        self.assertEqual(route_status(-1, 500.0, True, 400, 60), [STATUS["isolated"], None, 500])

    def test_coverage_around_counts_only_area_pixels(self):
        valid = np.ones((10, 10), bool)
        valid[:, :5] = False
        in_mask = np.ones_like(valid)
        self.assertAlmostEqual(coverage_around(valid, in_mask, 5, 5, 2), 0.6)
        in_mask[:, :5] = False
        self.assertEqual(coverage_around(valid, in_mask, 5, 5, 2), 1.0)
        self.assertIsNone(coverage_around(valid, in_mask, 12, 5, 2))
        self.assertIsNone(coverage_around(valid, in_mask, 5, 1, 1))   # only pixels outside the area around

    def test_width_mask_keeps_channel_centre_lines(self):
        water = np.zeros((9, 9), bool)
        water[:, 2:7] = True   # 5 px channel
        from scipy import ndimage
        inside = ndimage.distance_transform_edt(water) * PX
        self.assertTrue((width_mask(water, inside, 0, PX) == water).all())
        self.assertEqual(int(width_mask(water, inside, 60, PX)[4].sum()), 3)
        self.assertFalse(width_mask(water, inside, 200, PX).any())

    def test_disk_and_near_labels_at_the_edge(self):
        self.assertEqual(int(disk(1).sum()), 5)
        labels = np.zeros((5, 5), int)
        labels[0, 0], labels[4, 4] = 1, 2
        self.assertEqual(near_labels(labels, 0, 1, 1), {1})
        self.assertEqual(near_labels(labels, 2, 2, 3), {1, 2})
        self.assertEqual(near_labels(labels, 20, 20, 1), set())


class TestWaterMask(unittest.TestCase):
    def test_specks_removed_and_small_holes_filled(self):
        db = np.full((100, 100), -5.0, np.float32)
        db[20:80, 20:80] = -20.0      # lake
        db[50, 50] = -5.0             # one bright pixel inside the lake (wind, boat)
        db[5:7, 5:7] = -20.0          # 4 px speck
        water, valid = water_mask(db, -15.0)
        self.assertTrue(water[50, 50])
        self.assertFalse(water[5, 5])
        self.assertTrue(valid.all())

    def test_size_limits(self):
        db = np.full((60, 60), -5.0, np.float32)
        db[2:7, 2:7] = -20.0                      # exactly MIN_WATER_PX: kept
        db[20:50, 20:50] = -20.0
        db[30:35, 30:40] = -5.0                   # MIN_HOLE_PX island: kept as land
        water, _ = water_mask(db, -15.0)
        self.assertEqual((MIN_WATER_PX, MIN_HOLE_PX), (25, 50))
        self.assertTrue(water[4, 4])
        self.assertFalse(water[32, 35])

    def test_nan_is_not_valid_and_not_water(self):
        db = np.full((40, 40), -20.0, np.float32)
        db[:, :10] = np.nan
        water, valid = water_mask(db, -15.0)
        self.assertFalse(valid[:, :10].any())
        self.assertFalse(water[:, :10].any())
        self.assertTrue(water[:, 10:].all())

    def test_hysteresis_keeps_rough_water_attached_to_calm_water(self):
        db = np.full((60, 100), -6.0, np.float32)
        db[20:40, :] = -20.0          # river
        db[20:40, 40:60] = -13.0      # wind-roughened stretch across the river
        db[50:58, 10:20] = -13.0      # darkish field, not touching water
        cut, _ = water_mask(db, -15.0)
        joined, _ = water_mask(db, -15.0, -12.0)
        self.assertFalse(cut[30, 50])
        self.assertTrue(joined[30, 50])
        self.assertFalse(joined[54, 15])

    def test_weak_threshold_below_the_strong_one_is_ignored(self):
        db = np.full((40, 40), -6.0, np.float32)
        db[10:30, 10:30] = -20.0
        a, _ = water_mask(db, -15.0)
        b, _ = water_mask(db, -15.0, -18.0)
        self.assertTrue((a == b).all())


class TestWideWater(unittest.TestCase):
    def test_narrow_channels_are_not_wide_water(self):
        water, _ = river_scene(channel_px=2)
        from scipy import ndimage
        wide = wide_water(water, ndimage.distance_transform_edt(water) * PX, 60, PX)
        self.assertTrue(wide[100, 20])        # river
        self.assertFalse(wide[97, 120])       # 40 m channel
        self.assertTrue(wide[100, 230])       # lake
        self.assertFalse((wide & ~water).any())


if __name__ == "__main__":
    unittest.main()
