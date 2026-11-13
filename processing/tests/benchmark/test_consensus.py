import unittest

import numpy as np

from lifeline.benchmark import consensus


def row(*vals):
    return np.array([vals], bool)


class TestVotes(unittest.TestCase):
    def test_blind_land_votes_are_dropped_and_water_wins_over_land_in_one_source(self):
        v = consensus.votes("s2", "optical", row(1, 0, 0, 1), row(1, 1, 1, 0), blind_land=row(0, 1, 0, 0))
        np.testing.assert_array_equal(v["water"], row(1, 0, 0, 1))
        np.testing.assert_array_equal(v["land"], row(0, 0, 1, 0))


class TestCombine(unittest.TestCase):
    def setUp(self):
        self.s2 = consensus.votes("s2", "optical", row(1, 1, 0, 0, 0), row(0, 0, 1, 1, 0))
        self.s1 = consensus.votes("s1", "sar", row(1, 0, 0, 1, 0), row(0, 0, 1, 0, 0))
        self.area = row(1, 1, 1, 1, 1)

    def test_agreement_disagreement_and_single_source(self):
        c = consensus.combine([self.s2, self.s1], self.area)
        np.testing.assert_array_equal(c["water"], row(1, 1, 0, 0, 0))     # 2nd pixel: only S2 sees it
        np.testing.assert_array_equal(c["land"], row(0, 0, 1, 0, 0))
        np.testing.assert_array_equal(c["disputed"], row(0, 0, 0, 1, 0))  # S2 land, S1 water
        np.testing.assert_array_equal(c["known"], row(1, 1, 1, 1, 0))
        np.testing.assert_array_equal(c["families"], np.array([[2, 1, 2, 0, 0]]))

    def test_outside_the_area_nothing_is_known(self):
        c = consensus.combine([self.s2], row(0, 0, 0, 0, 0))
        self.assertFalse(c["known"].any())

    def test_agreement_by_source(self):
        c = consensus.combine([self.s2, self.s1], self.area)
        a = consensus.agreement_by_source([self.s2, self.s1], c)
        self.assertEqual(a["s2"], {"family": "optical", "voted_px": 4, "agrees_share": 0.75})
        self.assertEqual(a["s1"]["agrees_share"], round(2 / 3, 4))
        none = consensus.votes("x", "sar", row(0, 0, 0, 0, 0), row(0, 0, 0, 0, 0))
        self.assertIsNone(consensus.agreement_by_source([none], c)["x"]["agrees_share"])


class TestStatusBounds(unittest.TestCase):
    def test_a_status_that_depends_on_the_disputed_pixels_is_undecided(self):
        cons = {"water": row(1, 0), "disputed": row(0, 1), "known": row(1, 1)}

        def status_of(water, known):
            linked = bool(water[0, 1])
            return {"a": [1 if linked else 3, None, 0], "b": [3, None, 0]}
        decided, low, high = consensus.status_bounds(status_of, cons)
        self.assertIsNone(decided["a"])
        self.assertEqual(decided["b"], [3, None, 0])
        self.assertEqual((low["a"][0], high["a"][0]), (3, 1))


class TestShoreBand(unittest.TestCase):
    def test_pixels_on_both_sides_of_the_edge(self):
        water = np.zeros((5, 6), bool)
        water[:, :3] = True
        band = consensus.shore_band(water, np.ones_like(water))
        self.assertTrue(band[:, 2:4].all())
        self.assertFalse(band[:, 0].any() or band[:, 5].any())
        self.assertFalse(consensus.shore_band(np.zeros_like(water), np.ones_like(water)).any())


if __name__ == "__main__":
    unittest.main()
