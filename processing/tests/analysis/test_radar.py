import io
import unittest

import numpy as np

from lifeline.analysis.radar import (
    area_edge,
    block_mean,
    box_sum,
    linear_to_db,
    product_window,
    read_pass,
    resample_into,
    speckle_filter,
    speckle_window,
)

from ..helpers import small_area

try:
    import h5py
    import pyproj  # noqa: F401
except ImportError:   # optional locally; the CI installs it from processing/pyproject.toml
    h5py = None


class TestBackscatterHelpers(unittest.TestCase):
    def test_linear_to_db_and_invalid_values(self):
        db = linear_to_db([1.0, 0.1, 0.0, -1.0, np.inf])
        np.testing.assert_allclose(db[:2], [0.0, -10.0], atol=1e-6)
        self.assertTrue(np.isnan(db[2:]).all())

    def test_box_sum_matches_a_brute_force_sum_clipped_at_the_edges(self):
        rng = np.random.default_rng(1)
        a = rng.random((7, 9))
        k, r = 3, 1
        expected = np.array([[a[max(0, i - r):i + r + 1, max(0, j - r):j + r + 1].sum() for j in range(9)]
                             for i in range(7)])
        np.testing.assert_allclose(box_sum(a, k), expected)

    def test_speckle_filter_averages_in_linear_power_and_ignores_nan(self):
        db = np.full((5, 5), -10.0, np.float32)
        db[2, 2] = 0.0
        db[0, 0] = np.nan
        out = speckle_filter(db, 3)
        expected = 10 * np.log10((8 * 0.1 + 1.0) / 9)
        self.assertAlmostEqual(float(out[2, 2]), expected, places=4)
        self.assertTrue(np.isnan(out[0, 0]))
        self.assertAlmostEqual(float(out[4, 4]), -10.0, places=4)

    def test_block_mean_ignores_nan_and_drops_incomplete_blocks(self):
        a = np.array([[1, 3, 5], [np.nan, 2, 7], [9, 9, 9]], np.float32)
        out = block_mean(a, 2)
        self.assertEqual(out.shape, (1, 1))
        self.assertAlmostEqual(float(out[0, 0]), 2.0)
        self.assertTrue(np.isnan(block_mean(np.full((2, 2), np.nan), 2)[0, 0]))

    def test_speckle_window_is_odd_and_at_least_three(self):
        self.assertEqual(speckle_window({"speckle_m": 60}, 20.0), 3)
        self.assertEqual(speckle_window({"speckle_m": 100}, 20.0), 5)
        self.assertEqual(speckle_window({"speckle_m": 120}, 20.0), 7)
        self.assertEqual(speckle_window({}, 10.0), 11)   # default 100 m
        self.assertEqual(speckle_window({"speckle_m": 10}, 20.0), 3)


class TestProductWindow(unittest.TestCase):
    def test_window_holds_the_edge_plus_padding_and_is_clipped(self):
        xs = np.arange(0, 1000, 10.0)          # 100 columns, x grows
        ys = np.arange(1000, 0, -10.0)         # 100 rows, y falls (north up)
        r0, r1, c0, c1 = product_window(xs, ys, ex=[200, 300], ey=[500, 600], pad=20)
        self.assertEqual((c0, c1), (18, 33))
        self.assertEqual((r0, r1), (38, 53))
        self.assertEqual(product_window(xs, ys, ex=[-500, 5000], ey=[-500, 5000], pad=0), (0, 100, 0, 100))

    def test_area_edge_runs_around_the_bbox(self):
        lon, lat = area_edge(small_area(), n=4)
        self.assertEqual(len(lon), 16)
        self.assertEqual((lon.min(), lon.max(), lat.min(), lat.max()), (-64.80, -64.74, -3.44, -3.40))


class IdentityTransformer:
    """lon/lat -> 'projected' x/y in metres around the area, enough for the resampling."""

    def transform(self, lon, lat):
        return np.asarray(lon) * 100000.0, np.asarray(lat) * 100000.0


class TestResample(unittest.TestCase):
    def test_nearest_pixel_fills_only_missing_pixels(self):
        area = small_area(nx=6, ny=4, step_deg=0.01, bbox=[0.0, 0.0, 0.06, 0.04])
        db = np.arange(24, dtype=np.float32).reshape(4, 6)   # product pixels on the same grid
        out = np.full((4, 6), np.nan, np.float32)
        out[0, 0] = -99.0
        # first product pixel centre at the first grid pixel centre; y falls by 1000 m per row
        resample_into(out, db, area, IdentityTransformer(), x0=500.0, y0=3500.0, dx=1000.0, dy=-1000.0)
        self.assertEqual(out[0, 0], -99.0)       # already filled by an earlier frame
        np.testing.assert_array_equal(out[1:], db[1:])

    def test_pixels_outside_the_product_stay_nan(self):
        area = small_area(nx=6, ny=4, step_deg=0.01, bbox=[0.0, 0.0, 0.06, 0.04])
        db = np.zeros((2, 2), np.float32)
        out = np.full((4, 6), np.nan, np.float32)
        resample_into(out, db, area, IdentityTransformer(), x0=500.0, y0=3500.0, dx=1000.0, dy=-1000.0)
        self.assertEqual(int(np.isfinite(out).sum()), 4)


@unittest.skipIf(h5py is None, "h5py and pyproj are needed to read GCOV products")
class TestReadPass(unittest.TestCase):
    """read_pass against a synthetic GCOV product in memory (UTM 20S, like Tefé)."""

    def gcov(self, area, with_hh=True):
        from pyproj import Transformer
        tr = Transformer.from_crs(4326, 32720, always_xy=True)
        x0, y1 = tr.transform(area["bbox"][0], area["bbox"][3])
        x1, y0 = tr.transform(area["bbox"][2], area["bbox"][1])
        xs = np.arange(x0 - 500, x1 + 500, 20.0)
        ys = np.arange(y1 + 500, y0 - 500, -20.0)
        buf = io.BytesIO()
        with h5py.File(buf, "w") as f:
            fa = f.create_group("science/LSAR/GCOV/grids/frequencyA")
            fa["projection"] = np.int32(32720)
            fa["xCoordinates"], fa["yCoordinates"] = xs, ys
            if with_hh:
                hh = np.full((len(ys), len(xs)), 10 ** (-0.5), np.float32)   # land, -5 dB
                hh[:, : len(xs) // 2] = 10 ** (-2.0)                          # water on the west half, -20 dB
                fa["HHHH"] = hh
        return buf.getvalue()

    def opener(self, products):
        class Remote(io.BytesIO):
            """In-memory stand-in for RemoteFile: a file object that counts the megabytes read."""

            def __init__(self, url, token):
                super().__init__(products[url])
                self.bytes = 1_000_000
        return Remote

    def test_reads_the_area_and_resamples_it_to_the_grid(self):
        area = small_area(speckle_m=60)
        ps = {"granules": [{"url": "a"}]}
        db, read_mb, spacing = read_pass(area, ps, "token", open_remote=self.opener({"a": self.gcov(area)}))
        self.assertEqual(db.shape, (area["ny"], area["nx"]))
        self.assertTrue(np.isfinite(db).all())
        self.assertAlmostEqual(float(np.nanmedian(db[:, :100])), -20.0, places=3)
        self.assertAlmostEqual(float(np.nanmedian(db[:, -100:])), -5.0, places=3)
        self.assertEqual((read_mb, spacing), (1.0, 20.0))

    def test_frames_without_hh_are_skipped(self):
        area = small_area()
        ps = {"granules": [{"url": "a"}]}
        db, read_mb, spacing = read_pass(area, ps, "token",
                                         open_remote=self.opener({"a": self.gcov(area, with_hh=False)}))
        self.assertTrue(np.isnan(db).all())
        self.assertEqual((read_mb, spacing), (0.0, None))


if __name__ == "__main__":
    unittest.main()
