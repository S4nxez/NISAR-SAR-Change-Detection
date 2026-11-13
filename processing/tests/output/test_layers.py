import os
import unittest

import numpy as np
from PIL import Image, features

from lifeline.output.layers import (
    load_backscatter,
    save_backscatter,
    CHANGE_GAINED,
    CHANGE_LOST,
    WATER_NARROW,
    WATER_VEGETATED,
    WATER_WIDE,
    change_index,
    load_mask,
    load_sentinel1,
    load_vegetated,
    save_change,
    save_mask,
    save_radar,
    save_sentinel1,
    save_water,
)

from ..helpers import TempDirTest


class TestLayers(TempDirTest):
    def test_mask_round_trip_with_a_size_that_is_not_a_multiple_of_eight(self):
        rng = np.random.default_rng(3)
        water, valid = rng.random((13, 7)) > 0.5, rng.random((13, 7)) > 0.2
        path = os.path.join(self.tmp, "water.npz")
        save_mask(water, valid, path)
        w2, v2 = load_mask(path)
        np.testing.assert_array_equal(w2, water)
        np.testing.assert_array_equal(v2, valid)

    def test_backscatter_round_trip_and_missing_file(self):
        hh = np.array([[-20.0, np.nan], [-5.25, -14.9]], np.float32)
        path = os.path.join(self.tmp, "b.npz")
        save_backscatter(hh, None, path)
        got, hv = load_backscatter(path)
        np.testing.assert_allclose(got, hh, atol=0.02)
        self.assertIsNone(hv)
        save_backscatter(hh, hh - 7, path)
        self.assertEqual(load_backscatter(path)[1].dtype, np.float32)
        self.assertEqual(load_backscatter(os.path.join(self.tmp, "none.npz")), (None, None))

    def test_sentinel1_round_trip_and_missing_file(self):
        rng = np.random.default_rng(5)
        view = {k: rng.random((9, 11)) > 0.5 for k in ("water", "land", "seen")}
        view["dates"] = ["2026-10-25", "2026-10-20"]
        path = os.path.join(self.tmp, "sentinel1.npz")
        save_sentinel1(view, path)
        got = load_sentinel1(path)
        for k in ("water", "land", "seen"):
            np.testing.assert_array_equal(got[k], view[k])
        self.assertEqual(got["dates"], ["2026-10-25", "2026-10-20"])
        self.assertIsNone(load_sentinel1(os.path.join(self.tmp, "none.npz")))

    def test_water_png_marks_wide_water_and_narrow_channels(self):
        water = np.zeros((4, 4), bool)
        water[:, :2] = True
        wide = np.zeros_like(water)
        wide[:, 0] = True
        path = os.path.join(self.tmp, "water.png")
        save_water(water, wide, path)
        with Image.open(path) as img:
            idx = np.array(img)
            self.assertEqual(img.mode, "P")
            self.assertEqual(img.info.get("transparency"), 0)
        self.assertEqual(idx[0].tolist(), [WATER_WIDE, WATER_NARROW, 0, 0])

    def test_water_under_vegetation_has_its_own_colour_and_never_hides_open_water(self):
        water = np.zeros((4, 4), bool)
        water[:, 0] = True
        vegetated = np.zeros_like(water)
        vegetated[:, :3] = True                                   # overlaps the open water on column 0
        path = os.path.join(self.tmp, "water.png")
        save_water(water, water, path, vegetated)
        with Image.open(path) as img:
            idx = np.array(img)
        self.assertEqual(idx[0].tolist(), [WATER_WIDE, WATER_VEGETATED, WATER_VEGETATED, 0])

    def test_the_vegetated_layer_is_stored_only_when_known(self):
        water, valid = np.zeros((5, 9), bool), np.ones((5, 9), bool)
        vegetated = np.zeros_like(water)
        vegetated[2, 3:6] = True
        with_veg, without = os.path.join(self.tmp, "a.npz"), os.path.join(self.tmp, "b.npz")
        save_mask(water, valid, with_veg, vegetated)
        save_mask(water, valid, without)
        np.testing.assert_array_equal(load_vegetated(with_veg), vegetated)
        self.assertIsNone(load_vegetated(without))
        np.testing.assert_array_equal(load_mask(with_veg)[1], valid)

    def test_change_only_where_both_passes_have_data(self):
        prev_w = np.array([[1, 1, 0, 0]], bool)
        cur_w = np.array([[0, 1, 1, 0]], bool)
        valid = np.array([[1, 1, 1, 1]], bool)
        self.assertEqual(change_index((prev_w, valid), (cur_w, valid)).tolist(), [[CHANGE_LOST, 0, CHANGE_GAINED, 0]])
        gap = np.array([[0, 1, 1, 1]], bool)
        self.assertEqual(change_index((prev_w, gap), (cur_w, valid)).tolist(), [[0, 0, CHANGE_GAINED, 0]])

    def test_save_change_writes_the_image_and_counts_pixels(self):
        prev = (np.array([[1, 1, 0]], bool), np.ones((1, 3), bool))
        cur = (np.array([[0, 0, 1]], bool), np.ones((1, 3), bool))
        path = os.path.join(self.tmp, "change.png")
        self.assertEqual(save_change(prev, cur, path), (2, 1))
        self.assertTrue(os.path.exists(path))

    @unittest.skipUnless(features.check("webp"), "Pillow built without WebP")
    def test_radar_preview_is_half_size_with_transparent_gaps(self):
        db = np.full((8, 6), -12.5, np.float32)
        db[:2, :2] = np.nan
        path = os.path.join(self.tmp, "radar.webp")
        save_radar(db, path)
        with Image.open(path) as img:
            self.assertEqual(img.size, (3, 4))
            px = np.array(img.convert("RGBA"))
        self.assertEqual(px[0, 0, 3], 0)
        self.assertAlmostEqual(int(px[3, 2, 0]), 127, delta=4)   # -12.5 dB is mid grey on -25..0 dB
        self.assertEqual(px[3, 2, 3], 255)


if __name__ == "__main__":
    unittest.main()
