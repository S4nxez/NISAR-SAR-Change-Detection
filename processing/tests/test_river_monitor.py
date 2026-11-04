"""Tests of the river lifeline monitor without network access:
python -m unittest discover -s processing/tests"""
import os
import sys
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from river_monitor import (STATUS, assign_access, classify_communities, connectivity,  # noqa: E402
                           parse_name, water_mask)

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
        water[:, 120:124] = water[:, 120:124] & ~(np.arange(200)[:, None] >= 0)  # dry 80 m of channel
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
        self.assertEqual(st, STATUS["no_data"])

    def test_route_through_a_data_gap_is_undetermined(self):
        water, valid = river_scene()
        valid[:, 100:120] = False   # the pass misses a strip across the channel
        water[:, 100:120] = False
        (st, _, _), = self.run_scene(water, valid, [(100, 262)])
        self.assertEqual(st, STATUS["no_data"])


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


class TestAccess(unittest.TestCase):
    SNAP = {"town": 3000, "hamlet": 500, "default": 300}

    def test_town_takes_its_port_and_the_port_is_not_a_community(self):
        places = [{"name": "Alvarães", "place": "town", "lon": -64.8148, "lat": -3.2156},
                  {"name": "Porto de Alvaraes", "place": "locality", "lon": -64.8044, "lat": -3.2110}]
        kept = assign_access(places, [], self.SNAP)
        self.assertEqual([p["name"] for p in kept], ["Alvarães"])
        self.assertEqual(kept[0]["access"], [-64.8044, -3.2110])
        self.assertIn("Porto de Alvaraes", kept[0]["access_source"])

    def test_nearest_landing_within_the_limit_of_the_place_type(self):
        landing = [{"lon": -64.810, "lat": -3.211, "kind": "ferry terminal"}]   # ~600 m away
        town = {"name": "A", "place": "town", "lon": -64.8148, "lat": -3.2140}
        hamlet = {"name": "B", "place": "hamlet", "lon": -64.8148, "lat": -3.2140}
        a, = assign_access([town], landing, self.SNAP)
        b, = assign_access([hamlet], landing, self.SNAP)
        self.assertEqual(a["access_source"], "ferry terminal")
        self.assertNotIn("access", b)

    def test_a_far_port_with_the_same_name_is_ignored(self):
        places = [{"name": "Nazaré", "place": "hamlet", "lon": -64.53, "lat": -3.17},
                  {"name": "Porto Nazaré", "place": "hamlet", "lon": -64.90, "lat": -3.60}]   # ~60 km apart
        kept = assign_access(places, [], self.SNAP)
        self.assertEqual(len(kept), 2)
        self.assertNotIn("access", kept[0])


class TestCatalog(unittest.TestCase):
    def test_parse_name(self):
        g = parse_name("NISAR_L2_PR_GCOV_033_161_A_176_2005_DHDH_A_20261023T100258_20261023T100332_P05023_N_F_J_001.h5")
        self.assertEqual((g["track"], g["direction"], g["frame"], g["mode"], g["pol"]), (161, "A", 176, "2005", "DHDH"))
        self.assertEqual(g["start"].strftime("%Y-%m-%d %H:%M"), "2026-10-23 10:02")

    def test_classification_uses_the_whole_record(self):
        area = {"access_radius_m": 1000}
        p = lambda d, st: {"date": d, "time_utc": "10:00", "evaluated": True, "status": st}  # noqa: E731
        cat = {"communities": [{"id": "a"}, {"id": "b"}, {"id": "c"}],
               "passes": [p("2026-01-01", {"a": [1, 100, 50], "b": [3, None, 300], "c": [3, None, 4000]}),
                          p("2026-01-07", {"a": [3, None, 900], "b": [3, None, 250], "c": [3, None, 4200]})]}
        classify_communities(area, cat)
        cls = {c["id"]: c["class"] for c in cat["communities"]}
        self.assertEqual(cls, {"a": "monitored", "b": "unresolved", "c": "inland"})
        self.assertEqual(cat["passes"][0]["counts"]["connected"], 1)

    def test_links_only_through_unresolvable_creeks_do_not_make_a_place_monitored(self):
        area = {"access_radius_m": 1000}
        p = lambda d, st: {"date": d, "time_utc": "10:00", "evaluated": True, "status": st}  # noqa: E731
        cat = {"communities": [{"id": "a"}, {"id": "b"}],
               "passes": [p("2026-01-01", {"a": [2, 0, 60], "b": [2, 40, 60]}),
                          p("2026-01-07", {"a": [3, None, 60], "b": [3, None, 60]})]}
        classify_communities(area, cat)
        self.assertEqual({c["id"]: c["class"] for c in cat["communities"]}, {"a": "unresolved", "b": "monitored"})

    def test_isolation_needs_two_passes_in_a_row(self):
        area = {"access_radius_m": 1000}
        p = lambda d, code: {"date": d, "time_utc": "10:00", "evaluated": True,  # noqa: E731
                             "status": {"a": [code, None if code == 3 else 100, 50]}}
        cat = {"communities": [{"id": "a"}],
               "passes": [p("2026-01-01", 1), p("2026-01-07", 3), p("2026-01-13", 0), p("2026-01-19", 3), p("2026-01-25", 1)]}
        classify_communities(area, cat)
        counts = [(q["counts"]["at_risk"], q["counts"]["isolated"]) for q in cat["passes"]]
        # 1st isolated pass: at risk (to confirm); no-data pass skipped; next isolated pass confirms
        self.assertEqual(counts, [(0, 0), (1, 0), (0, 0), (0, 1), (0, 0)])
        self.assertEqual(cat["passes"][1]["unconfirmed"], ["a"])


if __name__ == "__main__":
    unittest.main()
