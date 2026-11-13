import tempfile
import unittest

import numpy as np

from lifeline.benchmark import optical

from ..helpers import FakeResponse, small_area

SCALE_OFFSET = {"raster:bands": [{"scale": 0.0001, "offset": -0.1}]}


def item(date, tile, offset_applied=False):
    return {"id": f"S2_{tile}_{date}",
            "properties": {"datetime": date + "T14:30:00Z", "earthsearch:boa_offset_applied": offset_applied},
            "assets": {k: {"href": f"{k}:{tile}:{date}", **SCALE_OFFSET} for k in ("scl", "green", "swir16")}}


class TestReference(unittest.TestCase):
    def test_otsu_splits_a_bimodal_sample(self):
        rng = np.random.default_rng(0)
        v = np.concatenate([rng.normal(-0.5, 0.05, 5000), rng.normal(0.4, 0.05, 2000)])
        self.assertTrue(-0.3 < optical.otsu_threshold(v) < 0.2)
        self.assertTrue(np.isnan(optical.otsu_threshold(np.array([np.nan]))))

    def test_reflectance_applies_scale_and_offset_and_keeps_dark_water(self):
        dn = np.array([0, 1000, 1500, 3000], np.float32)
        np.testing.assert_allclose(optical.reflectance(dn, SCALE_OFFSET), [-0.1, 0.0, 0.05, 0.2], atol=1e-6)
        np.testing.assert_allclose(optical.reflectance(dn, {}), dn * 1e-4, atol=1e-6)
        # the catalogue already removed the offset: forest green at DN 400 is 0.04, not -0.06
        np.testing.assert_allclose(optical.reflectance(np.array([400.0]), SCALE_OFFSET, offset_applied=True), [0.04],
                                   atol=1e-6)

    def test_mndwi_is_clipped_and_nan_without_data(self):
        g = np.array([0.05, 0.05, 0.0, 0.2], np.float32)
        s = np.array([-0.01, 0.15, 0.0, 0.2], np.float32)
        m = optical.mndwi_of(g, s, np.array([1, 1, 1, 0], bool))
        self.assertEqual(m[0], 1.0)                       # SWIR below zero over water: clipped
        self.assertAlmostEqual(float(m[1]), -0.5, places=5)
        self.assertTrue(np.isnan(m[2]) and np.isnan(m[3]))

    def test_clear_mask_keeps_a_margin_around_clouds(self):
        scl = np.full((20, 20), 4, np.uint8)
        scl[10, 10] = 9
        scl[0, 0] = 0
        clear = optical.clear_mask(scl)
        self.assertFalse(clear[10, 10 + optical.CLOUD_MARGIN_PX])
        self.assertTrue(clear[10, 10 + optical.CLOUD_MARGIN_PX + 1])
        self.assertFalse(clear[0, 0])

    def test_reference_water_clamps_the_threshold_and_drops_specks(self):
        mndwi = np.full((30, 30), -0.4, np.float32)
        mndwi[:, :10] = 0.5
        mndwi[20, 20] = 0.6              # one-pixel speck
        clear = np.ones_like(mndwi, bool)
        water, valid, t = optical.reference_water(mndwi, clear, clear)
        self.assertTrue(water[:, :10].all())
        self.assertFalse(water[20, 20])
        self.assertTrue(optical.OTSU_RANGE[0] <= t <= optical.OTSU_RANGE[1])
        _, _, t_flat = optical.reference_water(np.full((5, 5), 0.9, np.float32), np.ones((5, 5), bool),
                                                np.ones((5, 5), bool))
        self.assertEqual(t_flat, optical.OTSU_RANGE[1])


class TestScenes(unittest.TestCase):
    def setUp(self):
        self.area = small_area()
        self.shape = (self.area["ny"], self.area["nx"])

    def fake_read(self, bands, log=None):
        """read_band stand-in: bands[(asset, tile)] -> array; the URLs read go to `log`."""
        def read(url, area, resampling, overview_level=None):
            asset, tile, _ = url.split(":")
            if log is not None:
                log.append((asset, tile))
            return bands[(asset, tile)].astype(np.float32)
        return read

    def test_mosaic_takes_the_first_tile_with_data(self):
        west, east = np.zeros(self.shape), np.zeros(self.shape)
        west[:, :150], east[:, 100:] = 1, 1
        bands = {("scl", "A"): west * 6, ("green", "A"): west * 1600, ("swir16", "A"): west * 1050,
                 ("scl", "B"): east * 4, ("green", "B"): east * 1300, ("swir16", "B"): east * 1900}
        mndwi, scl = optical.mosaic_date(self.area, [item("2026-08-30", "A"), item("2026-08-30", "B")],
                                         self.fake_read(bands))
        self.assertEqual((scl[0, 120], scl[0, 200]), (6, 4))       # overlap: first tile wins
        self.assertAlmostEqual(float(mndwi[0, 0]), (0.06 - 0.005) / (0.06 + 0.005), places=4)
        self.assertLess(float(mndwi[0, 200]), 0)

    def test_mosaic_of_offset_free_scenes_keeps_dark_surfaces_positive(self):
        one = np.ones(self.shape)
        bands = {("scl", "A"): one * 4, ("green", "A"): one * 400, ("swir16", "A"): one * 2200}   # forest
        mndwi, _ = optical.mosaic_date(self.area, [item("2026-08-30", "A", offset_applied=True)], self.fake_read(bands))
        self.assertAlmostEqual(float(mndwi[0, 0]), (0.04 - 0.22) / (0.04 + 0.22), places=4)

    def test_reference_for_pass_picks_the_clearest_date_or_none(self):
        clear_scl = np.full(self.shape, 4, np.uint8)
        cloudy_scl = np.full(self.shape, 9, np.uint8)
        green = np.full(self.shape, 1300.0)
        green[:, :50] = 1600
        swir = np.full(self.shape, 1900.0)
        swir[:, :50] = 1050
        bands = {("scl", "A"): clear_scl, ("green", "A"): green, ("swir16", "A"): swir,
                 ("scl", "C"): cloudy_scl, ("green", "C"): green, ("swir16", "C"): swir}
        items = [item("2026-08-29", "C"), item("2026-08-31", "A")]
        post = lambda url, json, timeout: FakeResponse(json_data={"features": items})   # noqa: E731
        mask = np.ones(self.shape, bool)
        reads = []
        with tempfile.TemporaryDirectory() as cache:
            ref = optical.reference_for_pass(self.area, "2026-08-30", mask, cache, 2, 0.3, post,
                                             self.fake_read(bands, reads))
            self.assertEqual((ref["date"], ref["days_apart"], ref["clear_share"]), ("2026-08-31", 1, 1.0))
            self.assertNotIn(("green", "C"), reads)                  # the cloudy date's bands are never read
            self.assertTrue(ref["water"][:, :50].all() and not ref["water"][:, 60:].any())
            only_cloudy = lambda url, json, timeout: FakeResponse(json_data={"features": items[:1]})   # noqa: E731
            self.assertIsNone(optical.reference_for_pass(self.area, "2026-08-30", mask, cache, 2, 0.3,
                                                         only_cloudy, self.fake_read(bands)))

    def test_search_asks_for_the_window_around_the_day(self):
        import datetime as dt
        sent = {}

        def post(url, json, timeout):
            sent.update(json)
            return FakeResponse(json_data={"features": []})
        self.assertEqual(optical.search_scenes(self.area, dt.date(2026, 8, 30), 2, post), [])
        self.assertEqual(sent["datetime"], "2026-08-28T00:00:00Z/2026-09-01T23:59:59Z")
        self.assertEqual(sent["collections"], ["sentinel-2-l2a"])


if __name__ == "__main__":
    unittest.main()
