import pandas as pd
import math
import random

# ----------------------
# Helpers
# ----------------------
def sql(v):
    if pd.isna(v):
        return "NULL"
    if isinstance(v, str):
        return "'" + v.replace("'", "''") + "'"
    return str(v)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def nearest_k_pairs(items, k=5):
    # items: list of dicts with keys id, lat, lon
    pairs = []
    for i, a in enumerate(items):
        dists = []
        for j, b in enumerate(items):
            if i == j:
                continue
            d = haversine(a["lat"], a["lon"], b["lat"], b["lon"])
            dists.append((d, b))
        dists.sort(key=lambda x: x[0])
        for d, b in dists[:k]:
            pairs.append((a, b, d))
    return pairs

# ----------------------
# 1) Load source files
# ----------------------
countries = pd.read_csv("countries.csv")
airports = pd.read_csv("airports.csv")

# Column detection for flexible CSVs
COUNTRY_NAME_COL = "name" if "name" in countries.columns else "country"
COUNTRY_CODE_COL = "code" if "code" in countries.columns else "iso_country"

AIRPORT_NAME_COL = "name"
AIRPORT_COUNTRY_COL = "iso_country"
LAT_COL = "latitude_deg" if "latitude_deg" in airports.columns else "latitude"
LON_COL = "longitude_deg" if "longitude_deg" in airports.columns else "longitude"
TYPE_COL = "type" if "type" in airports.columns else None

# ----------------------
# 2) Static catalog ids
# ----------------------
location_kind_id = {
    "COUNTRY_HUB": 1,
    "AIRPORT": 2,
    "PORT": 3,
    "CITY": 4,
}

transport_type_id = {
    "AIR": 1,
    "SEA": 2,
    "LAND": 3,
}

tariff_type_id = {
    "MFN": 1,
    "APPLIED": 2,
    "AVERAGE": 3,
    "MOCK": 4,
}

# ----------------------
# 3) Build country inserts
# ----------------------
country_rows = []
country_id_map = {}
country_id = 1

for _, row in countries.iterrows():
    iso2 = str(row[COUNTRY_CODE_COL]).strip()
    name = str(row[COUNTRY_NAME_COL]).strip()
    country_id_map[iso2] = country_id
    country_rows.append(
        f"INSERT INTO country (id, name, iso2) VALUES ({country_id}, {sql(name)}, {sql(iso2)});"
    )
    country_id += 1

# ----------------------
# 4) Build one location per country
#    Prefer a large airport, then medium, then any airport
# ----------------------
location_rows = []
location_id_map = {}
location_id = 1

if TYPE_COL and TYPE_COL in airports.columns:
    airports = airports[airports[TYPE_COL].isin(["large_airport", "medium_airport", "small_airport"])].copy()

for iso2, cid in country_id_map.items():
    group = airports[airports[AIRPORT_COUNTRY_COL] == iso2].copy()

    if group.empty:
        continue  # if you need full coverage, add a centroid fallback from Natural Earth

    # Rank airport preference
    if TYPE_COL and TYPE_COL in group.columns:
        priority = {"large_airport": 0, "medium_airport": 1, "small_airport": 2}
        group["prio"] = group[TYPE_COL].map(priority).fillna(9)
        group = group.sort_values(["prio"])
    else:
        group = group.head(1)

    airport = group.iloc[0]

    name = iso2  # hub name for MVP
    code = iso2
    lat = float(airport[LAT_COL])
    lon = float(airport[LON_COL])

    location_rows.append(
        f"""INSERT INTO location
(id, country_id, kind_id, name, code, latitude, longitude, active)
VALUES
({location_id}, {cid}, {location_kind_id["COUNTRY_HUB"]}, {sql(name)}, {sql(code)}, {lat:.6f}, {lon:.6f}, TRUE);"""
    )
    location_id_map[iso2] = {
        "id": location_id,
        "lat": lat,
        "lon": lon,
        "name": name,
    }
    location_id += 1

# ----------------------
# 5) Build route_edge inserts
#    Connect each country hub to its k nearest country hubs
# ----------------------
route_rows = []
route_id = 1
nodes = []

for iso2, data in location_id_map.items():
    nodes.append({
        "iso2": iso2,
        "id": data["id"],
        "lat": data["lat"],
        "lon": data["lon"],
    })

k = 5
pairs = nearest_k_pairs(nodes, k=k)

seen = set()
for a, b, dist in pairs:
    key = (a["id"], b["id"], transport_type_id["AIR"])
    if key in seen:
        continue
    seen.add(key)

    base_cost = dist * 0.12
    est_hours = dist / 750.0  # mock air speed

    route_rows.append(
        f"""INSERT INTO route_edge
(id, origin_location_id, destination_location_id, transport_type_id, distance_km, base_cost, estimated_hours, active)
VALUES
({route_id}, {a["id"]}, {b["id"]}, {transport_type_id["AIR"]}, {dist:.2f}, {base_cost:.2f}, {est_hours:.2f}, TRUE);"""
    )
    route_id += 1

# ----------------------
# 6) Build tariff inserts
#    One mock tariff row per country
# ----------------------
tariff_rows = []
tariff_id = 1

for iso2, cid in country_id_map.items():
    rate = round(random.uniform(2, 15), 3)
    tariff_rows.append(
        f"""INSERT INTO tariff
(id, country_id, partner_country_id, hs6_code, rate_pct, tariff_type_id, source, effective_from, effective_to)
VALUES
({tariff_id}, {cid}, NULL, NULL, {rate}, {tariff_type_id["MOCK"]}, 'MOCK', NULL, NULL);"""
    )
    tariff_id += 1

# ----------------------
# 7) Write seed.sql
# ----------------------
with open("seed.sql", "w", encoding="utf-8") as f:
    f.write("-- Catalog tables\n")
    f.write("INSERT INTO location_kind (code) VALUES ('COUNTRY_HUB'), ('AIRPORT'), ('PORT'), ('CITY');\n")
    f.write("INSERT INTO transport_type (code) VALUES ('AIR'), ('SEA'), ('LAND');\n")
    f.write("INSERT INTO tariff_type (code) VALUES ('MFN'), ('APPLIED'), ('AVERAGE'), ('MOCK');\n\n")

    f.write("-- country\n")
    f.write("\n".join(country_rows))
    f.write("\n\n-- location\n")
    f.write("\n".join(location_rows))
    f.write("\n\n-- route_edge\n")
    f.write("\n".join(route_rows))
    f.write("\n\n-- tariff\n")
    f.write("\n".join(tariff_rows))

print("seed.sql generated")