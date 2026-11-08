import unittest

from lifeline.asf import best_granules, group_passes, mode_rank, parse_name, search

from .helpers import FakeResponse, small_area

NAME = "NISAR_L2_PR_GCOV_033_{track}_{dir}_{frame}_{mode}_{pol}_A_{start}_20261023T100332_P05023_N_F_J_001.h5"
PROVISIONAL = "NISAR_L2_GCOV_PROVISIONAL_V1"
BETA = "NISAR_L2_GCOV_BETA_V1"


def feature(track=161, direction="A", frame=176, mode="2005", pol="DHDH", start="20261023T100258",
            collection=PROVISIONAL, ext=".h5"):
    name = NAME.format(track=track, dir=direction, frame=frame, mode=mode, pol=pol, start=start).replace(".h5", ext)
    return {"properties": {"fileName": name, "url": f"https://data.example/{name}", "collectionName": collection}}


class TestNames(unittest.TestCase):
    def test_parse_name(self):
        g = parse_name("NISAR_L2_PR_GCOV_033_161_A_176_2005_DHDH_A_20261023T100258_20261023T100332_P05023_N_F_J_001.h5")
        self.assertEqual((g["cycle"], g["track"], g["direction"], g["frame"], g["mode"], g["pol"]),
                         (33, 161, "A", 176, "2005", "DHDH"))
        self.assertEqual(g["start"].strftime("%Y-%m-%d %H:%M"), "2026-10-23 10:02")

    def test_mode_rank_prefers_provisional_20_mhz_and_hh(self):
        g = lambda mode, pol="DHDH", coll=PROVISIONAL: {"mode": mode, "pol": pol, "collection": coll}  # noqa: E731
        self.assertIsNone(mode_rank(g("0005")))
        self.assertLess(mode_rank(g("2005")), mode_rank(g("4005")))
        self.assertLess(mode_rank(g("4005")), mode_rank(g("2005", coll=BETA)))
        self.assertLess(mode_rank(g("2005", "SHSH")), mode_rank(g("2005", "QPQP")))


class TestPasses(unittest.TestCase):
    def test_best_granule_per_day_track_and_frame(self):
        feats = [feature(mode="4005"), feature(mode="2005"), feature(mode="0005", frame=177),
                 feature(ext=".xml"), feature(frame=177, collection=BETA)]
        best = best_granules(feats)
        self.assertEqual(sorted((g["frame"], g["mode"]) for g in best), [(176, "2005"), (177, "2005")])

    def test_frames_of_one_track_and_day_make_one_pass(self):
        passes = group_passes(best_granules([
            feature(frame=177, start="20261023T100330"), feature(frame=176, start="20261023T100258"),
            feature(track=169, direction="D", frame=10, start="20261023T220000", collection=BETA)]))
        self.assertEqual(sorted(passes), ["2026-10-23_t161A", "2026-10-23_t169D"])
        asc = passes["2026-10-23_t161A"]
        self.assertEqual((asc["direction"], asc["frames"], asc["time_utc"], asc["beta"]),
                         ("ascending", [176, 177], "10:02", False))
        self.assertEqual(asc["modes"], ["2005_DHDH"])
        desc = passes["2026-10-23_t169D"]
        self.assertEqual((desc["direction"], desc["beta"]), ("descending", True))

    def test_search_asks_asf_for_the_area_and_groups_the_answer(self):
        seen = {}

        def get(url, params, timeout, headers):
            seen.update(url=url, params=params)
            return FakeResponse(json_data={"features": [feature()]})

        passes = search(small_area(), get=get)
        self.assertIn("asf.alaska.edu", seen["url"])
        self.assertEqual(seen["params"]["processingLevel"], "GCOV")
        self.assertTrue(seen["params"]["intersectsWith"].startswith("POLYGON(("))
        self.assertEqual(list(passes), ["2026-10-23_t161A"])

    def test_search_fails_on_http_errors(self):
        import requests
        with self.assertRaises(requests.HTTPError):
            search(small_area(), get=lambda *a, **k: FakeResponse(503))


if __name__ == "__main__":
    unittest.main()
