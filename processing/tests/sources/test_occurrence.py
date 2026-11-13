import os
from unittest import mock

import numpy as np

from lifeline.sources import occurrence

from ..helpers import TempDirTest, small_area


@mock.patch("lifeline.sources.occurrence.log")
class TestOccurrence(TempDirTest):
    def test_tiles_are_named_by_the_north_west_corner(self, _log):
        self.assertEqual(occurrence.occurrence_tiles([-65.245, -3.897, -64.255, -2.903]), ["70W_0N"])
        self.assertEqual(occurrence.occurrence_tiles([5.0, 9.0, 12.0, 11.0]),
                         ["0E_20N", "10E_20N", "0E_10N", "10E_10N"])

    def test_fetch_mosaics_the_tiles_in_order(self, _log):
        area = small_area(bbox=[-0.5, -0.5, 0.5, 0.5])   # four tiles
        calls = []

        def read(url, area):
            calls.append(url)
            out = np.full((area["ny"], area["nx"]), occurrence.NO_DATA, np.uint8)
            out[0, len(calls)] = 10 * len(calls)
            out[0, 0] = 10 * len(calls)   # every tile has the first pixel: the first one wins
            return out
        occ = occurrence.fetch_occurrence(area, read)
        self.assertEqual(len(calls), 4)
        self.assertTrue(all("occurrence_" in u and u.endswith("v1_4_2021.tif") for u in calls))
        self.assertEqual(list(occ[0, :5]), [10, 10, 20, 30, 40])
        self.assertEqual(occ[1, 0], occurrence.NO_DATA)

    def test_saved_layer_is_read_back(self, _log):
        area = small_area(occurrence="test_occ.png")
        occ = np.random.default_rng(1).integers(0, 101, (area["ny"], area["nx"])).astype(np.uint8)
        occ[0, 0] = occurrence.NO_DATA
        path = occurrence.save_occurrence(area, occ, self.tmp)
        self.assertEqual(os.path.basename(path), "test_occ.png")
        np.testing.assert_array_equal(occurrence.load_occurrence(area, self.tmp), occ)

    def test_missing_or_mismatched_layer_is_none(self, log):
        area = small_area()
        self.assertIsNone(occurrence.load_occurrence(area, self.tmp))
        self.assertTrue(occurrence.occurrence_path(area, self.tmp).endswith("test_occurrence.png"))
        occurrence.save_occurrence(area, np.zeros((10, 10), np.uint8), self.tmp)
        self.assertIsNone(occurrence.load_occurrence(area, self.tmp))
        self.assertEqual(log.call_count, 2)
