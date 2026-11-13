import datetime as dt
import os
import unittest
from unittest import mock

import numpy as np

from lifeline.sources import sentinel1

from ..helpers import FakeResponse, TempDirTest, small_area

CFG = {"max_days": 4, "level_tolerance_cm": 30, "water_db": -18.0, "weak_db": -16.0, "land_db": -16.0}


def item(date, href="https://blob.example/vv.tiff", orbit=54):
    return {"properties": {"datetime": f"{date}T10:03:39Z", "sat:relative_orbit": orbit},
            "assets": {"vv": {"href": href}, "vh": {"href": href.replace("vv", "vh")}}}


class TestScenes(unittest.TestCase):
    def test_search_asks_for_the_window_around_the_pass(self):
        post = mock.Mock(return_value=FakeResponse(json_data={"features": [item("2026-10-25")]}))
        area = small_area()
        out = sentinel1.search_scenes(area, dt.date(2026, 10, 23), 4, post)
        self.assertEqual(len(out), 1)
        url, body = post.call_args.args[0], post.call_args.kwargs["json"]
        self.assertEqual(url, sentinel1.STAC_SEARCH)
        self.assertEqual(body["collections"], ["sentinel-1-rtc"])
        self.assertEqual(body["datetime"], "2026-10-19T00:00:00Z/2026-10-27T23:59:59Z")
        self.assertEqual(body["bbox"], area["bbox"])

    def test_by_date_groups_tiles_and_skips_items_without_vv(self):
        no_vv = {"properties": {"datetime": "2026-10-20T09:55:20Z"}, "assets": {"vh": {"href": "x"}}}
        got = sentinel1.by_date([item("2026-10-20"), item("2026-10-20", orbit=156), no_vv, item("2026-10-25")])
        self.assertEqual({k: len(v) for k, v in got.items()}, {"2026-10-20": 2, "2026-10-25": 1})

    def test_urls_are_signed_with_the_access_token(self):
        get = mock.Mock(return_value=FakeResponse(json_data={"token": "st=1&sig=abc", "msft:expiry": "x"}))
        token = sentinel1.access_token(get)
        self.assertEqual(get.call_args.args[0], sentinel1.SAS_TOKEN)
        self.assertEqual(sentinel1.signed("https://b/vv.tiff", token), "https://b/vv.tiff?st=1&sig=abc")
        self.assertEqual(sentinel1.signed("https://b/vv.tiff?a=1", token), "https://b/vv.tiff?a=1&st=1&sig=abc")

    def test_usable_dates_closest_first_within_the_window_and_the_river_level(self):
        series = [["2026-10-19", 836.0], ["2026-10-20", 827.0], ["2026-10-23", 797.0], ["2026-10-25", 783.5],
                  ["2026-10-26", 760.0], ["2026-10-27", 750.0]]
        dates = ["2026-10-18", "2026-10-20", "2026-10-25", "2026-10-26", "2026-10-27"]
        # 10-18 is 5 days away; 10-26 and 10-27: the river had fallen more than 30 cm below the pass level
        self.assertEqual(sentinel1.usable_dates(dates, "2026-10-23", series, 4, 30), ["2026-10-25", "2026-10-20"])
        # without a gauge the window alone decides; on a tie the earlier scene comes first
        self.assertEqual(sentinel1.usable_dates(["2026-10-25", "2026-10-21"], "2026-10-23", None, 4, 30),
                         ["2026-10-21", "2026-10-25"])
        # an unknown level on the scene day (gap in the series) does not exclude the scene
        self.assertEqual(sentinel1.usable_dates(["2026-10-22"], "2026-10-23", series, 4, 30), ["2026-10-22"])


class TestClasses(unittest.TestCase):
    def test_to_db_marks_missing_and_non_positive_power(self):
        got = sentinel1.to_db(np.array([[0.01, 0.0, np.nan, -1.0]], np.float32))
        self.assertAlmostEqual(float(got[0, 0]), -20.0, places=4)
        self.assertTrue(np.isnan(got[0, 1:]).all())

    def test_classify_water_land_and_undecided(self):
        vv = np.full((40, 40), -8.0, np.float32)    # land
        vv[:, :20] = -21.0                           # open water
        vv[:, 20:22] = -17.0                         # wind-roughened edge touching the water: water
        vv[10:20, 30:39] = -17.0                     # isolated pixels between the thresholds: undecided
        vv[30:, 30:] = np.nan                        # no scene
        got = sentinel1.classify(vv, CFG)
        self.assertTrue(got["water"][:, :22].all())
        self.assertFalse(got["water"][:, 22:].any())
        self.assertFalse(got["land"][10:20, 30:39].any() or got["water"][10:20, 30:39].any())
        self.assertTrue(got["land"][0:10, 22:].all())
        self.assertFalse(got["seen"][30:, 30:].any() or got["land"][30:, 30:].any())

    def test_agreement_counts_only_pixels_both_judged(self):
        water = np.zeros((10, 10), bool)
        water[:, :5] = True
        valid = np.ones_like(water)
        valid[9, :] = False
        view = {"dates": ["2026-10-25"], "water": np.zeros_like(water), "land": np.zeros_like(water)}
        view["water"][:, :4] = True        # NISAR has one more column of water (column 4)
        view["land"][:, 4:8] = True        # columns 8-9 undecided
        got = sentinel1.agreement(water, valid, view, 20.0)
        self.assertEqual(got["judged_km2"], round(72 * 0.0004, 1))
        self.assertEqual(got["agreement"], round(63 / 72, 4))
        self.assertEqual((got["both_water_km2"], got["nisar_only_km2"], got["sentinel1_only_km2"]),
                         (round(36 * 0.0004, 2), round(9 * 0.0004, 2), 0.0))
        self.assertIsNone(sentinel1.agreement(water, valid, {**view, "land": view["water"] * False,
                                                             "water": view["water"] * False}, 20.0)["agreement"])


class TestReading(TempDirTest):
    def setUp(self):
        super().setUp()
        self.area = small_area()
        self.calls = []

    def read(self, url, area):
        """Fake COG reader: tile A covers the west half (-20 dB), tile B everything (-5 dB)."""
        self.calls.append(url)
        out = np.full((area["ny"], area["nx"]), np.nan, np.float32)
        if "/a/" in url:
            out[:, :150] = 0.01
        else:
            out[:] = 10 ** -0.5
        return out

    def test_mosaic_first_tile_with_data_wins(self):
        vv = sentinel1.mosaic_date(self.area, [item("2026-10-25", "https://b/a/vv.tiff"),
                                               item("2026-10-25", "https://b/b/vv.tiff")], "tok", self.read)
        self.assertAlmostEqual(float(vv[0, 0]), -20.0, places=4)
        self.assertAlmostEqual(float(vv[0, 299]), -5.0, places=4)
        self.assertTrue(all(u.endswith("vv.tiff?tok") for u in self.calls))

    def test_a_filtered_date_is_read_once_through_the_cache(self):
        items = [item("2026-10-25", "https://b/a/vv.tiff")]
        token = mock.Mock(return_value="tok")
        first = sentinel1.filtered_date(self.area, "2026-10-25", items, self.tmp, token, self.read)
        again = sentinel1.filtered_date(self.area, "2026-10-25", items, self.tmp, token, self.read)
        self.assertEqual(len(self.calls), 1)
        token.assert_called_once()
        np.testing.assert_allclose(again, first, atol=0.02)
        self.assertTrue(os.path.exists(sentinel1.cache_path(self.area, "2026-10-25", self.tmp)))
        sentinel1.filtered_date(self.area, "2026-10-25", items, None, token, self.read)   # no cache: read again
        self.assertEqual(len(self.calls), 2)

    def test_pass_view_the_closest_usable_scene_decides_each_pixel(self):
        found = [item("2026-10-20", "https://b/b/vv.tiff"), item("2026-10-25", "https://b/a/vv.tiff")]
        post = mock.Mock(return_value=FakeResponse(json_data={"features": found}))
        get = mock.Mock(return_value=FakeResponse(json_data={"token": "tok"}))
        with mock.patch("lifeline.sources.sentinel1.log"):
            view = sentinel1.pass_view(self.area, "2026-10-23", CFG, self.tmp, None, post, get, self.read)
        self.assertEqual(view["dates"], ["2026-10-25", "2026-10-20"])
        self.assertTrue(view["water"][:, :140].all())     # the 25th (closest) covers the west: water
        self.assertTrue(view["land"][:, 160:].all())      # the 20th fills the east: land
        self.assertTrue(view["seen"].all())
        get.assert_called_once()                          # one token for every tile

    def test_pass_view_is_none_without_a_usable_scene(self):
        post = mock.Mock(return_value=FakeResponse(json_data={"features": [item("2026-10-26")]}))
        series = [["2026-10-23", 797.0], ["2026-10-26", 700.0]]
        self.assertIsNone(sentinel1.pass_view(self.area, "2026-10-23", CFG, self.tmp, series, post, mock.Mock(),
                                              self.read))
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
