import pandas as pd
import math
import random
from datetime import date, timedelta

# ----------------------
# Helpers
# ----------------------
def sql(v):
    if v is None or (not isinstance(v, str) and pd.isna(v)):
        return "NULL"
    if isinstance(v, str):
        return "'" + v.replace("'", "''") + "'"
    return str(v)

def to_db(linear):
    return 10.0 * math.log10(linear)

def to_linear(db):
    return 10.0 ** (db / 10.0)

# ----------------------
# 1) Load source files
#    countries.csv resuelve ISO2 -> nombre de país
# ----------------------
countries = pd.read_csv("countries.csv")

COUNTRY_NAME_COL = "name" if "name" in countries.columns else "country"
COUNTRY_CODE_COL = "code" if "code" in countries.columns else "iso_country"

country_name = {
    str(row[COUNTRY_CODE_COL]).strip(): str(row[COUNTRY_NAME_COL]).strip()
    for _, row in countries.iterrows()
}

# ----------------------
# 2) Escenarios de cambio SAR
#    Respuesta típica (dB) de VV/VH tras el evento. Valores ilustrativos.
# ----------------------
scenarios = {
    "FLOOD":         {"vv": -3.5, "vh": -2.8},   # agua especular -> baja retrodispersión
    "WETLAND":       {"vv": -1.5, "vh": -1.2},
    "WILDFIRE":      {"vv": -4.0, "vh": -4.5},   # pérdida de biomasa -> cae sobre todo VH
    "DEFORESTATION": {"vv": -3.7, "vh": -4.6},
    "AGRICULTURE":   {"vv":  2.0, "vh":  2.0},   # crecimiento del cultivo
    "URBAN":         {"vv":  3.0, "vh":  1.0},   # dobles rebotes en estructuras
}

# Sitios: (id, nombre, iso2, lat, lon, categoría, VV base, VH base, descripción)
sites = [
    ("ES_VALENCIA_001", "Albufera de Valencia", "ES", 39.3040, -0.3550, "FLOOD", -10.2, -17.4,
     "Zona humeda cercana a Valencia para simular cambios de superficie inundada."),
    ("BR_AMAZON_001", "Amazonas - zona de Manaus", "BR", -3.1000, -60.0000, "DEFORESTATION", -7.8, -13.1,
     "Zona de bosque tropical para simular perdida de cubierta forestal."),
    ("CA_ALBERTA_001", "Bosques de Alberta", "CA", 54.5000, -115.0000, "WILDFIRE", -8.1, -13.9,
     "Area forestal canadiense para simular cambios de superficie tras un incendio."),
]

# NISAR: ciclo de repetición de 12 días
REVISIT_DAYS = 12
N_OBSERVATIONS = 6
EVENT_INDEX = 3
NOISE_DB = 0.25

# ----------------------
# 3) Build sar_site + sar_observation inserts
# ----------------------
site_rows = []
observation_rows = []

for site_id, name, iso2, lat, lon, category, vv_base, vh_base, description in sites:
    delta = scenarios[category]
    start = date(2024, random.randint(1, 10), 1)

    vv_series, vh_series = [], []
    for i in range(N_OBSERVATIONS):
        # Recuperación parcial tras el evento
        factor = 0.0 if i < EVENT_INDEX else 1.0 - 0.15 * (i - EVENT_INDEX)
        vv = vv_base + delta["vv"] * factor + random.gauss(0, NOISE_DB)
        vh = vh_base + delta["vh"] * factor + random.gauss(0, NOISE_DB)
        vv_series.append(vv)
        vh_series.append(vh)
        obs_date = start + timedelta(days=REVISIT_DAYS * i)
        observation_rows.append(
            f"('{site_id}', '{obs_date.isoformat()}', {vv:.3f}, {vh:.3f})"
        )

    # Log-ratio (dB) entre media post-evento y pre-evento sobre VH
    pre = sum(to_linear(v) for v in vh_series[:EVENT_INDEX]) / EVENT_INDEX
    post = sum(to_linear(v) for v in vh_series[EVENT_INDEX:]) / (N_OBSERVATIONS - EVENT_INDEX)
    log_ratio = to_db(post / pre)

    level = "HIGH" if abs(log_ratio) >= 3 else "MEDIUM" if abs(log_ratio) >= 1.5 else "LOW"
    direction = "INCREASE" if log_ratio > 0 else "DECREASE"
    confidence = min(0.999, 0.80 + abs(log_ratio) * 0.03)

    site_rows.append(
        f"({sql(site_id)}, {sql(name)}, {sql(country_name.get(iso2, iso2))}, {lat:.4f}, {lon:.4f}, "
        f"{sql(level)}, {sql(direction)}, {sql(category)}, {sql(description)}, {confidence:.3f})"
    )

# ----------------------
# 4) Write seed.sql
# ----------------------
with open("seed.sql", "w", encoding="utf-8") as f:
    f.write("-- Datos sintéticos generados por sql_generator.py (no son mediciones NISAR reales)\n")
    f.write("INSERT INTO sar_site (id, name, country, latitude, longitude, change_level, change_value, "
            "category, description, confidence) VALUES\n")
    f.write(",\n".join(site_rows) + ";\n\n")
    f.write("INSERT INTO sar_observation (site_id, observation_date, vv, vh) VALUES\n")
    f.write(",\n".join(observation_rows) + ";\n")
