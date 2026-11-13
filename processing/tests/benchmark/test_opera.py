import datetime as dt
import os
from unittest import mock

import numpy as np

from lifeline.benchmark import opera

from ..helpers import TempDirTest, small_area


def umm(name, start, files):
    return {"umm": {"GranuleUR": name, "TemporalExtent": {"RangeDateTime": {"BeginningDateTime": start}},
                    "RelatedUrls": [{"Type": "GET DATA", "URL": f"https://data.example/{f}"} for f in files]
                    + [{"Type": "GET DATA", "URL": f"s3://bucket/{files[0]}"}]}}


class Response:
    def __init__(self, status=200, body=None, content=b""):
        self.status_code, self.body, self.content = status, body, content

    def json(self):
        return self.body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


class TestCatalogue(TempDirTest):
    def test_only_granules_with_an_https_water_layer_are_kept(self):
        items = [umm("A", "2026-08-24T10:00:00Z", ["A_B01_WTR.tif", "A_B02_BWTR.tif"]),
                 umm("B", "2026-08-25T10:00:00Z", ["B_B02_BWTR.tif"]),
                 {"umm": {"GranuleUR": "C"}}]
        got = opera.granules_from_umm(items)
        self.assertEqual(got, [{"date": "2026-08-24", "name": "A", "url": "https://data.example/A_B01_WTR.tif"}])

    def test_search_asks_cmr_for_the_area_and_window(self):
        get = mock.Mock(return_value=Response(body={"items": []}))
        opera.search_granules("OPERA_L3_DSWX-S1_V1", small_area(), dt.date(2026, 8, 24), 3, get)
        params = get.call_args.kwargs["params"]
        self.assertEqual(params["temporal"], "2026-08-21T00:00:00Z,2026-08-27T23:59:59Z")
        self.assertEqual(params["bounding_box"], "-64.8,-3.44,-64.74,-3.4")


class TestClasses(TempDirTest):
    def test_class_masks(self):
        m = opera.class_masks(np.array([[0, 1, 2, 3, 250, 255]], np.uint8))
        np.testing.assert_array_equal(m["water"], [[0, 1, 0, 0, 0, 0]])
        np.testing.assert_array_equal(m["land"], [[1, 0, 0, 1, 0, 0]])   # inundated vegetation is no boat route
        np.testing.assert_array_equal(m["partial"], [[0, 0, 1, 0, 0, 0]])
        np.testing.assert_array_equal(m["valid"], [[1, 1, 1, 1, 0, 0]])

    def test_mosaic_first_class_wins(self):
        a = np.array([[255, 1, 255]], np.uint8)
        b = np.array([[0, 0, 255]], np.uint8)
        np.testing.assert_array_equal(opera.mosaic([a, b]), [[0, 1, 255]])


class TestDownload(TempDirTest):
    def test_download_once_with_the_token(self):
        get = mock.Mock(return_value=Response(content=b"tif"))
        path = os.path.join(self.tmp, "x", "a.tif")
        opera.download("https://u/a.tif", path, "tok", get)
        opera.download("https://u/a.tif", path, "tok", get)
        get.assert_called_once()
        self.assertEqual(get.call_args.kwargs["headers"], {"Authorization": "Bearer tok"})
        with open(path, "rb") as f:
            self.assertEqual(f.read(), b"tif")

    def test_refused_or_missing_token(self):
        with self.assertRaises(PermissionError):
            opera.download("https://u/b.tif", os.path.join(self.tmp, "b.tif"), "tok",
                           mock.Mock(return_value=Response(401)))
        with self.assertRaises(PermissionError):
            opera.download("https://u/c.tif", os.path.join(self.tmp, "c.tif"), None, mock.Mock())


class TestReference(TempDirTest):
    def test_the_date_with_the_largest_coverage_is_chosen_and_cached(self):
        area = small_area()
        in_area = np.ones((area["ny"], area["nx"]), bool)
        items = [umm("D1", "2026-08-23T10:00:00Z", ["D1_B01_WTR.tif"]),
                 umm("D2", "2026-08-25T10:00:00Z", ["D2_B01_WTR.tif"])]

        def get(url, **kw):
            if url == opera.CMR_GRANULES:
                return Response(body={"items": items})
            return Response(content=b"x")

        def read(path, area):
            out = np.full((area["ny"], area["nx"]), opera.NO_DATA, np.uint8)
            cols = 50 if "D1" in path else 200          # D2 covers more of the area
            out[:, :cols] = opera.OPEN_WATER
            return out
        ref = opera.reference_for_pass("dswx_s1", area, "2026-08-24", in_area, self.tmp, 3, "tok", get, read)
        self.assertEqual((ref["date"], ref["days_apart"], ref["coverage"]), ("2026-08-25", 1, round(200 / 300, 4)))
        self.assertTrue(ref["water"][:, :200].all())
        again = opera.reference_for_pass("dswx_s1", area, "2026-08-24", in_area, self.tmp, 3, None, get,
                                         mock.Mock(side_effect=AssertionError("cached")))
        self.assertEqual(again["date"], "2026-08-25")

    def test_no_granule_gives_none(self):
        area = small_area()
        get = mock.Mock(return_value=Response(body={"items": []}))
        self.assertIsNone(opera.reference_for_pass("dswx_hls", area, "2026-08-24",
                                                   np.ones((area["ny"], area["nx"]), bool), self.tmp, 2, "t", get))
