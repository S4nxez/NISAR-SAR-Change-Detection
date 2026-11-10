"""Search of NISAR GCOV passes over an area at the ASF DAAC (no account needed)."""
import datetime as dt

import requests

from lifeline.config import ASF_SEARCH, USER_AGENT
from lifeline.geometry.area import area_wkt


def parse_name(name):
    """NISAR_L2_PR_GCOV_033_161_A_176_2005_DHDH_A_20261023T100258_... -> fields."""
    p = name.split("_")
    return {"cycle": int(p[4]), "track": int(p[5]), "direction": p[6], "frame": int(p[7]),
            "mode": p[8], "pol": p[9], "start": dt.datetime.strptime(p[11], "%Y%m%dT%H%M%S")}


def mode_rank(granule):
    """Sort key of the granules of one frame (lower is better), None for unusable ones:
    provisional before beta, 20 MHz before 40 MHz, dual/single HH before other polarisations."""
    m = granule["mode"]
    if m[:2] == "00":
        return None  # no 20/40 MHz frequency A: only the coarse 5 MHz band
    return (0 if granule["collection"].endswith("PROVISIONAL_V1") else 1,
            {"20": 0, "40": 1}.get(m[:2], 2), 0 if granule["pol"] in ("DHDH", "SHSH") else 1)


def best_granules(features):
    """The best granule of every (day, track, frame) among ASF search features."""
    best = {}
    for feat in features:
        p = feat["properties"]
        name = p["fileName"]
        if not name.endswith(".h5"):
            continue
        g = parse_name(name)
        g.update(name=name, url=p["url"], collection=p["collectionName"])
        rank = mode_rank(g)
        if rank is None:
            continue
        key = (g["start"].date(), g["track"], g["frame"])
        if key not in best or rank < best[key][0]:
            best[key] = (rank, g)
    return [g for _, g in best.values()]


def group_passes(granules):
    """Granules -> passes (all frames of one track on one day): {pass_id: pass}."""
    passes = {}
    for g in granules:
        day = g["start"].date()
        pid = f"{day.isoformat()}_t{g['track']:03d}{g['direction']}"
        ps = passes.setdefault(pid, {"id": pid, "date": day.isoformat(), "track": g["track"],
                                     "direction": "ascending" if g["direction"] == "A" else "descending",
                                     "granules": []})
        ps["granules"].append(g)
    for ps in passes.values():
        ps["granules"].sort(key=lambda g: g["frame"])
        ps["time_utc"] = ps["granules"][0]["start"].strftime("%H:%M")
        ps["frames"] = [g["frame"] for g in ps["granules"]]
        ps["modes"] = sorted({g["mode"] + "_" + g["pol"] for g in ps["granules"]})
        ps["beta"] = any("BETA" in g["collection"] for g in ps["granules"])
    return passes


def search(area, get=requests.get):
    """All GCOV passes over the area: {pass_id: {id, date, track, direction, granules[], ...}}."""
    params = {"dataset": "NISAR", "processingLevel": "GCOV", "output": "geojson",
              "maxResults": "5000", "intersectsWith": area_wkt(area)}
    r = get(ASF_SEARCH, params=params, timeout=180, headers={"User-Agent": USER_AGENT})
    r.raise_for_status()
    return group_passes(best_granules(r.json().get("features", [])))
