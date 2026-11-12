import unittest

import numpy as np

from lifeline.analysis.water import (
    MIN_HOLE_PX,
    MIN_WATER_PX,
    connectivity,
    coverage_around,
    disk,
    ki_threshold,
    low_water_route,
    mixed_tiles,
    near_labels,
    pass_thresholds,
    route_status,
    seasonal_ground,
    vegetated_water,
    water_mask,
    wide_water,
    width_mask,
)
from lifeline.config import STATUS

from ..helpers import PX, WIDTHS, river_scene


def two_class_scene(water_db=-22.0, land_db=-7.0, seed=0):
    """400 x 400 px: water on the west 30 %, land elsewhere, with Gaussian spread in dB."""
    rng = np.random.default_rng(seed)
    db = rng.normal(land_db, 2.0, (400, 400)).astype(np.float32)
    db[:, :120] = rng.normal(water_db, 1.5, (400, 120))
    return db


class TestPassThreshold(unittest.TestCase):
    ADAPTIVE = {"range_db": [-20.0, -13.0], "tile_m": 2000, "min_tiles": 2}

    def area(self, **kw):
        return {"water_db": -15.0, "water_db_weak": -12.0, "px_m": 20.0, **kw}

    def test_ki_cuts_between_the_two_classes(self):
        t = ki_threshold(two_class_scene().ravel())
        self.assertTrue(-18.0 < t < -11.0, t)
        self.assertTrue(np.isnan(ki_threshold(np.array([np.nan, 3.0]))))
        self.assertTrue(np.isnan(ki_threshold(np.full(100, -10.0))))

    def test_only_mixed_and_complete_tiles_are_used(self):
        db = two_class_scene()
        db[300:, :] = np.nan                                  # gappy bottom row of tiles
        tiles = mixed_tiles(db, 100, -15.0)
        self.assertEqual(sorted((t[0].start, t[1].start) for t in tiles), [(0, 100), (100, 100), (200, 100)])

    def test_fixed_thresholds_without_the_adaptive_setting(self):
        self.assertEqual(pass_thresholds(self.area(), two_class_scene()),
                         (-15.0, -12.0, {"source": "fixed", "strong_db": -15.0, "weak_db": -12.0}))

    def test_adaptive_threshold_is_measured_and_keeps_the_weak_offset(self):
        strong, weak, info = pass_thresholds(self.area(water_db_adaptive=self.ADAPTIVE), two_class_scene())
        self.assertEqual(info["source"], "adaptive")
        self.assertTrue(-18.0 < strong < -13.0)
        self.assertAlmostEqual(weak - strong, 3.0)
        self.assertEqual(info["tiles"], 4)                    # the column of tiles across the shore

    def test_adaptive_threshold_is_clamped_to_its_range(self):
        rng = np.random.default_rng(2)
        db = rng.normal(-6.0, 0.3, (400, 400)).astype(np.float32)
        db[:, :200] = rng.normal(-16.0, 0.3, (400, 200))      # water and land 10 dB apart: KI cuts near -11 dB
        strong, weak, info = pass_thresholds(self.area(water_db_adaptive={**self.ADAPTIVE, "tile_m": 8000,
                                                                          "min_tiles": 1}), db)
        self.assertGreater(info["measured_db"], -13.0)
        self.assertEqual((strong, weak, info["source"]), (-13.0, -10.0, "adaptive"))

    def test_too_few_mixed_tiles_fall_back_to_the_fixed_threshold(self):
        land = np.full((400, 400), -7.0, np.float32)
        strong, weak, info = pass_thresholds(self.area(water_db_adaptive=self.ADAPTIVE), land)
        self.assertEqual((strong, weak, info["source"], info["tiles"]), (-15.0, -12.0, "fixed", 0))


class TestVegetatedWater(unittest.TestCase):
    CFG = {"hh_min_db": -4.0, "ratio_min_db": 7.0, "near_water_m": 1000}

    def scene(self):
        """100 x 200 px: a river on the left, flooded vegetation beside it, dry forest, and a bright patch far
        from any water (a town or a field of the same double bounce)."""
        hh = np.full((100, 200), -7.0, np.float32)
        hv = np.full((100, 200), -12.5, np.float32)
        water = np.zeros((100, 200), bool)
        water[:, :20] = True
        hh[:, :20], hv[:, :20] = -23.0, -30.0
        hh[20:60, 20:40], hv[20:60, 20:40] = -1.0, -9.5      # flooded vegetation next to the river
        hh[20:60, 120:140], hv[20:60, 120:140] = -1.0, -9.5  # same signature 2 km from the water
        hh[70:90, 60:80], hv[70:90, 60:80] = -1.0, -6.0      # bright but with bright HV: not double bounce
        hh[5, 30], hv[5, 30] = -1.0, -9.5                    # a single speck
        return hh, hv, water

    def test_flooded_vegetation_near_water_is_flagged(self):
        hh, hv, water = self.scene()
        v = vegetated_water(hh, hv, water, self.CFG, PX)
        self.assertTrue(v[20:60, 20:40].all())
        self.assertFalse(v[20:60, 120:140].any())             # too far from open water
        self.assertFalse(v[70:90, 60:80].any())               # HH - HV only 5 dB
        self.assertFalse(v[5, 30])                            # specks under 1 ha are dropped
        self.assertFalse((v & water).any())
        self.assertFalse(v[:, 45:120].any())                  # dry forest

    def test_no_layer_without_hv_or_without_the_setting(self):
        hh, hv, water = self.scene()
        self.assertIsNone(vegetated_water(hh, None, water, self.CFG, PX))
        self.assertIsNone(vegetated_water(hh, hv, water, None, PX))
        self.assertFalse(vegetated_water(hh, hv, np.zeros_like(water), self.CFG, PX).any())


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


class TestLowWaterRoute(unittest.TestCase):
    RULE = {"gauge_max_cm": 1200, "seasonal_pct": [30, 90], "patch_radius_m": 60}

    def setUp(self):
        # the river and a lake joined by a channel; the lake is a bed that drains at low water (60 % of the months)
        self.water, _ = river_scene(channel_px=3)
        self.occ = np.full(self.water.shape, 98, np.uint8)
        self.occ[60:140, 200:260] = 60

    def test_seasonal_ground_is_the_band_between_rarely_and_always_water(self):
        occ = np.array([[0, 29, 30, 60, 89, 90, 100, 255]], np.uint8)
        np.testing.assert_array_equal(seasonal_ground(occ, 30, 90),
                                      [[False, False, True, True, True, False, False, False]])

    def test_a_drained_bed_leaves_the_routes_at_low_water(self):
        route, applied = low_water_route(self.water, self.occ, 800.0, self.RULE, PX)
        self.assertTrue(applied)
        self.assertFalse(route[63:137, 203:257].any())   # an opening may leave a few corner pixels of the bed
        self.assertLess(route[60:140, 200:260].sum(), 0.02 * 80 * 60)
        np.testing.assert_array_equal(route[:, :200], self.water[:, :200])   # river and channel kept

    def test_nothing_changes_at_high_water_or_without_a_rule_layer_or_level(self):
        for occ, level, rule in ((self.occ, 1500.0, self.RULE), (self.occ, 1200.0 + 0.1, self.RULE),
                                 (None, 800.0, self.RULE), (self.occ, None, self.RULE), (self.occ, 800.0, None)):
            route, applied = low_water_route(self.water, occ, level, rule, PX)
            self.assertFalse(applied)
            self.assertIs(route, self.water)
        self.assertTrue(low_water_route(self.water, self.occ, 1200.0, self.RULE, PX)[1])   # the limit is included

    def test_thin_seasonal_banks_new_channels_and_unknown_ground_are_kept(self):
        occ = np.full(self.water.shape, 98, np.uint8)
        occ[:, 10:12] = 60      # a 40 m seasonal fringe along the river bank: not a broad bed
        occ[:, 15:25] = 10      # the river now runs over ground that was rarely water: a new channel
        occ[60:140, 200:260] = 255   # no occurrence data on the lake
        route, applied = low_water_route(self.water, occ, 800.0, self.RULE, PX)
        self.assertTrue(applied)
        np.testing.assert_array_equal(route, self.water)


if __name__ == "__main__":
    unittest.main()
