import os
from unittest import mock

import numpy as np

from lifeline.benchmark import static_layers

from ..helpers import TempDirTest, small_area


class TestTiles(TempDirTest):
    def test_worldcover_tiles_are_named_by_the_south_west_corner(self):
        self.assertEqual(static_layers.worldcover_tiles([-65.245, -3.897, -64.255, -2.903]), ["S06W066", "S03W066"])
        self.assertEqual(static_layers.worldcover_tiles([1.5, 0.5, 2.0, 1.0]), ["N00E000"])

    def test_occurrence_tiles_are_named_by_the_north_west_corner(self):
        self.assertEqual(static_layers.occurrence_tiles([-65.245, -3.897, -64.255, -2.903]), ["70W_0N"])
        self.assertEqual(static_layers.occurrence_tiles([5.0, 9.0, 12.0, 11.0]),
                         ["0E_20N", "10E_20N", "0E_10N", "10E_10N"])

    def test_layers_are_read_once_and_mosaicked(self):
        area = small_area()
        calls = []

        def read(url, area):
            calls.append(url)
            out = np.full((area["ny"], area["nx"]), static_layers.NO_DATA, np.uint8)
            out[:, :10] = 90 if "WorldCover" in url else 40
            return out
        layers = static_layers.load(area, self.tmp, read)
        self.assertEqual((layers["worldcover"][0, 0], layers["occurrence"][0, 0]), (90, 40))
        self.assertEqual(layers["worldcover"][0, 50], static_layers.NO_DATA)
        n = len(calls)
        static_layers.load(area, self.tmp, mock.Mock(side_effect=AssertionError("cached")))
        self.assertEqual(n, len(calls))
        self.assertTrue(os.path.exists(os.path.join(self.tmp, "static", "test_layers.npz")))

    def test_optical_is_blind_under_wetlands_and_mangroves(self):
        wc = np.array([[10, 80, 90, 95]], np.uint8)
        np.testing.assert_array_equal(static_layers.optical_blind(wc), [[False, False, True, True]])
