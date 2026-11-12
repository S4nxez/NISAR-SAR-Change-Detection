"""Markdown of a benchmark result and the history index (processing/benchmark/history/README.md)."""
import glob
import json
import os

from lifeline.benchmark.causes import FAMILIES, FAMILY, MEANING
from lifeline.config import STATUS_NAME

INDEX_COLUMNS = [
    ("synthetic_correct_share", "Synthetic correct", "share of lane results that are right (higher is better)"),
    ("synthetic_dangerous", "Synthetic dangerous", "lane results showing a route that does not exist or is too narrow"),
    ("optical_iou", "Water IoU vs reference",
     "agreement of the water mask with the reference: Sentinel-2 in exam 1, the consensus of the references from "
     "exam 2 (higher is better)"),
    ("optical_recall_narrow", "Narrow recall", "share of reference channels under 60 m mapped as water"),
    ("optical_false_water_shore", "False water at shore", "share of shoreline land mapped as water (lower is better)"),
    ("status_agreement", "Status agreement", "community status equal to the one from the reference water"),
    ("false_route", "False routes",
     "community shown with a route the reference water does not have (lower is better; not yet checked by a person)"),
    ("false_isolated", "False isolated", "community shown isolated while the reference water links it"),
    ("gauge_rho_lost_route", "Gauge rho", "rank correlation of lost routes with the river level (more negative is better)"),
    ("field_correct_share", "Field checks", "share of field and report checks the record gets right"),
    ("status_undecided", "Undecided", "community-pass pairs the references cannot decide (exam 2), left unscored"),
    ("review_needed", "To review", "disagreements a person has to check (exam 2; see Manual review in the report)"),
    ("false_route_confirmed", "Confirmed false routes",
     "false routes a person confirmed in processing/benchmark/reviews.json (exam 2)"),
]


def km2(px, px_m=20.0):
    return round(px * (px_m / 1000) ** 2, 2)


def status_name(code):
    return STATUS_NAME.get(code, str(code))


KIND_TEXT = {"false_route": "route the reference does not have", "overconfident": "route wider than the reference's",
             "false_isolated": "isolated while the reference links it",
             "underconfident": "route narrower than the reference's"}


def link_list(links):
    names = {"sentinel2": "Sentinel-2", "sentinel1": "Sentinel-1", "openstreetmap": "map"}
    return " · ".join(f"[{names.get(k, k)}]({v})" for k, v in links.items())


def site_block(i, s):
    """One site of the manual review: where, what, which communities and passes, links and a review to paste."""
    kinds = "; ".join(KIND_TEXT.get(k, k) for k in s["kinds"])
    near = f"{s['distance_km']} km from {s['near']}" if s["distance_km"] else f"at {s['near']}"
    lines = [f"### {i}. Near {s['near']}: {kinds}", "",
             f"- Where: {near} ({s['lon']}, {s['lat']}); the links open the map on that point.",
             f"- Probable cause: `{s['cause']}` ({FAMILY.get(s['cause'], s['family'])}): {MEANING.get(s['cause'], '')}",
             f"- Communities: {', '.join(s['communities'])}",
             f"- Passes ({s['cases']} cases): {', '.join(s['passes'])}"]
    lines += [f"  - {p}: {link_list(links)}" for p, links in s["links"].items()]
    if s.get("verdicts"):
        lines.append(f"- Reviewed: {', '.join(s['verdicts'])}")
    review = {"passes": s["passes"], "community_ids": s["community_ids"], "verdict": "nisar | reference | undecidable",
              "cause": s["cause"], "reviewer": "", "date": "", "note": ""}
    lines += ["- Verdict to add to `processing/benchmark/reviews.json`:", "", "```json",
              json.dumps(review, ensure_ascii=False), "```", ""]
    return lines


def reference_markdown(ref):
    """Sections of an exam-2 result: the consensus, the disagreements with their causes and the manual review."""
    sm = ref["summary"]
    rules = ref["rules"]
    px_m = sm.get("px_m", 20.0)
    refs = ", ".join(f"{k} (within {v['max_days']} days)" for k, v in rules["references"].items()) or "none"
    lines = ["## Real passes against the reference consensus", "",
             f"Anchor: the clearest Sentinel-2 L2A date within {rules['optical']['max_days']} days of the pass, at "
             f"least {rules['optical']['min_clear']:.0%} of the area clear ({sm['passes']} passes). Other references: "
             f"{refs}. A pixel is reference water or land when the sources that can see it agree, and disputed "
             "(not scored) when they do not; optical \"not water\" under wetlands and mangroves is not trusted.", "",
             table(["IoU", "F1", "Precision", "Recall", "Recall < 60 m", "Recall 60-200 m", "Recall >= 200 m",
                    "False water shore", "False water far", "IoU vs Sentinel-2 only"],
                   [(sm["iou"], sm["f1"], sm["precision"], sm["recall"], sm["recall_by_width"].get("narrow_lt60m"),
                     sm["recall_by_width"].get("medium_60_200m"), sm["recall_by_width"].get("wide_ge200m"),
                     sm["false_water"].get("shore"), sm["false_water"].get("far"), sm["s2_only"]["iou"])]), "",
             "Community status against the status the monitor's own route rule gives on the consensus water "
             f"({sm['status_pairs']} decided community-pass pairs; inland places left out). Undecided: the "
             "status changes depending on whether the disputed pixels are water or land.", "",
             table(["Agreement", "Mean kappa", "False routes", "Overconfident", "False isolated", "Undecided"],
                   [(sm["status_agreement"], sm["status_kappa_mean"], sm["false_route"], sm["overconfident"],
                     sm["false_isolated"], sm["undecided"])]), "",
             "How often each source agrees with the consensus where it votes (a source that often disagrees is less "
             "trustworthy over this area):", "",
             table(["Source", "Family", "Passes", "Votes (km²)", "Agrees"],
                   [(k, v["family"], v["passes"], km2(v["voted_px"], px_m), v["agrees_share"])
                    for k, v in sm["sources"].items()]), "",
             table(["Pass", "Sentinel-2", "DSWx-HLS", "DSWx-S1", "Disputed km²", "Both families", "Level change cm",
                    "IoU", "Agreement", "False routes", "Undecided", "Cases"],
                   [(r["pass"], r["s2_date"], (r["sources"].get("dswx_hls") or {}).get("date"),
                     (r["sources"].get("dswx_s1") or {}).get("date"), r["consensus"]["disputed_km2"],
                     r["consensus"]["two_families_share"], r["level_change_cm"], r["water"]["iou"],
                     r["status"]["agreement"], r["status"]["false_route"], len(r["undecided"]), r["cases"])
                    for r in ref["passes"]]), ""]
    pc = sm["pixel_causes"]
    names = sorted(set(pc["commission"]) | set(pc["omission"]),
                   key=lambda n: -(pc["commission"].get(n, 0) + pc["omission"].get(n, 0)))
    lines += ["## Disagreements and probable causes", "",
              "Every pixel where the water mask and the consensus disagree gets the first cause whose rule it meets "
              "(commission: NISAR water on reference land; omission: reference water NISAR misses). The rules are "
              "evidence, not proof.", "",
              table(["Cause", "Family", "Commission km²", "Omission km²", "Meaning"],
                    [(n, FAMILY[n], km2(pc["commission"].get(n, 0), px_m), km2(pc["omission"].get(n, 0), px_m), MEANING[n])
                     for n in names]), "",
              table(["Family", "Commission km²", "Omission km²", "Meaning"],
                    [(f, km2(sm["pixel_families"]["commission"].get(f, 0), px_m),
                      km2(sm["pixel_families"]["omission"].get(f, 0), px_m), m) for f, m in FAMILIES.items()]), ""]
    cases = ref["cases"]
    if cases:
        lines += ["Cases: communities whose status differs from the decided reference. The culprit pixels are the "
                  "fewest disputed pixels a route crosses between the hub and the community.", "",
                  table(["Pass", "Community", "Kind", "NISAR", "Reference", "Cause", "Family", "Culprit px",
                         "Lon, lat", "Review", "Verdict"],
                        [(c["pass"], c["community"], c["kind"], status_name(c["status"]),
                          status_name(c["reference_status"]), c["cause"], c["family"], c["culprit_px"],
                          f"{c['lon']}, {c['lat']}", "yes" if c["review"] else "no",
                          (c.get("reviewed") or {}).get("verdict")) for c in cases]), ""]
        rv = sm["reviews"]
        lines += [table(["Kind", "Cases", "Confirmed", "Rejected", "Undecidable", "Pending"],
                        [(k, v["cases"], v["confirmed"], v["rejected"], v["undecidable"], v["pending"])
                         for k, v in rv.items()]), ""]
    todo = [s for s in ref.get("sites", []) if s["review"]]
    n_cases = sum(1 for c in cases if c["review"])
    lines += ["## Manual review", "",
              f"{n_cases} cases need a person (every false route, the dangerous error, and every case whose cause says "
              f"the reference may be wrong, points at our processing or is unexplained). They come from {len(todo)} "
              "places, each named after the nearest community. How to check a place: docs/river-monitor-benchmark.md, "
              "\"Manual review\"; one verdict covers every community and pass of the place.", ""]
    for i, s in enumerate(todo, 1):
        lines += site_block(i, s)
    rest = [s for s in ref.get("sites", []) if not s["review"]]
    if rest:
        lines += ["Other places with disagreements (cause known, no review needed):", "",
                  table(["Near", "Kinds", "Cause", "Communities", "Passes"],
                        [(s["near"], ", ".join(s["kinds"]), s["cause"], ", ".join(s["communities"]),
                          ", ".join(s["passes"])) for s in rest]), ""]
    return lines



def fmt(v):
    if v is None:
        return "–"
    if isinstance(v, float):
        return f"{v:.3f}"
    return str(v)


def table(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    out += ["| " + " | ".join(fmt(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def markdown(result):
    """Human-readable report of one result."""
    s = result["scorecard"]
    lines = [f"# Benchmark: {result['label']}", "",
             f"Exam version {result['exam_version']} · {result['created_utc']} · commit `{result['commit']}`"
             + (" (uncommitted changes)" if result.get("dirty") else ""), "",
             "## Scorecard", "", table(["Metric", "Value", "Meaning"],
                                       [(name, s.get(key), meaning) for key, name, meaning in INDEX_COLUMNS]), ""]
    syn = result["synthetic"]
    lines += ["## Synthetic scenes", "",
              f"{len(syn['seeds'])} speckle draws with {syn['looks']} looks. Expected status per lane and how often "
              "each grade came out.", "",
              table(["Lane", "Expected", "Correct", "Conservative", "Dangerous", "No data"],
                    [(name, lane["expected"], *(lane["grades"].get(g, 0) for g in
                                                ("correct", "conservative", "dangerous", "no_data")))
                     for name, lane in syn["lanes"].items()]), "",
              table(["Surface", "HH / HV (dB)", "Mapped as water", "Mapped as vegetated water"],
                    [(name, "{:g} / {:g}".format(*syn["surfaces_db"][name]), v.get("as_water"),
                      v.get("as_vegetated_water")) for name, v in syn["surfaces"].items()]), ""]
    if result.get("reference"):
        lines += reference_markdown(result["reference"])
    opt = result.get("optical")
    if opt:
        sm = opt["summary"]
        lines += ["## Real passes against Sentinel-2", "",
                  f"Reference: MNDWI of the clearest Sentinel-2 L2A date within {opt['rules']['max_days']} days of "
                  f"the pass, at least {opt['rules']['min_clear']:.0%} of the area clear. {sm['passes']} passes "
                  "had one. Pixel counts pooled over all of them.", "",
                  table(["IoU", "F1", "Precision", "Recall", "Recall < 60 m", "Recall 60-200 m", "Recall >= 200 m",
                         "False water shore", "False water far"],
                        [(sm["iou"], sm["f1"], sm["precision"], sm["recall"],
                          sm["recall_by_width"].get("narrow_lt60m"), sm["recall_by_width"].get("medium_60_200m"),
                          sm["recall_by_width"].get("wide_ge200m"), sm["false_water"].get("shore"),
                          sm["false_water"].get("far"))]), "",
                  "Community status against the status the monitor's own route rule gives on the Sentinel-2 water "
                  f"({sm['status_pairs']} community-pass pairs; inland places left out):", "",
                  table(["Agreement", "Mean kappa", "False routes", "Overconfident", "False isolated"],
                        [(sm["status_agreement"], sm["status_kappa_mean"], sm["false_route"], sm["overconfident"],
                          sm["false_isolated"])]), "",
                  table(["Pass", "Sentinel-2", "Days", "Clear", "IoU", "Recall < 60 m", "Agreement", "False routes",
                         "False isolated"],
                        [(r["pass"], r["s2_date"], r["days_apart"], r["clear_share"], r["water"]["iou"],
                          r["water"]["recall_by_width"]["narrow_lt60m"]["recall"], r["status"]["agreement"],
                          r["status"]["false_route"], r["status"]["false_isolated"]) for r in opt["passes"]]), ""]
    gauge = result.get("gauge")
    if gauge and gauge.get("available"):
        lines += ["## River gauge", "", f"{gauge['source']}.", "",
                  table(["Correlation", "Spearman rho", "Passes", "Expected sign"],
                        [("water area vs level", gauge["water_vs_level"]["rho"], gauge["water_vs_level"]["n"], "+"),
                         ("lost routes vs level", gauge["lost_route_vs_level"]["rho"],
                          gauge["lost_route_vs_level"]["n"], "-")]), ""]
    field = result.get("field")
    if field:
        lines += ["## Field and report checks", "",
                  table(["Community", "Expected", "Kind", "Found", "Passes judged", "Correct", "Source"],
                        [(r["community"], r["expected"], r["kind"], r["found"], len(r["passes"]),
                          sum(x["correct"] for x in r["passes"]), r["source"]) for r in field["checks"]]), ""]
    if result.get("classes"):
        lines += ["## Community classes", "", table(list(result["classes"]), [list(result["classes"].values())]), ""]
    return "\n".join(lines)


def update_index(history_dir, *_):
    """Rewrite history_dir/README.md: one row per result, oldest first."""
    rows = []
    for path in sorted(glob.glob(os.path.join(history_dir, "*.json"))):
        with open(path, encoding="utf-8") as f:
            r = json.load(f)
        stem = os.path.splitext(os.path.basename(path))[0]
        rows.append((f"[{r['label']}]({stem}.md)", r["created_utc"][:10], r["exam_version"],
                     f"`{r['commit']}`" + ("*" if r.get("dirty") else ""),
                     *(r["scorecard"].get(key) for key, _, _ in INDEX_COLUMNS)))
    head = ["Result", "Date", "Exam", "Commit"] + [name for _, name, _ in INDEX_COLUMNS]
    text = ["# Benchmark history", "",
            "One row per run of `river-monitor benchmark` (see docs/river-monitor-benchmark.md). Compare rows of the "
            "same exam version only. `*` after a commit: the run had uncommitted changes.", "",
            table(head, rows), "", "Columns:", ""]
    text += [f"- **{name}**: {meaning}." for _, name, meaning in INDEX_COLUMNS]
    with open(os.path.join(history_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(text) + "\n")
