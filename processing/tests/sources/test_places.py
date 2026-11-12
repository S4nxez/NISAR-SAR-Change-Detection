import unittest

import requests

from lifeline.sources.places import (
    assign_access,
    communities_collection,
    fetch_landings,
    fetch_places,
    landing_from_element,
    load_communities,
    overpass,
    place_from_element,
    save_communities,
)

from ..helpers import FakeResponse, TempDirTest, small_area


class TestAccess(unittest.TestCase):
    SNAP = {"town": 3000, "hamlet": 500, "default": 300}

    def test_town_takes_its_port_and_the_port_is_not_a_community(self):
        places = [{"name": "Alvarães", "place": "town", "lon": -64.8148, "lat": -3.2156},
                  {"name": "Porto de Alvaraes", "place": "locality", "lon": -64.8044, "lat": -3.2110}]
        kept = assign_access(places, [], self.SNAP)
        self.assertEqual([p["name"] for p in kept], ["Alvarães"])
        self.assertEqual(kept[0]["access"], [-64.8044, -3.2110])
        self.assertIn("Porto de Alvaraes", kept[0]["access_source"])

    def test_nearest_landing_within_the_limit_of_the_place_type(self):
        landing = [{"lon": -64.810, "lat": -3.211, "kind": "ferry terminal"}]   # ~600 m away
        town = {"name": "A", "place": "town", "lon": -64.8148, "lat": -3.2140}
        hamlet = {"name": "B", "place": "hamlet", "lon": -64.8148, "lat": -3.2140}
        a, = assign_access([town], landing, self.SNAP)
        b, = assign_access([hamlet], landing, self.SNAP)
        self.assertEqual(a["access_source"], "ferry terminal")
        self.assertNotIn("access", b)

    def test_unknown_place_type_uses_the_default_limit(self):
        landing = [{"lon": -64.8148, "lat": -3.2120, "kind": "pier"}]   # ~220 m away
        p, = assign_access([{"name": "C", "place": "locality", "lon": -64.8148, "lat": -3.2140}], landing, self.SNAP)
        self.assertEqual(p["access_source"], "pier")

    def test_a_place_on_its_landing_keeps_its_position(self):
        landing = [{"lon": -64.8148, "lat": -3.2140, "kind": "pier"}]
        p, = assign_access([{"name": "D", "place": "hamlet", "lon": -64.8148, "lat": -3.2140}], landing, self.SNAP)
        self.assertNotIn("access", p)

    def test_a_far_port_with_the_same_name_is_ignored(self):
        places = [{"name": "Nazaré", "place": "hamlet", "lon": -64.53, "lat": -3.17},
                  {"name": "Porto Nazaré", "place": "hamlet", "lon": -64.90, "lat": -3.60}]   # ~60 km apart
        kept = assign_access(places, [], self.SNAP)
        self.assertEqual(len(kept), 2)
        self.assertNotIn("access", kept[0])

    def test_a_port_named_after_no_place_is_a_community(self):
        kept = assign_access([{"name": "Porto Velho", "place": "hamlet", "lon": -64.5, "lat": -3.1}], [], self.SNAP)
        self.assertEqual(len(kept), 1)


class TestOverpassElements(unittest.TestCase):
    def test_place_from_element(self):
        e = {"id": 7, "lon": -64.1234567, "lat": -3.7654321, "tags": {"name": "Caiambé", "place": "village",
                                                                      "population": "1200"}}
        self.assertEqual(place_from_element(e), {"id": "osm7", "name": "Caiambé", "place": "village",
                                                 "lon": -64.123457, "lat": -3.765432, "population": 1200})
        self.assertNotIn("population", place_from_element({**e, "tags": {"name": "X", "population": "about 50"}}))
        self.assertIsNone(place_from_element({**e, "tags": {"place": "hamlet"}}))

    def test_landing_kinds_and_way_centres(self):
        self.assertEqual(landing_from_element({"lon": 1, "lat": 2, "tags": {"amenity": "ferry_terminal"}})["kind"],
                         "ferry terminal")
        self.assertEqual(landing_from_element({"center": {"lon": 1, "lat": 2}, "tags": {"man_made": "pier"}}),
                         {"lon": 1, "lat": 2, "kind": "pier"})
        self.assertEqual(landing_from_element({"lon": 1, "lat": 2, "tags": {"landuse": "port"}})["kind"], "harbour")

    def test_fetch_queries_the_area_box(self):
        queries = []

        def query(q):
            queries.append(q)
            return [{"id": 1, "lon": -64.77, "lat": -3.42, "tags": {"name": "A", "place": "hamlet"}}]

        self.assertEqual(fetch_places(small_area(), query)[0]["name"], "A")
        fetch_landings(small_area(), query)
        self.assertTrue(all("(-3.44,-64.8,-3.4,-64.74)" in q for q in queries))

    def test_overpass_falls_back_to_the_next_mirror(self):
        calls = []

        def post(url, data, timeout, headers):
            calls.append(url)
            if len(calls) == 1:
                raise requests.ConnectionError("down")
            return FakeResponse(json_data={"elements": [{"id": 1}]})

        self.assertEqual(overpass("q", post=post), [{"id": 1}])
        self.assertEqual(len(calls), 2)

    def test_overpass_exits_when_every_mirror_fails(self):
        with self.assertRaisesRegex(SystemExit, "Overpass"):
            overpass("q", post=lambda *a, **k: FakeResponse(504))


class TestCommunitiesFile(TempDirTest):
    def places(self):
        return [{"id": "osm1", "name": "Hub", "place": "town", "lon": -64.796, "lat": -3.42,
                 "access": [-64.797, -3.421], "access_source": "pier"},
                {"id": "osm2", "name": "Bravo", "place": "hamlet", "lon": -64.76, "lat": -3.41},
                {"id": "osm3", "name": "Alpha", "place": "hamlet", "lon": -64.77, "lat": -3.43},
                {"id": "osm4", "name": "Far", "place": "hamlet", "lon": -64.50, "lat": -3.43}]

    def test_collection_drops_the_hub_and_places_outside_and_sorts_by_name(self):
        fc = communities_collection(small_area(), self.places())
        self.assertEqual([f["properties"]["name"] for f in fc["features"]], ["Alpha", "Bravo"])
        self.assertEqual(fc["features"][0]["geometry"]["coordinates"], [-64.77, -3.43])
        self.assertNotIn("lon", fc["features"][0]["properties"])
        self.assertEqual(fc["hub_access"], {"lon": -64.797, "lat": -3.421, "source": "pier"})
        self.assertIn("OpenStreetMap", fc["attribution"])

    def test_saved_file_loads_back_with_the_hub_access(self):
        area = small_area()
        save_communities(area, communities_collection(area, self.places()), self.tmp)
        loaded = load_communities(area, self.tmp)
        self.assertEqual([c["name"] for c in loaded], ["Alpha", "Bravo"])
        self.assertEqual((loaded[0]["lon"], loaded[0]["lat"]), (-64.77, -3.43))
        self.assertEqual(area["hub"]["access"]["source"], "pier")

    def test_missing_file_explains_how_to_create_it(self):
        with self.assertRaisesRegex(SystemExit, "communities"):
            load_communities(small_area(), self.tmp)


if __name__ == "__main__":
    unittest.main()
