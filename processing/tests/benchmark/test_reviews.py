import os

from lifeline.benchmark import reviews

from ..helpers import TempDirTest


def case(cid, kind="false_route", cause="unexplained"):
    return {"community_id": cid, "kind": kind, "cause": cause, "family": "unexplained", "review": True}


class TestReviews(TempDirTest):
    def test_missing_file_has_no_reviews_and_an_unknown_verdict_is_refused(self):
        self.assertEqual(reviews.load(os.path.join(self.tmp, "none.json")), [])
        path = self.write_json("r.json", {"reviews": [{"pass": "p", "community_id": "a", "verdict": "maybe"}]})
        with self.assertRaises(ValueError):
            reviews.load(path)

    def test_reviews_attach_to_their_case_and_may_correct_the_cause(self):
        path = self.write_json("r.json", {"reviews": [
            {"pass": "p1", "community_id": "a", "verdict": "nisar", "cause": "cloud_edge", "reviewer": "JN",
             "date": "2026-11-12", "note": "cloud shadow over the channel"},
            {"pass": "p2", "community_id": "b", "verdict": "reference"}]})
        found = reviews.attach("p1", [case("a"), case("b")], reviews.load(path))
        self.assertEqual(found[0]["reviewed"]["verdict"], "nisar")
        self.assertEqual((found[0]["cause"], found[0]["cause_found"], found[0]["family"]),
                         ("cloud_edge", "unexplained", "reference"))
        self.assertFalse(found[0]["review"])
        self.assertNotIn("reviewed", found[1])   # the review of b is for another pass

    def test_one_review_covers_every_pass_and_community_of_a_site(self):
        path = self.write_json("r.json", {"reviews": [
            {"passes": ["p1", "p2"], "community_ids": ["a", "b"], "verdict": "reference"}]})
        rs = reviews.load(path)
        self.assertEqual(reviews.pairs(rs[0]), [("p1", "a"), ("p1", "b"), ("p2", "a"), ("p2", "b")])
        found = reviews.attach("p2", [case("a"), case("b"), case("c")], rs)
        self.assertEqual([("reviewed" in c) for c in found], [True, True, False])
        bad = self.write_json("bad.json", {"reviews": [{"passes": ["p1"], "verdict": "nisar"}]})
        with self.assertRaises(ValueError):
            reviews.load(bad)

    def test_summary_counts_verdicts_per_kind(self):
        cs = [case("a"), case("b"), case("c"), case("d", kind="false_isolated")]
        cs[0]["reviewed"] = {"verdict": "reference"}
        cs[1]["reviewed"] = {"verdict": "nisar"}
        s = reviews.summary(cs)
        self.assertEqual(s["false_route"], {"cases": 3, "confirmed": 1, "rejected": 1, "undecidable": 0,
                                            "pending": 1})
        self.assertEqual(s["false_isolated"]["pending"], 1)
