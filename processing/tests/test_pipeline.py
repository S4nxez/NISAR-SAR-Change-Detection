import os
import unittest
from unittest import mock

import numpy as np

from lifeline import pipeline
from lifeline.catalog import catalog_path, pass_dir
from lifeline.places import communities_collection, save_communities

from .helpers import TempDirTest, river_scene, scene_db, small_area

LON0, LAT1, STEP = -64.80, -3.40, 0.0002


def lonlat(row, col):
    return LON0 + (col + 0.5) * STEP, LAT1 - (row + 0.5) * STEP


def scene_area():
    hub_lon, hub_lat = lonlat(100, 20)
    river_lon, river_lat = lonlat(10, 20)
    return small_area(px_m=20.0, hub={"name": "Hub", "lon": hub_lon, "lat": hub_lat, "radius_m": 200},
                      river={"name": "River", "lon": river_lon, "lat": river_lat, "radius_m": 200})


def found_pass(pid="2026-10-23_t161A", date="2026-10-23"):
    return {"id": pid, "date": date, "time_utc": "10:02", "track": 161, "direction": "ascending", "frames": [176],
            "modes": ["2005_DHDH"], "beta": False, "granules": [{"url": "u"}]}


class SyncExecutor:
    """ProcessPoolExecutor stand-in that runs the jobs in this process."""

    def __init__(self, max_workers):
        self.max_workers = max_workers

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def map(self, fn, jobs):
        return map(fn, jobs)


@mock.patch("lifeline.pipeline.log")
@mock.patch("lifeline.catalog.log", create=True)
class TestPipeline(TempDirTest):
    def setUp(self):
        super().setUp()
        self.area = scene_area()
        river_lon, river_lat = lonlat(20, 31)
        lake_lon, lake_lat = lonlat(100, 262)
        places = [{"id": "osm1", "name": "Riverside", "place": "hamlet", "lon": river_lon, "lat": river_lat},
                  {"id": "osm2", "name": "Lakeside", "place": "hamlet", "lon": lake_lon, "lat": lake_lat}]
        save_communities(self.area, communities_collection(self.area, places), self.tmp)
        water, _ = river_scene(channel_px=2)
        self.db = scene_db(water)
        self.read = mock.Mock(return_value=(self.db.copy(), 12.34, 20.0))
        self.patch_read = mock.patch("lifeline.pipeline.read_pass", self.read)
        self.patch_read.start()
        self.addCleanup(self.patch_read.stop)
        self.patch_gauge = mock.patch("lifeline.pipeline.refresh_gauge")
        self.gauge = self.patch_gauge.start()
        self.addCleanup(self.patch_gauge.stop)

    def update(self, found, **kw):
        return pipeline.update(self.area, out_root=self.tmp, areas_dir=self.tmp, search=lambda area: found,
                               token=lambda: "tok", executor=SyncExecutor, **kw)

    def test_process_pass_writes_the_layers_and_returns_the_entry(self, *_):
        entry = pipeline.process_pass(self.area, [], found_pass(), self.tmp, "tok", read=self.read)
        pdir = pass_dir(self.area, "2026-10-23_t161A", self.tmp)
        self.assertEqual(sorted(os.listdir(pdir)), ["radar.webp", "water.npz", "water.png"])
        self.assertEqual((entry["read_mb"], entry["spacing_m"], entry["track"]), (12.3, 20.0, 161))
        self.assertEqual(entry["files"], {"radar": "radar.webp", "water": "water.png"})
        self.assertTrue(entry["evaluated"])
        self.assertNotIn("granules", entry)

    def test_update_processes_new_passes_and_classifies_the_record(self, *_):
        cat = self.update({"2026-10-23_t161A": found_pass()})
        self.assertEqual([p["id"] for p in cat["passes"]], ["2026-10-23_t161A"])
        status = cat["passes"][0]["status"]
        self.assertEqual({k: v[0] for k, v in status.items()}, {"osm1": 1, "osm2": 2})
        self.assertEqual(cat["community_classes"]["monitored"], 1)   # the lake is only linked through a creek
        self.assertIn("last_search", cat)
        self.assertTrue(os.path.exists(catalog_path(self.area, self.tmp)))
        self.gauge.assert_called_once()

    def test_update_skips_known_passes_unless_redo(self, *_):
        self.update({"2026-10-23_t161A": found_pass()})
        self.read.reset_mock()
        self.update({"2026-10-23_t161A": found_pass()})
        self.read.assert_not_called()
        self.update({"2026-10-23_t161A": found_pass()}, redo=True)
        self.read.assert_called_once()

    def test_update_without_new_passes_needs_no_token(self, *_):
        token = mock.Mock()
        pipeline.update(self.area, out_root=self.tmp, areas_dir=self.tmp, search=lambda area: {}, token=token,
                        executor=SyncExecutor)
        token.assert_not_called()

    def test_a_failed_pass_is_logged_and_the_others_are_kept(self, *_):
        good = self.read.return_value
        self.read.side_effect = [RuntimeError("HTTP 500"), good]
        cat = self.update({"2026-10-11_t161A": found_pass("2026-10-11_t161A", "2026-10-11"),
                           "2026-10-23_t161A": found_pass()})
        self.assertEqual([p["id"] for p in cat["passes"]], ["2026-10-23_t161A"])

    def test_reevaluate_rebuilds_the_record_from_stored_masks(self, *_):
        self.update({"2026-10-11_t161A": found_pass("2026-10-11_t161A", "2026-10-11"),
                     "2026-10-23_t161A": found_pass()})
        self.read.reset_mock()
        cat = pipeline.reevaluate(self.area, out_root=self.tmp, areas_dir=self.tmp)
        self.read.assert_not_called()
        self.assertEqual(cat["passes"][1]["change"], {"since": "2026-10-11_t161A", "lost_km2": 0.0, "gained_km2": 0.0})
        self.assertEqual([p["counts"]["connected"] for p in cat["passes"]], [1, 1])

    def test_pending_passes_order_and_limit(self, *_):
        found = {pid: {"id": pid, "date": pid} for pid in ("2026-03", "2026-01", "2026-02")}
        cat = {"passes": [{"id": "2026-02"}]}
        self.assertEqual([p["id"] for p in pipeline.pending_passes(found, cat)], ["2026-01", "2026-03"])
        self.assertEqual([p["id"] for p in pipeline.pending_passes(found, cat, redo=True, limit=2)], ["2026-02", "2026-03"])

    def test_describe_partial_and_evaluated_passes(self, *_):
        base = {"id": "p", "coverage": 0.5, "water_km2": 1.0, "read_mb": 2.0, "seconds": 3.0}
        self.assertIn("not evaluated", pipeline.describe(base))
        counts = {"connected": 4, "at_risk": 2, "isolated": 1}
        self.assertIn("connected 4 / at risk 2 / isolated 1", pipeline.describe({**base, "counts": counts}))


@mock.patch("lifeline.pipeline.log")
class TestCommunitiesAndWatch(TempDirTest):
    def test_communities_writes_the_file_from_openstreetmap(self, _log):
        area = small_area(access_snap_m={"default": 300})
        answers = {"place": [{"id": 1, "lon": -64.77, "lat": -3.42, "tags": {"name": "Alpha", "place": "hamlet"}}],
                   "pier": [{"lon": -64.7705, "lat": -3.4205, "tags": {"man_made": "pier"}}]}

        def query(q):
            return answers["place"] if '"place"' in q else answers["pier"]

        fc = pipeline.communities(area, self.tmp, query=query)
        self.assertEqual(fc["features"][0]["properties"]["access_source"], "pier")
        self.assertEqual(self.read_json("test_communities.geojson")["features"][0]["properties"]["name"], "Alpha")

    def test_watch_keeps_going_after_a_failed_round(self, _log):
        run = mock.Mock(side_effect=[RuntimeError("ASF down"), None])
        sleep = mock.Mock()
        pipeline.watch({"id": "a"}, hours=0.5, workers=3, run=run, sleep=sleep, rounds=2)
        self.assertEqual(run.call_args_list, [mock.call({"id": "a"}, 3)] * 2)
        sleep.assert_called_with(1800.0)
        self.assertEqual(sleep.call_count, 2)


class TestProcessJob(unittest.TestCase):
    def test_errors_become_text_so_the_batch_keeps_running(self):
        with mock.patch("lifeline.pipeline.process_pass", side_effect=ValueError("bad product")):
            pid, entry, err = pipeline._process_job(({}, [], {"id": "p"}, "/tmp", "tok"))
        self.assertEqual((pid, entry), ("p", None))
        self.assertIn("bad product", err)

    def test_partial_coverage_pixels_outside_a_circle_are_not_data(self):
        area = scene_area()
        area["circle"] = {"lon": LON0 + 150 * STEP, "lat": LAT1 - 100 * STEP, "radius_km": 1.0}
        db = np.full((area["ny"], area["nx"]), -5.0, np.float32)
        with mock.patch("lifeline.pipeline.save_radar"), mock.patch("lifeline.pipeline.save_water"), \
                mock.patch("lifeline.pipeline.save_mask"), mock.patch("lifeline.pipeline.os.makedirs"):
            entry = pipeline.process_pass(area, [], found_pass(), "/nonexistent", "tok",
                                          read=lambda *a: (db, 1.0, 20.0))
        self.assertEqual(entry["coverage"], 1.0)   # coverage is measured inside the circle only


if __name__ == "__main__":
    unittest.main()
