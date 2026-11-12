import unittest

import numpy as np

from lifeline.analysis.water import EIGHT_NEIGHBOURS
from lifeline.benchmark import causes
from lifeline.config import STATUS

from ..helpers import river_scene, small_area

RULES = {"cloud_near_m": 100, "level_change_cm": 20, "seasonal_occurrence": [5, 90], "permanent_occurrence": 90,
         "swath_edge_m": 100, "mixed_px": 1, "threshold_margin_db": 1.0, "max_bridge_px": 50}
GAP = (slice(97, 100), slice(120, 125))      # 5 px of the 3 px wide channel the reference calls land


def scene():
    nisar, valid = river_scene(channel_px=3)
    ref = nisar.copy()
    ref[GAP] = False
    return nisar, valid, ref


def ctx(nisar, valid, ref, **extra):
    c = {"ref_water": ref, "ref_known": valid, "nisar_valid": valid, "in_area": np.ones_like(valid),
         "hh": np.where(nisar, -22.0, -6.0).astype(np.float32), "strong_db": -16.0, "weak_db": -14.0}
    c.update(extra)
    return c


class TestPixelCauses(unittest.TestCase):
    def setUp(self):
        self.nisar, self.valid, self.ref = scene()
        self.commission = self.nisar & ~self.ref

    def causes_of(self, **extra):
        cond = causes.conditions(ctx(self.nisar, self.valid, self.ref, **extra), RULES, 20.0)
        return causes.cause_counts(causes.pixel_causes("commission", self.commission, cond))

    def test_a_dark_disputed_pixel_on_unknown_ground_is_unexplained(self):
        # the gap's two end columns (3 px each) touch the reference water: mixed pixels
        self.assertEqual(self.causes_of(), {"shore_mixed_pixel": 6, "unexplained": 9})

    def test_rules_in_order_of_priority(self):
        cloudy = np.zeros_like(self.valid)
        cloudy[95, 122] = True
        occ = np.full(self.valid.shape, 50, np.uint8)
        self.assertEqual(self.causes_of(cloudy=cloudy, occurrence=occ), {"cloud_edge": 15})
        self.assertEqual(self.causes_of(occurrence=occ, level_change_cm=-35.0), {"river_level_change": 15})
        self.assertEqual(self.causes_of(occurrence=occ, level_change_cm=-5.0),
                         {"shore_mixed_pixel": 6, "smooth_ground": 9})
        hh = np.where(self.nisar, -22.0, -6.0).astype(np.float32)
        hh[GAP] = -16.5
        self.assertEqual(self.causes_of(occurrence=occ, hh=hh), {"shore_mixed_pixel": 6, "threshold": 9})

    def test_swath_edge_and_shore(self):
        valid = self.valid.copy()
        valid[90:110, 126:140] = False
        cond = causes.conditions(ctx(self.nisar, valid, self.ref), RULES, 20.0)
        # the west end column is 120 m from the gap in the data: beyond swath_edge_m, a mixed pixel
        self.assertEqual(causes.cause_counts(causes.pixel_causes("commission", self.commission, cond)),
                         {"swath_edge": 12, "shore_mixed_pixel": 3})
        shore = np.zeros_like(self.valid)
        shore[50, 30] = True              # land pixel right beside the river
        cond = causes.conditions(ctx(self.nisar, self.valid, self.ref), RULES, 20.0)
        self.assertEqual(causes.cause_counts(causes.pixel_causes("commission", shore, cond)),
                         {"shore_mixed_pixel": 1})

    def test_omission_causes(self):
        ref, _ = river_scene(channel_px=2)    # a 40 m channel NISAR misses for 5 px
        nisar = ref.copy()
        nisar[GAP] = False
        hh = np.where(nisar, -22.0, -6.0).astype(np.float32)
        cond = causes.conditions(ctx(nisar, self.valid, ref, hh=hh), RULES, 20.0)
        self.assertEqual(causes.cause_counts(causes.pixel_causes("omission", ref & ~nisar, cond)),
                         {"narrow_channel": 10})
        wide = np.zeros_like(ref)
        wide[:, 10:30] = True
        lost = wide.copy()
        lost[40:60, 10:30] = False
        veg = np.zeros_like(ref)
        veg[40:50, :] = True
        occ = np.full(ref.shape, 100, np.uint8)
        hh = np.where(lost, -22.0, -6.0).astype(np.float32)
        cond = causes.conditions(ctx(lost, self.valid, wide, hh=hh, vegetated=veg, occurrence=occ), RULES, 20.0)
        got = causes.cause_counts(causes.pixel_causes("omission", wide & ~lost, cond))
        # the two bank columns are mixed pixels; plants on rows 40-49, wind on the permanent water of rows 50-59
        self.assertEqual(got, {"shore_mixed_pixel": 40, "vegetation": 180, "wind_roughness": 180})
        self.assertEqual(causes.by_family({"vegetation": 2, "wind_roughness": 3, "threshold": 1}),
                         {"radar_physics": 5, "processing": 1})


class TestBridge(unittest.TestCase):
    def setUp(self):
        self.nisar, self.valid, self.ref = scene()
        self.starts = causes.disk_mask(self.nisar.shape, 100, 20, 10)
        self.ends = causes.disk_mask(self.nisar.shape, 100, 230, 5)

    def test_the_gap_the_route_crosses_is_found(self):
        got = causes.bridge_pixels(self.nisar, self.nisar & self.ref, self.starts, self.ends, EIGHT_NEIGHBOURS)
        self.assertEqual(int(got.sum()), 5)
        self.assertTrue(got[GAP].sum() == 5)

    def test_free_route_unreachable_and_too_long(self):
        free = causes.bridge_pixels(self.nisar, self.nisar, self.starts, self.ends)
        self.assertEqual(int(free.sum()), 0)
        self.assertIsNone(causes.bridge_pixels(self.ref, self.ref, self.starts, self.ends))   # cut off
        self.assertIsNone(causes.bridge_pixels(self.nisar, self.nisar & self.ref, self.starts, self.ends,
                                               max_px=3))
        self.assertIsNone(causes.bridge_pixels(self.nisar, self.nisar, np.zeros_like(self.nisar), self.ends))

    def test_disk_mask_is_clipped_at_the_edges(self):
        d = causes.disk_mask((10, 10), 0, 0, 2)
        self.assertTrue(d[0, 0] and d[2, 0] and not d[3, 0])
        self.assertFalse(causes.disk_mask((10, 10), 50, 50, 2).any())


class TestCases(unittest.TestCase):
    def test_kinds(self):
        C, R, ISO = STATUS["connected"], STATUS["at_risk"], STATUS["isolated"]
        self.assertIsNone(causes.case_kind(C, C))
        self.assertEqual(causes.case_kind(R, ISO), "false_route")
        self.assertEqual(causes.case_kind(ISO, C), "false_isolated")
        self.assertEqual(causes.case_kind(C, R), "overconfident")
        self.assertEqual(causes.case_kind(R, C), "underconfident")

    def test_a_false_route_is_located_explained_and_sent_to_review(self):
        nisar, valid, ref = scene()
        area = small_area(px_m=20.0, access_radius_m=100)
        cond = causes.conditions(ctx(nisar, valid, ref), RULES, 20.0)
        communities = [{"id": "a", "name": "Lakeside", "lon": 0, "lat": 0},
                       {"id": "b", "name": "Inland", "lon": 0, "lat": 0},
                       {"id": "c", "name": "Same", "lon": 0, "lat": 0}]
        pred = {"a": [STATUS["at_risk"], 40, 0], "b": [STATUS["isolated"], None, 900],
                "c": [STATUS["connected"], 400, 0]}
        ref_st = {"a": [STATUS["isolated"], None, 0], "b": [STATUS["isolated"], None, 950],
                  "c": [STATUS["connected"], 400, 0]}
        found = causes.cases(area, communities, pred, ref_st, nisar, ref, cond, [(100, 230), (5, 290), (100, 15)],
                             (100, 20, 200), "2026-08-24", "2026-08-25", 50)
        self.assertEqual(len(found), 1)
        c = found[0]
        self.assertEqual((c["community_id"], c["kind"], c["cause"], c["family"], c["culprit_px"], c["review"]),
                         ("a", "false_route", "unexplained", "unexplained", 5, True))
        lon, lat = causes.pixel_lonlat(area, 98, 122)
        self.assertAlmostEqual(c["lon"], round(lon, 5), places=4)
        self.assertIn("datasetId=S2_L2A_CDAS", c["links"]["sentinel2"])
        self.assertIn("fromTime=2026-08-25", c["links"]["sentinel1"])
        self.assertIn("openstreetmap.org", c["links"]["openstreetmap"])

    def test_explain_case_without_culprits(self):
        nisar, valid, ref = scene()
        cond = causes.conditions(ctx(nisar, valid, ref), RULES, 20.0)
        self.assertEqual(causes.explain_case("false_route", None, nisar, ref, cond), ("unexplained", {}))
        self.assertEqual(causes.explain_case("overconfident", np.zeros_like(nisar), nisar, ref, cond),
                         ("narrow_channel", {}))

    def test_cases_are_grouped_into_sites_named_after_the_nearest_community(self):
        def case(cid, name, kind, lon, lat, pass_id, review=True, cause="swath_edge"):
            return {"community_id": cid, "community": name, "kind": kind, "lon": lon, "lat": lat, "pass": pass_id,
                    "cause": cause, "review": review, "links": {"sentinel2": f"s2-{pass_id}"}}
        communities = [{"id": "i", "name": "Itauba", "lon": -64.320, "lat": -3.585},
                       {"id": "p", "name": "Prainha", "lon": -64.36, "lat": -3.53},
                       {"id": "f", "name": "Far", "lon": -64.80, "lat": -3.40}]
        found = [case("i", "Itauba", "false_route", -64.316, -3.587, "p1"),
                 case("p", "Prainha", "false_route", -64.3165, -3.5872, "p2"),
                 case("m", "Marajo", "overconfident", -64.3170, -3.5875, "p2", cause="cloud_edge"),
                 case("x", "Acapu", "false_isolated", -64.317, -3.587, "p1", review=False, cause="narrow_channel"),
                 case("f", "Far", "false_route", -64.80, -3.40, "p1")]
        got = causes.sites(found, communities)
        self.assertEqual(len(got), 3)
        first = got[0]
        self.assertEqual((first["near"], first["side"], first["cases"], first["cause"]),
                         ("Itauba", "dangerous", 3, "swath_edge"))
        self.assertEqual(first["communities"], ["Itauba", "Marajo", "Prainha"])
        self.assertEqual(first["passes"], ["p1", "p2"])
        self.assertEqual(first["links"], {"p1": {"sentinel2": "s2-p1"}, "p2": {"sentinel2": "s2-p2"}})
        self.assertLess(first["distance_km"], 1.0)
        self.assertEqual(got[-1]["side"], "safe")                 # same place, other side, no review: last
        self.assertFalse(got[-1]["review"])
        self.assertAlmostEqual(causes.distance_m(-64.0, -3.0, -64.0, -3.01), 1105.4, places=1)
        self.assertEqual(causes.nearest_community(0, 0, []), (None, None))

    def test_copernicus_link(self):
        url = causes.copernicus_link(-64.75, -3.4, "2026-08-24", "S2_L2A_CDAS", "1_TRUE_COLOR")
        self.assertTrue(url.startswith(causes.COPERNICUS_BROWSER + "?zoom=15&lat=-3.40000&lng=-64.75000"))
        self.assertIn("toTime=2026-08-24T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR", url)
        self.assertNotIn("layerId", causes.copernicus_link(0, 0, "2026-08-24", "S1_CDAS_IW_VVVH"))


if __name__ == "__main__":
    unittest.main()
