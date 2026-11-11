import os
import tempfile
import unittest

import numpy as np

from lifeline.benchmark.scoring import (
    cohen_kappa,
    confusion,
    grade,
    rates,
    spearman,
    status_scores,
    unpack_layers,
    water_scores,
    width_strata,
)
from lifeline.output.layers import save_mask

C, R, ISO, N = 1, 2, 3, 0   # connected, at risk, isolated, no data


class TestWaterScores(unittest.TestCase):
    def test_confusion_and_rates_of_known_masks(self):
        pred = np.array([1, 1, 0, 0, 1], bool)
        ref = np.array([1, 0, 1, 0, 1], bool)
        mask = np.array([1, 1, 1, 1, 0], bool)   # the last pixel is not judged
        c = confusion(pred, ref, mask)
        self.assertEqual(c, {"tp": 1, "fp": 1, "fn": 1, "tn": 1})
        self.assertEqual(rates(c), {"iou": 0.3333, "f1": 0.5, "precision": 0.5, "recall": 0.5})

    def test_rates_are_undefined_without_positives(self):
        self.assertEqual(rates({"tp": 0, "fp": 0, "fn": 0, "tn": 9}),
                         {"iou": None, "f1": None, "precision": None, "recall": None})

    def test_width_strata_split_channels_by_width(self):
        water = np.zeros((60, 80), bool)
        water[:, 0:20] = True        # 400 m river
        water[30:32, 20:80] = True   # 40 m channel
        water[10:14, 20:80] = True   # 80 m channel
        s = width_strata(water, 20.0)
        self.assertTrue(s["narrow_lt60m"][30:32, 40:60].all())
        self.assertTrue(s["medium_60_200m"][10:14, 40:60].all())
        self.assertTrue(s["wide_ge200m"][:, 5:15].all())
        self.assertFalse((s["narrow_lt60m"] & s["wide_ge200m"]).any())

    def test_water_scores_split_false_water_by_distance_to_the_shore(self):
        ref = np.zeros((50, 50), bool)
        ref[:, :10] = True
        pred = ref.copy()
        pred[:, 10:12] = True        # 40 m too wide at the shore
        pred[40:42, 40:42] = True    # a far false patch
        out = water_scores(pred, ref, np.ones_like(ref), 20.0)
        self.assertEqual(out["recall"], 1.0)
        self.assertEqual(out["false_water"]["shore"]["rate"], round(100 / (50 * 5), 4))   # 5 px = 100 m band
        self.assertEqual(out["false_water"]["far"]["rate"], round(4 / (50 * 35), 4))


class TestStatusScores(unittest.TestCase):
    def test_cohen_kappa_of_a_known_table(self):
        self.assertEqual(cohen_kappa([(1, 1), (1, 1), (3, 3), (3, 1)], [1, 2, 3]), 0.5)   # po 0.75, pe 0.5
        self.assertIsNone(cohen_kappa([], [1, 2, 3]))
        self.assertIsNone(cohen_kappa([(1, 1)], [1, 2, 3]))   # no chance disagreement

    def test_errors_are_named_by_their_consequence(self):
        pred = {"a": [C, 100, 10], "b": [R, 40, 10], "c": [ISO, None, 10], "d": [C, 200, 10], "e": [N, None, None],
                "f": [ISO, None, 5000]}
        ref = {"a": [ISO, None, 10], "b": [ISO, None, 10], "c": [C, 200, 10], "d": [R, 40, 10], "e": [C, 100, 10],
               "f": [ISO, None, 4000]}
        s = status_scores(pred, ref, list(pred), access_m=1000)
        self.assertEqual(s["n"], 4)                     # e has no data, f is inland in both
        self.assertEqual((s["false_route"], s["overconfident"], s["false_isolated"]), (2, 1, 1))
        self.assertEqual(s["agreement"], 0.0)
        self.assertEqual(s["isolated_recall"], 0.0)
        self.assertEqual(s["matrix_pred_by_ref"]["connected"]["isolated"], 1)

    def test_perfect_agreement(self):
        st = {"a": [C, 200, 10], "b": [ISO, None, 10], "c": [R, 40, 10]}
        s = status_scores(st, st, list(st), 1000)
        self.assertEqual((s["agreement"], s["kappa"], s["isolated_recall"]), (1.0, 1.0, 1.0))


class TestOther(unittest.TestCase):
    def test_spearman_sign_and_undefined_cases(self):
        self.assertEqual(spearman([1, 2, 3, 4], [40, 30, 20, 10]), {"rho": -1.0, "n": 4})
        self.assertEqual(spearman([1, 2, None, 4], [1, 2, 3, 4])["n"], 3)
        self.assertIsNone(spearman([1, 2], [1, 2])["rho"])
        self.assertIsNone(spearman([1, 2, 3], [5, 5, 5])["rho"])

    def test_grades_accept_the_safe_side_on_narrow_channels_only(self):
        self.assertEqual([grade("connected", c) for c in (C, R, ISO, N)],
                         ["correct", "conservative", "conservative", "no_data"])
        self.assertEqual([grade("narrow", c) for c in (C, R, ISO)], ["dangerous", "correct", "correct"])
        self.assertEqual([grade("isolated", c) for c in (C, R, ISO)], ["dangerous", "dangerous", "correct"])
        with self.assertRaises(ValueError):
            grade("maybe", C)

    def test_unpack_layers_reads_every_layer_of_a_mask_file(self):
        water = np.zeros((7, 9), bool)
        water[2:4, 1:5] = True
        valid = np.ones_like(water)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "water.npz")
            save_mask(water, valid, path)
            layers = unpack_layers(path)
        np.testing.assert_array_equal(layers["water"], water)
        np.testing.assert_array_equal(layers["valid"], valid)


if __name__ == "__main__":
    unittest.main()
