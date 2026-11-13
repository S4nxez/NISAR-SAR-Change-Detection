"""NISAR against Sentinel-1: where the two radars agree and the places where they disagree, for a person to check.

Sentinel-1 is part of the method since ADR-007, so it cannot be a reference of the exam any more; this section is
not scored. For every pass with Sentinel-1 scenes it compares the status each radar alone gives every community (the
monitor's route rule on NISAR water, without the low-water rule, and on Sentinel-1 water) and lists the
disagreements as cases, with the culprit pixels, a probable cause (the zone type: seasonal ground, narrow channel,
vegetation...) and links. The verdicts people give (processing/benchmark/crosscheck_reviews.json: "nisar",
"sentinel1" or "undecidable") are counted per zone type: they measure where each radar is more precise, and so
which one the method should trust in each kind of place.
"""
import json
import os

from lifeline.benchmark import causes, reviews
from lifeline.config import STATUS

VERDICTS = ("nisar", "sentinel1", "undecidable")


def load_reviews(path):
    """The crosscheck verdicts of the file (missing file: none)."""
    return reviews.load(path, VERDICTS)


def followed(fused, nisar, s1):
    """Which radar the published status of a community follows: "sentinel1", "nisar", "both" or "neither"."""
    a, b = fused == s1, fused == nisar
    return "both" if a and b else "sentinel1" if a else "nisar" if b else "neither"


def pass_cases(area, communities, fused, nisar_status, s1_status, nisar_water, s1_water, cond, targets, hub,
               s2_date, s1_date, max_px):
    """Cases of one pass: every community whose NISAR-alone and Sentinel-1-alone statuses differ ("false_route":
    NISAR links it and Sentinel-1 does not, and so on, NISAR in the role of the method), with the radar the published
    status followed."""
    found = causes.cases(area, communities, nisar_status, s1_status, nisar_water, s1_water, cond, targets, hub,
                         s2_date, s1_date, max_px)
    for c in found:
        c["followed"] = followed((fused.get(c["community_id"]) or [STATUS["no_data"]])[0], c["status"],
                                 c["reference_status"])
        c["review"] = True
    return found


def tally(cases):
    """Verdicts per zone type (the case's cause): cases, NISAR right, Sentinel-1 right, undecidable, pending."""
    out = {}
    for c in cases:
        k = out.setdefault(c["cause"], {"cases": 0, "nisar": 0, "sentinel1": 0, "undecidable": 0, "pending": 0})
        k["cases"] += 1
        k[(c.get("reviewed") or {}).get("verdict") or "pending"] += 1
    return out


def summary(rows, cases, found_sites):
    """Pooled agreement of the two radars and the counts of the review list."""
    judged = sum(r.get("judged_km2") or 0 for r in rows)
    agree = sum((r.get("judged_km2") or 0) * (r.get("agreement") or 0) for r in rows)
    return {"passes": len(rows), "judged_km2": round(judged, 1),
            "agreement": round(agree / judged, 4) if judged else None,
            "nisar_only_km2": round(sum(r.get("nisar_only_km2") or 0 for r in rows), 1),
            "sentinel1_only_km2": round(sum(r.get("sentinel1_only_km2") or 0 for r in rows), 1),
            "mud_km2": round(sum(r.get("mud_km2") or 0 for r in rows), 1),
            "status_cases": len(cases), "sites": len(found_sites),
            "followed": _count(cases, "followed"), "by_zone": tally(cases)}


def _count(items, key):
    out = {}
    for it in items:
        out[it[key]] = out.get(it[key], 0) + 1
    return out


def review_template(site):
    return json.dumps({"passes": site["passes"], "community_ids": site["community_ids"],
                       "verdict": " | ".join(VERDICTS), "cause": site["cause"], "reviewer": "", "date": "", "note": ""},
                      ensure_ascii=False)


def default_reviews_path(benchmark_dir):
    return os.path.join(benchmark_dir, "crosscheck_reviews.json")
