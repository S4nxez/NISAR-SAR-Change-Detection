import json
import os
import unittest

from lifeline.benchmark import crosscheck

from ..helpers import TempDirTest

C, R, ISO = 1, 2, 3


class TestCrosscheck(TempDirTest):
    def test_which_radar_the_published_status_follows(self):
        self.assertEqual(crosscheck.followed(ISO, C, ISO), "sentinel1")
        self.assertEqual(crosscheck.followed(C, C, ISO), "nisar")
        self.assertEqual(crosscheck.followed(R, C, ISO), "neither")   # held at risk: unverified water
        self.assertEqual(crosscheck.followed(C, C, C), "both")

    def test_verdicts_are_counted_per_zone_type(self):
        cases = [{"cause": "smooth_ground", "reviewed": {"verdict": "sentinel1"}},
                 {"cause": "smooth_ground", "reviewed": {"verdict": "nisar"}},
                 {"cause": "smooth_ground"},
                 {"cause": "vegetation", "reviewed": {"verdict": "undecidable"}}]
        self.assertEqual(crosscheck.tally(cases), {
            "smooth_ground": {"cases": 3, "nisar": 1, "sentinel1": 1, "undecidable": 0, "pending": 1},
            "vegetation": {"cases": 1, "nisar": 0, "sentinel1": 0, "undecidable": 1, "pending": 0}})

    def test_summary_pools_the_agreement_by_judged_area(self):
        rows = [{"judged_km2": 100.0, "agreement": 0.9, "nisar_only_km2": 1.0, "sentinel1_only_km2": 2.0,
                 "mud_km2": 0.5},
                {"judged_km2": 300.0, "agreement": 0.98, "nisar_only_km2": 0.5, "sentinel1_only_km2": 0.25}]
        cases = [{"cause": "narrow_channel", "followed": "nisar"}]
        sm = crosscheck.summary(rows, cases, [{"review": True}])
        self.assertEqual((sm["passes"], sm["judged_km2"], sm["agreement"]), (2, 400.0, 0.96))
        self.assertEqual((sm["nisar_only_km2"], sm["sentinel1_only_km2"], sm["mud_km2"]), (1.5, 2.2, 0.5))
        self.assertEqual((sm["status_cases"], sm["sites"], sm["followed"]), (1, 1, {"nisar": 1}))
        self.assertIsNone(crosscheck.summary([], [], [])["agreement"])

    def test_reviews_take_the_crosscheck_verdicts_only(self):
        path = os.path.join(self.tmp, "crosscheck_reviews.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"reviews": [{"pass": "p", "community_id": "a", "verdict": "sentinel1"}]}, f)
        self.assertEqual(crosscheck.load_reviews(path)[0]["verdict"], "sentinel1")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"reviews": [{"pass": "p", "community_id": "a", "verdict": "reference"}]}, f)
        with self.assertRaises(ValueError):
            crosscheck.load_reviews(path)
        self.assertEqual(crosscheck.load_reviews(os.path.join(self.tmp, "none.json")), [])

    def test_review_template_names_the_place_and_the_verdicts(self):
        site = {"passes": ["p"], "community_ids": ["a"], "cause": "smooth_ground"}
        got = json.loads(crosscheck.review_template(site))
        self.assertEqual((got["passes"], got["verdict"]), (["p"], "nisar | sentinel1 | undecidable"))


if __name__ == "__main__":
    unittest.main()
