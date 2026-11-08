import os
import unittest

import numpy as np

from lifeline.catalog import (catalog_path, classify_communities, community_class, evaluate, hub_target, load_catalog,
                              pass_dir, refresh_changes, save_catalog, wide_water_of)
from lifeline.config import STATUS
from lifeline.layers import save_mask

from .helpers import TempDirTest, river_scene, small_area


def pass_entry(date, status, time_utc="10:00"):
    return {"date": date, "time_utc": time_utc, "evaluated": True, "status": status}


class TestClassification(unittest.TestCase):
    AREA = {"access_radius_m": 1000}

    def test_classification_uses_the_whole_record(self):
        cat = {"communities": [{"id": "a"}, {"id": "b"}, {"id": "c"}],
               "passes": [pass_entry("2026-01-01", {"a": [1, 100, 50], "b": [3, None, 300], "c": [3, None, 4000]}),
                          pass_entry("2026-01-07", {"a": [3, None, 900], "b": [3, None, 250], "c": [3, None, 4200]})]}
        classify_communities(self.AREA, cat)
        cls = {c["id"]: c["class"] for c in cat["communities"]}
        self.assertEqual(cls, {"a": "monitored", "b": "unresolved", "c": "inland"})
        self.assertEqual(cat["passes"][0]["counts"]["connected"], 1)
        self.assertEqual(cat["community_classes"], {"monitored": 1, "unresolved": 1, "inland": 1, "no_data": 0})

    def test_links_only_through_unresolvable_creeks_do_not_make_a_place_monitored(self):
        cat = {"communities": [{"id": "a"}, {"id": "b"}],
               "passes": [pass_entry("2026-01-01", {"a": [2, 0, 60], "b": [2, 40, 60]}),
                          pass_entry("2026-01-07", {"a": [3, None, 60], "b": [3, None, 60]})]}
        classify_communities(self.AREA, cat)
        self.assertEqual({c["id"]: c["class"] for c in cat["communities"]}, {"a": "unresolved", "b": "monitored"})

    def test_isolation_needs_two_passes_in_a_row(self):
        p = lambda d, code: pass_entry(d, {"a": [code, None if code == 3 else 100, 50]})  # noqa: E731
        cat = {"communities": [{"id": "a"}],
               "passes": [p("2026-01-01", 1), p("2026-01-07", 3), p("2026-01-13", 0), p("2026-01-19", 3), p("2026-01-25", 1)]}
        classify_communities(self.AREA, cat)
        counts = [(q["counts"]["at_risk"], q["counts"]["isolated"]) for q in cat["passes"]]
        # 1st isolated pass: at risk (to confirm); no-data pass skipped; next isolated pass confirms
        self.assertEqual(counts, [(0, 0), (1, 0), (0, 0), (0, 1), (0, 0)])
        self.assertEqual(cat["passes"][1]["unconfirmed"], ["a"])

    def test_passes_are_taken_in_time_order_whatever_the_catalog_order(self):
        cat = {"communities": [{"id": "a"}],
               "passes": [pass_entry("2026-01-13", {"a": [3, None, 50]}), pass_entry("2026-01-01", {"a": [1, 100, 50]}),
                          pass_entry("2026-01-07", {"a": [3, None, 50]})]}
        classify_communities(self.AREA, cat)
        self.assertEqual(cat["passes"][0]["counts"]["isolated"], 1)   # 13 Jan confirms 7 Jan
        self.assertEqual(cat["passes"][2]["unconfirmed"], ["a"])

    def test_community_missing_from_an_older_pass_counts_as_no_data(self):
        # "b" was added to the community list after the first pass was processed
        cat = {"communities": [{"id": "a"}, {"id": "b"}],
               "passes": [pass_entry("2026-01-01", {"a": [1, 100, 50]}),
                          pass_entry("2026-01-07", {"a": [1, 100, 50], "b": [1, 200, 30]})]}
        classify_communities(self.AREA, cat)
        self.assertEqual(cat["passes"][0]["counts"], {"no_data": 1, "connected": 1, "at_risk": 0, "isolated": 0})
        self.assertEqual(cat["passes"][1]["counts"]["connected"], 2)

    def test_partial_passes_are_ignored(self):
        cat = {"communities": [{"id": "a"}],
               "passes": [{"date": "2026-01-01", "time_utc": "10:00", "evaluated": False}]}
        classify_communities(self.AREA, cat)
        self.assertEqual(cat["communities"][0]["class"], "no_data")
        self.assertNotIn("counts", cat["passes"][0])

    def test_community_class_rules(self):
        self.assertEqual(community_class([None, [0, None, None]], 1000), "no_data")
        self.assertEqual(community_class([[3, None, 1500]], 1000), "inland")
        self.assertEqual(community_class([[2, 0, 50], [3, None, 50]], 1000), "unresolved")
        self.assertEqual(community_class([[2, 40, 50]], 1000), "monitored")


class TestEvaluate(unittest.TestCase):
    def setUp(self):
        self.area = small_area(px_m=20.0, hub={"name": "Hub", "lon": -64.80 + 20.5 * 0.0002,
                                               "lat": -3.40 - 100.5 * 0.0002, "radius_m": 200})
        self.water, self.valid = river_scene(channel_px=2)   # 40 m channel to the lake
        self.wide = wide_water_of(self.area, self.water)
        self.communities = [{"id": "river", "lon": -64.80 + 31.5 * 0.0002, "lat": -3.40 - 20.5 * 0.0002},
                            {"id": "pond", "lon": -64.80 + 105.5 * 0.0002, "lat": -3.40 - 185.5 * 0.0002},
                            {"id": "lake", "lon": 0, "lat": 0,   # its access point is on the lake shore
                             "access": [-64.80 + 262.5 * 0.0002, -3.40 - 100.5 * 0.0002]}]

    def test_full_pass_gets_statistics_status_hub_link_and_counts(self):
        entry = {"status": "stale"}
        evaluate(self.area, self.communities, self.water, self.valid, self.wide, entry)
        self.assertEqual(entry["coverage"], 1.0)
        self.assertTrue(entry["evaluated"] and entry["shown"])
        self.assertAlmostEqual(entry["water_km2"], round(self.water.sum() * 0.0004, 2))
        self.assertGreater(entry["narrow_km2"], 0)
        self.assertEqual({k: v[0] for k, v in entry["status"].items()},
                         {"river": STATUS["connected"], "pond": STATUS["isolated"], "lake": STATUS["at_risk"]})
        self.assertEqual(entry["counts"], {"no_data": 0, "connected": 1, "at_risk": 1, "isolated": 1})
        self.assertEqual(entry["hub_link"][0], STATUS["connected"])

    def test_partial_pass_is_shown_but_not_evaluated(self):
        valid = self.valid.copy()
        valid[:, 100:] = False
        entry = {"status": {"old": [1, 100, 0]}, "counts": {}, "hub_link": [1, 100, 0]}
        evaluate(self.area, self.communities, self.water & valid, valid, self.wide & valid, entry)
        self.assertAlmostEqual(entry["coverage"], 1 / 3, places=3)
        self.assertTrue(entry["shown"])
        self.assertFalse(entry["evaluated"])
        self.assertFalse({"status", "counts", "hub_link"} & set(entry))

    def test_hub_target_uses_the_water_access(self):
        area = small_area(hub={"name": "Hub", "lon": -64.79, "lat": -3.41, "radius_m": 500,
                               "access": {"lon": -64.80 + 0.5 * 0.0002, "lat": -3.40 - 0.5 * 0.0002}})
        self.assertEqual(hub_target(area), (0, 0, 500))


class TestCatalogFiles(TempDirTest):
    def test_new_catalog_has_the_area_grid_and_communities(self):
        area = small_area(circle=None, secret="not published")
        cat = load_catalog(area, [{"id": "a"}], self.tmp)
        self.assertEqual(cat["passes"], [])
        self.assertNotIn("secret", cat["area"])
        self.assertEqual(cat["grid"]["bounds"], [[-3.44, -64.80], [-3.40, -64.74]])
        self.assertEqual(cat["grid"]["pixel_m"], 22.3)
        self.assertEqual(cat["status_codes"], {"0": "no_data", "1": "connected", "2": "at_risk", "3": "isolated"})
        self.assertEqual(cat["communities"], [{"id": "a"}])

    def test_save_sorts_passes_and_load_keeps_them(self):
        area = small_area()
        cat = load_catalog(area, [], self.tmp)
        cat["passes"] = [{"id": "b", "date": "2026-02-01", "time_utc": "10:00"},
                         {"id": "a2", "date": "2026-01-01", "time_utc": "22:00"},
                         {"id": "a1", "date": "2026-01-01", "time_utc": "10:00"}]
        cat["last_search"] = "2026-11-08T10:00:00Z"
        save_catalog(area, cat, self.tmp)
        self.assertFalse(os.path.exists(catalog_path(area, self.tmp) + ".tmp"))
        again = load_catalog(area, [{"id": "new"}], self.tmp)
        self.assertEqual([p["id"] for p in again["passes"]], ["a1", "a2", "b"])
        self.assertEqual(again["last_search"], "2026-11-08T10:00:00Z")
        self.assertEqual(again["communities"], [{"id": "new"}])


class TestRefreshChanges(TempDirTest):
    def store(self, area, pid, water):
        os.makedirs(pass_dir(area, pid, self.tmp))
        save_mask(water, np.ones_like(water), os.path.join(pass_dir(area, pid, self.tmp), "water.npz"))

    def test_change_against_the_previous_shown_pass_of_the_same_track(self):
        area = small_area(px_m=100.0)   # 0.01 km² per pixel
        full, empty = np.ones((4, 4), bool), np.zeros((4, 4), bool)
        half = full.copy()
        half[:, :2] = False
        for pid, water in (("p1", full), ("p2", half), ("p3", empty), ("q1", empty)):
            self.store(area, pid, water)
        mk = lambda pid, date, track, shown=True: {"id": pid, "date": date, "track": track, "shown": shown,  # noqa: E731
                                                   "files": {}}
        cat = {"passes": [mk("p3", "2026-01-25", 1), mk("p2", "2026-01-13", 1, shown=False), mk("p1", "2026-01-01", 1),
                          mk("q1", "2026-01-05", 2)]}
        refresh_changes(area, cat, self.tmp)
        p3, p2, p1, q1 = cat["passes"]
        self.assertEqual(p3["change"], {"since": "p1", "lost_km2": 0.16, "gained_km2": 0.0})   # p2 is hidden
        self.assertEqual(p3["files"]["change"], "change.png")
        self.assertTrue(os.path.exists(os.path.join(pass_dir(area, "p3", self.tmp), "change.png")))
        self.assertNotIn("change", p1)
        self.assertNotIn("change", q1)
        self.assertNotIn("change", p2)

    def test_up_to_date_changes_and_missing_masks_are_skipped(self):
        area = small_area()
        self.store(area, "p1", np.ones((2, 2), bool))
        cat = {"passes": [{"id": "p1", "date": "2026-01-01", "track": 1, "files": {}},
                          {"id": "p2", "date": "2026-01-13", "track": 1, "files": {}},
                          {"id": "p3", "date": "2026-01-25", "track": 1, "files": {}, "change": {"since": "p2"}}]}
        refresh_changes(area, cat, self.tmp)
        self.assertNotIn("change", cat["passes"][1])
        self.assertEqual(cat["passes"][2]["change"], {"since": "p2"})


if __name__ == "__main__":
    unittest.main()
