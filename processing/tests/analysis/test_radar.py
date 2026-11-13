import io
import tempfile
import unittest
from unittest import mock

import numpy as np

from lifeline.analysis.radar import (
    trim_swath_edge,
    area_edge,
    block_mean,
    box_sum,
    filter_db,
    granule_window,
    linear_to_db,
    load_window,
    mask_fill,
    product_window,
    read_pass,
    read_pass_bands,
    read_window,
    refined_lee,
    resample_into,
    speckle_filter,
    speckle_window,
    window_cache_path,
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

    def test_fill_below_the_floor_becomes_no_data(self):
        db = np.array([-12.0, -39.9, -40.0, -57.0, -150.0, np.nan], np.float32)
        out = mask_fill(db, -40.0)
        np.testing.assert_array_equal(np.isnan(out), [False, False, False, True, True, True])
        self.assertIs(out, db)

    def test_the_band_along_the_swath_edge_becomes_no_data(self):
        db = np.full((6, 10), -8.0, np.float32)
        db[:, 8:] = np.nan                                   # the swath ends at column 8
        in_area = np.ones_like(db, bool)
        in_area[0, :3] = False                               # a corner of the circle: not an edge
        db[0, :3] = np.nan
        out = trim_swath_edge(db, in_area, 40.0, 20.0)
        self.assertIs(out, db)
        self.assertTrue(np.isnan(out[:, 6:]).all())          # 2 px = 40 m from the edge
        self.assertFalse(np.isnan(out[1:, :6]).any())
        same = np.full((3, 3), -8.0, np.float32)
        trim_swath_edge(same, np.ones((3, 3), bool), 0, 20.0)
        trim_swath_edge(same, np.ones((3, 3), bool), 100.0, 20.0)   # no gap: nothing to trim
        self.assertFalse(np.isnan(same).any())

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


def gamma_db(mean_db, shape, looks, seed=0):
    rng = np.random.default_rng(seed)
    return (10 * np.log10(rng.gamma(looks, 1 / looks, shape) * 10 ** (mean_db / 10))).astype(np.float32)


class TestRefinedLee(unittest.TestCase):
    def test_homogeneous_areas_are_smoothed_without_bias(self):
        db = gamma_db(-10.0, (120, 120), 9)
        out = refined_lee(db, 9.0)
        lin_in, lin_out = 10 ** (db / 10), 10 ** (out / 10)
        enl_in = (lin_in.mean() / lin_in.std()) ** 2
        enl_out = (lin_out[10:-10, 10:-10].mean() / lin_out[10:-10, 10:-10].std()) ** 2
        self.assertGreater(enl_out, 4 * enl_in)
        self.assertAlmostEqual(float(lin_out.mean() / lin_in.mean()), 1.0, delta=0.03)

    def test_a_noiseless_shore_is_kept_and_a_narrow_line_is_less_blurred_than_by_the_box(self):
        db = np.full((40, 40), -7.0, np.float32)
        db[:, :20] = -23.0                                         # lake | forest
        out = refined_lee(db, 9.0)
        np.testing.assert_allclose(out, db, atol=1e-3)              # an edge is not blurred at all
        line = np.full((40, 40), -7.0, np.float32)
        line[:, 19:21] = -23.0                                     # 40 m channel: thinner than the half windows
        lee, box = refined_lee(line, 9.0)[5:-5, 19:21], speckle_filter(line, 3)[5:-5, 19:21]
        self.assertTrue((lee < box - 3).all())                     # darker than the box keeps it, not exact

    def test_a_60m_channel_keeps_its_width_where_the_box_filter_shrinks_it(self):
        mean = np.full((200, 200), -7.0, np.float32)
        mean[:, 99:102] = -23.0                                    # 3 px = 60 m
        noisy = mean + gamma_db(0.0, mean.shape, 9, seed=3)
        lee = refined_lee(noisy, 9.0)[5:-5, 99:102] < -15
        box = speckle_filter(noisy, 3)[5:-5, 99:102] < -15
        self.assertGreater(lee.mean(), 0.95)
        self.assertLess(box.mean(), 0.5)

    def test_a_shore_next_to_a_gap_is_kept(self):
        db = np.full((40, 40), -7.0, np.float32)
        db[:, :20] = -23.0
        db[:6, :] = np.nan                                         # swath edge just north of the shore's end
        db[:, 36:] = np.nan
        out = refined_lee(db, 9.0)
        ok = np.isfinite(db)
        np.testing.assert_allclose(out[ok], db[ok], atol=1e-3)

    def test_no_data_stays_no_data_and_does_not_spread(self):
        db = gamma_db(-10.0, (60, 60), 9)
        db[20:30, 20:30] = np.nan
        out = refined_lee(db, 9.0)
        np.testing.assert_array_equal(np.isnan(out), np.isnan(db))

    def test_chunks_give_the_same_result(self):
        db = gamma_db(-12.0, (90, 50), 9, seed=5)
        db[:, 20:23] = -23.0
        whole = refined_lee(db, 9.0)
        with mock.patch("lifeline.analysis.radar.LEE_CHUNK_ROWS", 7):
            np.testing.assert_allclose(refined_lee(db, 9.0), whole, atol=1e-5)

    def test_filter_choice_comes_from_the_area(self):
        db = gamma_db(-10.0, (30, 30), 9)
        np.testing.assert_array_equal(filter_db({"speckle_m": 60}, db, 20.0), speckle_filter(db, 3))
        np.testing.assert_array_equal(filter_db({"speckle_filter": "refined_lee", "speckle_looks": 9}, db, 20.0),
                                      refined_lee(db, 9.0))
        with self.assertRaises(ValueError):
            filter_db({"speckle_filter": "median"}, db, 20.0)


@unittest.skipIf(h5py is None, "h5py and pyproj are needed to read GCOV products")
class TestReadPass(unittest.TestCase):
    """read_pass against a synthetic GCOV product in memory (UTM 20S, like Tefé)."""

    def gcov(self, area, with_hh=True, with_hv=False, fill_rows=0):
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
                hh[:fill_rows] = 1e-10                                        # swath-edge fill, -100 dB
                fa["HHHH"] = hh
            if with_hv:
                fa["HVHV"] = np.full((len(ys), len(xs)), 10 ** (-1.2), np.float32)   # -12 dB
        return buf.getvalue()

    def opener(self, products, opened=None):
        class Remote(io.BytesIO):
            """In-memory stand-in for RemoteFile: a file object that counts the megabytes read."""

            def __init__(self, url, token):
                super().__init__(products[url])
                self.bytes = 1_000_000
                if opened is not None:
                    opened.append(url)
        return Remote

    def test_the_cache_is_read_instead_of_the_product_and_gives_the_same_pass(self):
        area = small_area(speckle_m=60)
        ps = {"granules": [{"url": "https://asf.example/NISAR_G1.h5", "name": "NISAR_G1.h5"}]}
        products = {ps["granules"][0]["url"]: self.gcov(area, with_hv=True)}
        direct = read_pass(area, ps, "token", open_remote=self.opener(products))
        opened = []
        with tempfile.TemporaryDirectory() as cache:
            first = read_pass(area, ps, "token", open_remote=self.opener(products, opened), cache_dir=cache)
            second = read_pass(area, ps, "token", open_remote=self.opener(products, opened), cache_dir=cache)
            window = load_window(window_cache_path(area, ps["granules"][0], cache))
        self.assertEqual(len(opened), 1)                       # the second read used the cache only
        np.testing.assert_array_equal(first[0], direct[0])
        np.testing.assert_array_equal(second[0], direct[0])
        self.assertEqual((first[1], second[1], second[2]), (1.0, 0.0, 20.0))
        self.assertEqual(sorted(window["bands"]), ["HHHH", "HVHV"])   # HV is kept for the methods that need it

    def test_a_granule_without_hh_is_cached_as_empty(self):
        area = small_area()
        g = {"url": "u", "name": "NISAR_G2.h5"}
        opened = []
        with tempfile.TemporaryDirectory() as cache:
            for _ in range(2):
                self.assertIsNone(granule_window(area, g, "t", open_remote=self.opener(
                    {"u": self.gcov(area, with_hh=False)}, opened), cache_dir=cache))
        self.assertEqual(opened, ["u"])

    def test_without_a_cache_only_the_asked_bands_are_read(self):
        area = small_area()
        w = read_window(area, {"url": "u"}, "t", ("HHHH",), self.opener({"u": self.gcov(area, with_hv=True)}))
        self.assertEqual(list(w["bands"]), ["HHHH"])

    def test_cache_files_depend_on_the_area_and_the_granule(self):
        a, b = small_area(), small_area(bbox=[-64.81, -3.44, -64.74, -3.40])
        g = {"url": "https://x/NISAR_G3.h5", "name": "NISAR_G3.h5"}
        self.assertNotEqual(window_cache_path(a, g, "/c"), window_cache_path(b, g, "/c"))
        self.assertTrue(window_cache_path(a, g, "/c").endswith("NISAR_G3.npz"))

    def test_reads_the_area_and_resamples_it_to_the_grid(self):
        area = small_area(speckle_m=60)
        ps = {"granules": [{"url": "a"}]}
        db, read_mb, spacing = read_pass(area, ps, "token", open_remote=self.opener({"a": self.gcov(area)}))
        self.assertEqual(db.shape, (area["ny"], area["nx"]))
        self.assertTrue(np.isfinite(db).all())
        self.assertAlmostEqual(float(np.nanmedian(db[:, :100])), -20.0, places=3)
        self.assertAlmostEqual(float(np.nanmedian(db[:, -100:])), -5.0, places=3)
        self.assertEqual((read_mb, spacing), (1.0, 20.0))

    def test_swath_edge_fill_is_no_data_and_does_not_leak_into_the_filter(self):
        area = small_area(speckle_m=60)
        ps = {"granules": [{"url": "a"}]}
        db, _, _ = read_pass(area, ps, "token", open_remote=self.opener({"a": self.gcov(area, fill_rows=60)}))
        self.assertTrue(np.isnan(db[:5]).all())                 # the north rows fall in the fill
        valid = db[np.isfinite(db)]
        self.assertGreater(valid.min(), -21.0)                  # nothing darker than the real water came through
        self.assertTrue(np.isfinite(db[-50:]).all())

    def test_hv_is_read_with_hh_and_is_none_on_single_polarisation_passes(self):
        area = small_area(speckle_m=60)
        ps = {"granules": [{"url": "a"}]}
        dual, _, _ = read_pass_bands(area, ps, "t", ("HHHH", "HVHV"), self.opener({"a": self.gcov(area, with_hv=True)}))
        single, _, _ = read_pass_bands(area, ps, "t", ("HHHH", "HVHV"), self.opener({"a": self.gcov(area)}))
        self.assertAlmostEqual(float(np.nanmedian(dual["HVHV"])), -12.0, places=3)
        self.assertIsNone(single["HVHV"])
        np.testing.assert_array_equal(dual["HHHH"], single["HHHH"])

    def test_frames_without_hh_are_skipped(self):
        area = small_area()
        ps = {"granules": [{"url": "a"}]}
        db, read_mb, spacing = read_pass(area, ps, "token",
                                         open_remote=self.opener({"a": self.gcov(area, with_hh=False)}))
        self.assertTrue(np.isnan(db).all())
        self.assertEqual((read_mb, spacing), (0.0, None))


if __name__ == "__main__":
    unittest.main()
