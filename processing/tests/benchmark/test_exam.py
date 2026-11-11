import datetime as dt
import os
import unittest
from unittest import mock

import numpy as np

from lifeline.benchmark import exam, report
from lifeline.output.catalog import pass_dir
from lifeline.output.layers import save_mask

from ..helpers import TempDirTest, river_scene, small_area

C, R, ISO, N = 1, 2, 3, 0


def evaluated(pid, status, water_km2=10.0):
    return {"id": pid, "date": pid[:10], "evaluated": True, "status": status, "water_km2": water_km2}


class TestGauge(TempDirTest):
    def test_level_on_the_day_or_the_closest_one(self):
        series = [["2026-08-30", 900.0], ["2026-09-02", 850.0]]
        self.assertEqual(exam.gauge_level(series, "2026-08-30"), 900.0)
        self.assertEqual(exam.gauge_level(series, "2026-08-31"), 900.0)
        self.assertIsNone(exam.gauge_level(series, "2026-09-05"))

    def test_lost_routes_fall_with_the_river_and_the_series_is_cached(self):
        area = small_area()
        gauge = {"source": "ANA", "series": [["2026-08-01", 1200.0], ["2026-09-01", 1000.0], ["2026-10-01", 800.0]]}
        cat = {"gauge": gauge, "passes": [
            evaluated("2026-08-01_t1", {"a": [C, 200, 10], "b": [C, 200, 10]}, 30.0),
            evaluated("2026-09-01_t1", {"a": [ISO, None, 10], "b": [C, 200, 10]}, 20.0),
            evaluated("2026-10-01_t1", {"a": [ISO, None, 10], "b": [ISO, None, 300], "c": [ISO, None, 9000]}, 10.0)]}
        g = exam.gauge_section(area, cat, self.tmp)
        self.assertEqual([r["lost_route"] for r in g["passes"]], [0, 1, 2])   # c is inland, not a lost route
        self.assertEqual((g["water_vs_level"]["rho"], g["lost_route_vs_level"]["rho"]), (1.0, -1.0))
        again = exam.gauge_section(area, {"passes": cat["passes"]}, self.tmp)   # ANA down: cached series
        self.assertEqual(again["lost_route_vs_level"]["rho"], -1.0)
        self.assertEqual(exam.gauge_section(area, {"passes": []}, os.path.join(self.tmp, "x")), {"available": False})


class TestField(unittest.TestCase):
    def test_checks_match_by_name_within_their_dates(self):
        communities = [{"id": "osm1", "name": "Caiambé"}, {"id": "osm2", "name": "Vila Nova"}]
        cat = {"passes": [evaluated("2026-08-01_t1", {"osm1": [C, 200, 10], "osm2": [ISO, None, 10]}),
                          evaluated("2026-09-01_t1", {"osm1": [N, None, None], "osm2": [R, 40, 10]}),
                          evaluated("2026-12-01_t1", {"osm1": [ISO, None, 10]})]}
        truth = {"checks": [
            {"community": "CAIAMBE", "expected": "linked", "kind": "sanity", "from": "2026-06-01", "to": "2026-11-30",
             "source": "s"},
            {"community": "Vila Nova", "expected": "isolated", "kind": "field", "from": "2026-07-01",
             "to": "2026-09-30", "source": "s"},
            {"community": "Missing", "expected": "isolated", "kind": "field", "from": "2026-01-01", "to": "2026-12-31",
             "source": "s"}]}
        f = exam.field_section(cat, communities, truth)
        self.assertEqual([len(r["passes"]) for r in f["checks"]], [1, 2, 0])   # no data and out of dates skipped
        self.assertEqual([x["correct"] for x in f["checks"][1]["passes"]], [True, False])
        self.assertFalse(f["checks"][2]["found"])
        self.assertEqual(f["by_kind"]["field"], {"checks": 2, "judged": 2, "correct": 1})
        self.assertEqual(f["correct_share"], round(2 / 3, 4))


class TestPasses(TempDirTest):
    def test_passes_are_searched_once_and_must_all_exist(self):
        found = {"p1": {"id": "p1", "granules": [{"start": dt.datetime(2026, 8, 1)}]}, "p2": {"id": "p2", "granules": []}}
        search = mock.Mock(return_value=found)
        area = small_area()
        self.assertEqual(list(exam.frozen_passes(area, {"passes": ["p1"]}, self.tmp, search)), ["p1"])
        exam.frozen_passes(area, {"passes": ["p2"]}, self.tmp, search)
        search.assert_called_once()
        with self.assertRaises(SystemExit):
            exam.frozen_passes(area, {"passes": ["p9"]}, self.tmp, search)

    def test_run_record_empties_the_run_folder_and_uses_the_cache(self):
        run_dir = os.path.join(self.tmp, "run")
        os.makedirs(os.path.join(run_dir, "old"))
        seen = {}

        def update(area, workers, out_root, areas_dir, search, token):
            seen.update(cache=os.environ.get("MONITOR_CACHE_DIR"), passes=search(area), old=os.path.exists(
                os.path.join(out_root, "old")))
            return {"passes": []}
        exam.run_record({"id": "a"}, {"p": {}}, "/cache", run_dir, 2, update=update)
        self.assertEqual(seen, {"cache": "/cache", "passes": {"p": {}}, "old": False})


class TestOptical(TempDirTest):
    def test_passes_with_a_reference_are_scored_and_pooled(self):
        area = small_area(px_m=20.0, access_radius_m=100)
        water, valid = river_scene(channel_px=3)
        pdir = pass_dir(area, "2026-08-30_t1", self.tmp)
        os.makedirs(pdir)
        save_mask(water, valid, os.path.join(pdir, "water.npz"))
        cat = {"passes": [evaluated("2026-08-30_t1", {"a": [C, 60, 0]}), {"id": "x", "date": "2026-08-31"}]}
        communities = [{"id": "a", "name": "A", "lon": -64.7567, "lat": -3.4195}]   # in the lake

        def reference(area, date, in_mask, cache, max_days, min_clear, post):
            ref = water.copy()
            ref[97:100, 30:200] = False                # Sentinel-2 sees no channel: the lake is cut off
            return {"date": date, "days_apart": 0, "clear_share": 1.0, "threshold": 0.0, "water": ref,
                    "valid": np.ones_like(ref)}
        out = exam.optical_section(area, cat, communities, self.tmp, self.tmp, {"max_days": 2, "min_clear": 0.3},
                                   reference=reference)
        self.assertEqual(out["summary"]["passes"], 1)
        self.assertEqual(out["summary"]["false_route"], 1)          # the method links a community S2 does not
        self.assertEqual(out["summary"]["recall_by_width"]["wide_ge200m"], 1.0)
        self.assertLess(out["summary"]["precision"], 1.0)


class TestRunAndReport(TempDirTest):
    @mock.patch("lifeline.pipeline.log")
    @mock.patch("lifeline.benchmark.exam.log")
    def test_a_synthetic_run_writes_the_result_and_the_index(self, *_):
        exam_path = self.write_json("exam.json", {"version": 1, "passes": [], "optical": {},
                                                  "synthetic": {"looks": 4, "seeds": [3]}})
        truth_path = self.write_json("truth.json", {"checks": []})
        history = os.path.join(self.tmp, "history")
        now = dt.datetime(2026, 11, 11, 12, 0, tzinfo=dt.timezone.utc)
        from lifeline.geometry.area import load_area
        area = load_area("tefe")
        result, jpath, mpath = exam.run(area, "baseline", self.tmp, exam_path=exam_path, truth_path=truth_path,
                                        history_dir=history, skip_real=True, now=now)
        self.assertTrue(jpath.endswith("20261111T120000Z_baseline.json") and os.path.exists(mpath))
        self.assertIn("synthetic_dangerous", result["scorecard"])
        self.assertIsNone(result["scorecard"]["optical_iou"])
        with open(os.path.join(history, "README.md"), encoding="utf-8") as f:
            index = f.read()
        self.assertIn("[baseline](20261111T120000Z_baseline.md)", index)
        with open(mpath, encoding="utf-8") as f:
            self.assertIn("## Synthetic scenes", f.read())

    def test_markdown_of_a_full_result(self):
        syn = {"seeds": [1], "looks": 4, "lanes": {"l": {"expected": "connected", "grades": {"correct": 1}}},
               "totals": {"correct": 1, "conservative": 0, "dangerous": 0, "no_data": 0}, "correct_share": 1.0,
               "surfaces_db": {"water": [-23, -30]}, "surfaces": {"water": {"as_water": 0.9}}}
        opt = {"rules": {"max_days": 2, "min_clear": 0.3},
               "summary": {"passes": 1, "iou": 0.8, "f1": 0.9, "precision": 0.9, "recall": 0.9,
                           "recall_by_width": {"narrow_lt60m": 0.5}, "false_water": {"shore": 0.1},
                           "status_pairs": 3, "status_agreement": 0.66, "status_kappa_mean": 0.4, "false_route": 1,
                           "overconfident": 0, "false_isolated": 0},
               "passes": [{"pass": "p", "s2_date": "d", "days_apart": 0, "clear_share": 1.0, "water": {
                   "iou": 0.8, "recall_by_width": {"narrow_lt60m": {"recall": 0.5}}},
                   "status": {"agreement": 0.66, "false_route": 1, "false_isolated": 0}}]}
        result = {"label": "x", "exam_version": 1, "created_utc": "t", "commit": "abc", "dirty": True,
                  "synthetic": syn, "optical": opt,
                  "gauge": {"available": True, "source": "ANA", "water_vs_level": {"rho": 0.8, "n": 9},
                            "lost_route_vs_level": {"rho": -0.7, "n": 9}},
                  "field": {"checks": [{"community": "A", "expected": "linked", "kind": "sanity", "found": True,
                                        "passes": [{"correct": True}], "source": "s"}]},
                  "classes": {"monitored": 3}}
        result["scorecard"] = exam.scorecard(result)
        text = report.markdown(result)
        for part in ("(uncommitted changes)", "## Real passes against Sentinel-2", "## River gauge",
                     "## Field and report checks", "| 0.800 |", "| – |"):
            self.assertIn(part, text)


if __name__ == "__main__":
    unittest.main()
