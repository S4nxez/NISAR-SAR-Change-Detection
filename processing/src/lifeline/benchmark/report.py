"""Markdown of a benchmark result and the history index (processing/benchmark/history/README.md)."""
import glob
import json
import os

INDEX_COLUMNS = [
    ("synthetic_correct_share", "Synthetic correct", "share of lane results that are right (higher is better)"),
    ("synthetic_dangerous", "Synthetic dangerous", "lane results showing a route that does not exist or is too narrow"),
    ("optical_iou", "Water IoU vs S2", "agreement of the water mask with Sentinel-2 (higher is better)"),
    ("optical_recall_narrow", "Narrow recall", "share of Sentinel-2 channels under 60 m mapped as water"),
    ("optical_false_water_shore", "False water at shore", "share of shoreline land mapped as water (lower is better)"),
    ("status_agreement", "Status agreement", "community status equal to the one from Sentinel-2 water"),
    ("false_route", "False routes", "community shown with a route Sentinel-2 water does not have (lower is better)"),
    ("false_isolated", "False isolated", "community shown isolated while Sentinel-2 water links it"),
    ("gauge_rho_lost_route", "Gauge rho", "rank correlation of lost routes with the river level (more negative is better)"),
    ("field_correct_share", "Field checks", "share of field and report checks the record gets right"),
]


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
