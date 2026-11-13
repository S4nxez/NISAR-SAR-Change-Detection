"""Verdicts of people who looked at a disagreement (processing/benchmark/reviews.json).

Each review names a pass and a community ("pass", "community_id"), or a whole site of the report ("passes",
"community_ids": every pair of them), and says who was right:
  "nisar"        the method was right, the reference wrong (the case is not an error of the method)
  "reference"    the reference was right (a confirmed error of the method)
  "undecidable"  the images do not tell
A review may also correct the cause. The exam attaches every review to its case and counts confirmed and rejected
errors, so the record of what went wrong grows with every exam.
"""
import json
import os

from lifeline.benchmark.causes import FAMILY

VERDICTS = ("nisar", "reference", "undecidable")


def load(path, verdicts=VERDICTS):
    """The reviews of the file (missing file: none). Raises ValueError on a verdict not in `verdicts`."""
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        reviews = json.load(f).get("reviews", [])
    for r in reviews:
        if not pairs(r):
            raise ValueError(f"review {r}: give pass and community_id, or passes and community_ids")
        if r.get("verdict") not in verdicts:
            raise ValueError(f"review of {r.get('pass')} / {r.get('community_id')}: verdict must be one of "
                             f"{verdicts}, not {r.get('verdict')!r}")
    return reviews


def pairs(review):
    """The (pass, community id) pairs a review covers."""
    passes = review.get("passes") or ([review["pass"]] if review.get("pass") else [])
    ids = review.get("community_ids") or ([review["community_id"]] if review.get("community_id") else [])
    return [(p, c) for p in passes for c in ids]


def attach(pass_id, cases, reviews):
    """Put the review of each case (same pass and community) on it, as `reviewed`; a review's cause wins. A later
    review of the same pair replaces an earlier one."""
    index = {pair: r for r in reviews for pair in pairs(r)}
    for c in cases:
        r = index.get((pass_id, c["community_id"]))
        if r is None:
            continue
        c["reviewed"] = {k: r.get(k) for k in ("verdict", "cause", "reviewer", "date", "note")}
        if r.get("cause"):
            c["cause_found"], c["cause"] = c["cause"], r["cause"]
            c["family"] = FAMILY.get(r["cause"], c["family"])
        c["review"] = False
    return cases


def summary(cases):
    """Counts per kind: cases, reviewed, confirmed (reference right), rejected (NISAR right), undecidable, pending."""
    out = {}
    for c in cases:
        k = out.setdefault(c["kind"], {"cases": 0, "confirmed": 0, "rejected": 0, "undecidable": 0, "pending": 0})
        k["cases"] += 1
        v = (c.get("reviewed") or {}).get("verdict")
        k[{"reference": "confirmed", "nisar": "rejected", "undecidable": "undecidable"}.get(v, "pending")] += 1
    return out
