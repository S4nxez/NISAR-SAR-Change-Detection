"""Official river level next to the hub town (ANA telemetry), shown with the passes so the
record can be read against the river: the radar result should follow it."""
import datetime as dt
import io
import xml.etree.ElementTree as ET

import numpy as np
import requests

from lifeline.config import ANA_TELEMETRY, USER_AGENT, log

LOOKBACK_DAYS = 15
ROW_TAG = "DadosHidrometereologicos"   # sic: ANA's spelling


def parse_gauge(xml_bytes):
    """ANA DadosHidrometeorologicos XML -> {date: daily median level (cm)}."""
    days, when = {}, None
    for _, el in ET.iterparse(io.BytesIO(xml_bytes)):
        tag = el.tag.rsplit("}", 1)[-1]
        if tag == "DataHora":
            when = (el.text or "").strip()[:10]
        elif tag == "Nivel" and when and (el.text or "").strip():
            days.setdefault(when, []).append(float(el.text))
        elif tag == ROW_TAG:
            el.clear()
    return {d: float(np.median(v)) for d, v in sorted(days.items())}


def refresh_gauge(area, cat, get=requests.get, today=None):
    """Store the gauge series in cat["gauge"]; on failure keep the previous series."""
    g = area.get("gauge")
    if not g or not cat["passes"]:
        return
    start = dt.date.fromisoformat(min(p["date"] for p in cat["passes"])) - dt.timedelta(days=LOOKBACK_DAYS)
    params = {"codEstacao": g["ana_code"], "dataInicio": start.strftime("%d/%m/%Y"),
              "dataFim": (today or dt.date.today()).strftime("%d/%m/%Y")}
    try:
        r = get(ANA_TELEMETRY, params=params, timeout=300, headers={"User-Agent": USER_AGENT})
        r.raise_for_status()
        series = parse_gauge(r.content)
    except (requests.RequestException, ValueError, ET.ParseError) as e:
        log(f"river gauge not updated ({e}); keeping the previous series")
        return
    if series:
        cat["gauge"] = {"name": g["name"], "source": f"ANA telemetry, station {g['ana_code']}", "unit": "cm",
                        "series": [[d, round(v, 1)] for d, v in series.items()]}
        log(f"river gauge {g['name']}: {len(series)} days")
