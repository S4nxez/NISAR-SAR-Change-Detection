"""Communities of an area from OpenStreetMap, with the water access people actually use."""
import json
import os

import requests

from .area import in_area
from .config import AREAS_DIR, OVERPASS_MIRRORS, USER_AGENT
from .geo import fold, metres

PLACE_TYPES = "town|village|hamlet|isolated_dwelling|locality"
PORT_PREFIXES = ("porto de ", "porto do ", "porto da ", "porto ")
PORT_MAX_M = 5000   # a "Porto de X" further than this from X is another place
ATTRIBUTION = "© OpenStreetMap contributors (ODbL)"


def overpass(query, post=requests.post):
    """Elements of an Overpass query, trying each mirror in turn."""
    last = None
    for url in OVERPASS_MIRRORS:
        try:
            r = post(url, data={"data": query}, timeout=180, headers={"User-Agent": USER_AGENT})
            r.raise_for_status()
            return r.json().get("elements", [])
        except (requests.RequestException, ValueError) as e:
            last = e
    raise SystemExit(f"OpenStreetMap (Overpass) is not answering: {last}")


def osm_box(area):
    lon0, lat0, lon1, lat1 = area["bbox"]
    return f"({lat0},{lon0},{lat1},{lon1})"


def place_from_element(e):
    """Overpass place node -> community dict, None when it has no name."""
    t = e.get("tags", {})
    if not t.get("name"):
        return None
    p = {"id": f"osm{e['id']}", "name": t["name"], "place": t.get("place"),
         "lon": round(e["lon"], 6), "lat": round(e["lat"], 6)}
    if t.get("population", "").isdigit():
        p["population"] = int(t["population"])
    return p


def landing_from_element(e):
    """Overpass ferry terminal, pier or harbour (node, way or relation) -> {lon, lat, kind}."""
    t, c = e.get("tags", {}), e.get("center", e)
    if t.get("amenity") == "ferry_terminal":
        kind = "ferry terminal"
    elif t.get("man_made") == "pier":
        kind = "pier"
    else:
        kind = "harbour"
    return {"lon": round(c["lon"], 6), "lat": round(c["lat"], 6), "kind": kind}


def fetch_places(area, query=overpass):
    box = osm_box(area)
    elements = query(f'[out:json][timeout:90];(node["place"~"^({PLACE_TYPES})$"]{box};);out body;')
    return [p for p in map(place_from_element, elements) if p]


def fetch_landings(area, query=overpass):
    box = osm_box(area)
    q = (f'[out:json][timeout:90];(nwr["amenity"="ferry_terminal"]{box};nwr["harbour"]{box};'
         f'nwr["landuse"~"^(port|harbour)$"]{box};nwr["man_made"="pier"]{box};);out center tags;')
    return [landing_from_element(e) for e in query(q)]


def _port_owner_name(folded_name, by_name):
    for prefix in PORT_PREFIXES:
        if folded_name.startswith(prefix):
            owner = folded_name[len(prefix):]
            return owner if owner in by_name else None
    return None


def assign_access(places, landings, snap_m):
    """
    A place node marks the middle of a settlement, which for a town can be a kilometre or more
    from its waterfront. Give each place the water access people actually use:
      - a place called "Porto de X" / "Porto X" near X is X's port: it becomes X's access point
        and is dropped as a community of its own;
      - otherwise the nearest landing (ferry terminal, pier, harbour) within snap_m[place type].
    Places get "access" = [lon, lat] and "access_source" when moved.
    """
    by_name = {}
    for p in places:
        by_name.setdefault(fold(p["name"]), []).append(p)
    ports = set()
    for p in places:
        owner = _port_owner_name(fold(p["name"]), by_name)
        if owner is None:
            continue
        owners = [o for o in by_name[owner] if metres(o["lon"], o["lat"], p["lon"], p["lat"]) <= PORT_MAX_M]
        for o in owners:
            o["access"], o["access_source"] = [p["lon"], p["lat"]], f"port: {p['name']}"
        if owners:
            ports.add(id(p))
    kept = [p for p in places if id(p) not in ports]
    for p in kept:
        if "access" in p:
            continue
        limit = snap_m.get(p.get("place"), snap_m.get("default", 0))
        dist, landing = min(((metres(p["lon"], p["lat"], ld["lon"], ld["lat"]), ld) for ld in landings),
                            key=lambda t: t[0], default=(None, None))
        if landing is not None and 0 < dist <= limit:
            p["access"], p["access_source"] = [landing["lon"], landing["lat"]], landing["kind"]
    return kept


def communities_collection(area, places):
    """GeoJSON of the area's communities: the hub town is taken out (its water access, if any,
    goes to "hub_access") and so are the places outside the area."""
    hub_place = next((p for p in places if fold(p["name"]) == fold(area["hub"]["name"])), None)
    kept = [p for p in places if p is not hub_place and in_area(area, p["lon"], p["lat"])]
    feats = [{"type": "Feature", "properties": {k: v for k, v in p.items() if k not in ("lon", "lat")},
              "geometry": {"type": "Point", "coordinates": [p["lon"], p["lat"]]}}
             for p in sorted(kept, key=lambda p: p["name"])]
    out = {"type": "FeatureCollection", "attribution": ATTRIBUTION, "features": feats}
    if hub_place and hub_place.get("access"):
        out["hub_access"] = {"lon": hub_place["access"][0], "lat": hub_place["access"][1],
                             "source": hub_place["access_source"]}
    return out


def communities_path(area, areas_dir=AREAS_DIR):
    return os.path.join(areas_dir, area["communities"])


def save_communities(area, collection, areas_dir=AREAS_DIR):
    with open(communities_path(area, areas_dir), "w", encoding="utf-8") as f:
        json.dump(collection, f, ensure_ascii=False, indent=1)


def load_communities(area, areas_dir=AREAS_DIR):
    """Communities inside the area, as dicts with lon and lat. Sets the hub's water access
    (area["hub"]["access"]) when the file has one."""
    path = communities_path(area, areas_dir)
    if not os.path.exists(path):
        raise SystemExit(f"Missing {path}: run `river_monitor.py communities` first.")
    with open(path, encoding="utf-8") as f:
        fc = json.load(f)
    if fc.get("hub_access"):
        area["hub"] = {**area["hub"], "access": fc["hub_access"]}
    out = []
    for feat in fc["features"]:
        lon, lat = feat["geometry"]["coordinates"]
        if in_area(area, lon, lat):
            out.append({**feat["properties"], "lon": lon, "lat": lat})
    return out
