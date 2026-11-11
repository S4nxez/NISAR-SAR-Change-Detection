"""The benchmark run: synthetic scenes, the real NISAR record against Sentinel-2 and the river gauge, and the field
checks, all on the method of the current checkout. Writes one result (JSON + Markdown) to the history folder.

The exam definition (processing/benchmark/exam.json) fixes the passes, the reference rules and the synthetic
settings, so two results of the same exam version are comparable: only the method changed between them.
"""
import datetime as dt
import json
import os
import shutil
import subprocess

import numpy as np
import requests

from lifeline import pipeline
from lifeline.analysis.water import connectivity
from lifeline.benchmark import optical, report, synthetic
from lifeline.benchmark.scoring import (
    LINKED,
    add_counts,
    rates,
    ratio,
    spearman,
    status_scores,
    unpack_layers,
    water_scores,
)
from lifeline.config import AREAS_DIR, PROCESSING_DIR, STATUS, log
from lifeline.geometry.area import area_mask, to_px
from lifeline.geometry.geo import fold
from lifeline.output.catalog import hub_target, pass_dir
from lifeline.sources import asf, places

BENCHMARK_DIR = os.path.join(PROCESSING_DIR, "benchmark")
HISTORY_DIR = os.path.join(BENCHMARK_DIR, "history")


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def git_state(cwd=PROCESSING_DIR, run=subprocess.run):
    """(commit, dirty) of the checkout; (None, None) outside git."""
    try:
        commit = run(["git", "rev-parse", "--short", "HEAD"], cwd=cwd, capture_output=True, text=True,
                     check=True).stdout.strip()
        dirty = bool(run(["git", "status", "--porcelain", "--", "src", "areas"], cwd=cwd, capture_output=True,
                         text=True, check=True).stdout.strip())
        return commit, dirty
    except (OSError, subprocess.CalledProcessError):
        return None, None


def frozen_passes(area, exam, cache_dir, search=asf.search):
    """The exam's passes (exam["passes"]) as ASF describes them, stored once in the cache so later runs need no
    search and see the same granules."""
    path = os.path.join(cache_dir, f"asf_passes_{area['id']}.json")
    if os.path.exists(path):
        found = load_json(path)
    else:
        found = search(area)
        for ps in found.values():
            for g in ps["granules"]:
                g["start"] = str(g["start"])
        save_json(path, found)
    missing = sorted(set(exam["passes"]) - set(found))
    if missing:
        raise SystemExit(f"passes of the exam not found at ASF: {missing}")
    return {pid: found[pid] for pid in exam["passes"]}


def run_record(area, passes, cache_dir, run_dir, workers, areas_dir=AREAS_DIR, update=pipeline.update):
    """Process the exam's passes with the current method into run_dir (emptied first) and return the catalog.
    Windows come from the cache; the Earthdata token is only needed for the ones still missing."""
    shutil.rmtree(run_dir, ignore_errors=True)
    with synthetic.environment(MONITOR_CACHE_DIR=cache_dir):
        return update(area, workers=workers, out_root=run_dir, areas_dir=areas_dir, search=lambda a: passes,
                      token=lambda: os.environ.get("EARTHDATA_TOKEN", ""))


def reference_status(area, communities, water, valid, in_mask):
    """Community status computed from a reference water mask with the monitor's own route rule."""
    targets = [to_px(area, *(c.get("access") or (c["lon"], c["lat"]))) for c in communities]
    res = connectivity(water, valid, area["px_m"], hub_target(area), targets, area["widths_m"],
                       area["access_radius_m"], area["safe_width_m"], in_mask)
    return {c["id"]: r for c, r in zip(communities, res, strict=True)}


def optical_section(area, cat, communities, run_dir, cache_dir, rules, post=requests.post, reference=None):
    """Every evaluated pass against the Sentinel-2 reference of exam["optical"] rules."""
    reference = reference or optical.reference_for_pass
    in_mask = area_mask(area)
    ids = [c["id"] for c in communities]
    rows, pooled, status_pooled = [], {"tp": 0, "fp": 0, "fn": 0, "tn": 0}, []
    width_pooled, false_pooled = {}, {}
    for p in sorted(cat["passes"], key=lambda p: p["date"]):
        if not p.get("evaluated"):
            continue
        ref = reference(area, p["date"], in_mask, cache_dir, rules["max_days"], rules["min_clear"], post)
        if ref is None:
            continue
        layers = unpack_layers(os.path.join(pass_dir(area, p["id"], run_dir), "water.npz"))
        common = layers["valid"] & ref["valid"] & in_mask
        w = water_scores(layers["water"], ref["water"], common, area["px_m"])
        st = status_scores(p.get("status") or {}, reference_status(area, communities, ref["water"], ref["valid"],
                                                                   in_mask), ids, area["access_radius_m"])
        pooled = add_counts(pooled, w["counts"])
        status_pooled.append(st)
        for k, v in w["recall_by_width"].items():
            hit = 0 if v["recall"] is None else round(v["recall"] * v["pixels"])
            width_pooled[k] = add_counts(width_pooled.get(k, {}), {"hit": hit, "n": v["pixels"]})
        for k, v in w["false_water"].items():
            bad = 0 if v["rate"] is None else round(v["rate"] * v["pixels"])
            false_pooled[k] = add_counts(false_pooled.get(k, {}), {"bad": bad, "n": v["pixels"]})
        row = {"pass": p["id"], "s2_date": ref["date"], "days_apart": ref["days_apart"],
               "clear_share": ref["clear_share"], "mndwi_threshold": ref["threshold"],
               "common_km2": round(float(common.sum()) * (area["px_m"] / 1000) ** 2, 1), "water": w, "status": st}
        if "vegetated" in layers:
            veg = layers["vegetated"] & common
            row["vegetated"] = {"km2": round(float(veg.sum()) * (area["px_m"] / 1000) ** 2, 2),
                                "share_seen_as_water_by_s2": ratio(int((veg & ref["water"]).sum()), int(veg.sum()))}
        rows.append(row)
        log(f"benchmark: {p['id']} vs Sentinel-2 {ref['date']}: IoU {w['iou']}, status agreement {st['agreement']}")
    n = sum(s["n"] for s in status_pooled)
    summary = {"passes": len(rows), **rates(pooled),
               "recall_by_width": {k: ratio(v["hit"], v["n"]) for k, v in width_pooled.items()},
               "false_water": {k: ratio(v["bad"], v["n"]) for k, v in false_pooled.items()},
               "status_pairs": n,
               "status_agreement": ratio(sum(round((s["agreement"] or 0) * s["n"]) for s in status_pooled), n),
               "status_kappa_mean": (round(float(np.mean([s["kappa"] for s in status_pooled if s["kappa"] is not None])),
                                           4) if any(s["kappa"] is not None for s in status_pooled) else None),
               "false_route": sum(s["false_route"] for s in status_pooled),
               "overconfident": sum(s["overconfident"] for s in status_pooled),
               "false_isolated": sum(s["false_isolated"] for s in status_pooled)}
    return {"rules": rules, "summary": summary, "passes": rows}


def gauge_level(series, date, max_days=1):
    """Gauge level on `date`, else the closest day within max_days, else None."""
    levels = dict(series)
    day = dt.date.fromisoformat(date)
    for k in range(max_days + 1):
        for d in {day - dt.timedelta(days=k), day + dt.timedelta(days=k)}:
            if d.isoformat() in levels:
                return levels[d.isoformat()]
    return None


def gauge_section(area, cat, cache_dir):
    """Rank correlation of the record with the river level: detected water should rise with it (rho > 0) and the
    communities that lost their route should fall with it (rho < 0). The series is kept in the cache so a run
    without the ANA service still scores against the same data."""
    path = os.path.join(cache_dir, f"gauge_{area['id']}.json")
    if cat.get("gauge"):
        save_json(path, cat["gauge"])
    gauge = cat.get("gauge") or (load_json(path) if os.path.exists(path) else None)
    if not gauge:
        return {"available": False}
    rows = []
    for p in sorted(cat["passes"], key=lambda p: p["date"]):
        if not p.get("evaluated"):
            continue
        lost = sum(1 for r in (p.get("status") or {}).values()
                   if r[0] == STATUS["isolated"] and r[2] is not None and r[2] <= area["access_radius_m"])
        rows.append({"pass": p["id"], "level_cm": gauge_level(gauge["series"], p["date"]),
                     "water_km2": p["water_km2"], "lost_route": lost})
    levels = [r["level_cm"] for r in rows]
    return {"available": True, "source": gauge["source"], "passes": rows,
            "water_vs_level": spearman(levels, [r["water_km2"] for r in rows]),
            "lost_route_vs_level": spearman(levels, [r["lost_route"] for r in rows])}


def field_section(cat, communities, truth):
    """Field and report checks (processing/benchmark/ground_truth.json) against the record."""
    by_name = {fold(c["name"]): c for c in communities}
    by_id = {c["id"]: c for c in communities}
    rows = []
    for t in truth.get("checks", []):
        c = by_id.get(t.get("community_id")) or by_name.get(fold(t["community"]))
        row = {"community": t["community"], "expected": t["expected"], "kind": t["kind"], "source": t["source"],
               "found": c is not None, "passes": []}
        if c is not None:
            for p in sorted(cat["passes"], key=lambda p: p["date"]):
                if not p.get("evaluated") or not (t["from"] <= p["date"] <= t["to"]):
                    continue
                code = ((p.get("status") or {}).get(c["id"]) or [STATUS["no_data"]])[0]
                if code == STATUS["no_data"]:
                    continue
                ok = code in LINKED if t["expected"] == "linked" else code == STATUS["isolated"]
                row["passes"].append({"pass": p["id"], "status": code, "correct": ok})
        rows.append(row)
    judged = [x for r in rows for x in r["passes"]]
    by_kind = {}
    for r in rows:
        k = by_kind.setdefault(r["kind"], {"checks": 0, "judged": 0, "correct": 0})
        k["checks"] += 1
        k["judged"] += len(r["passes"])
        k["correct"] += sum(x["correct"] for x in r["passes"])
    return {"checks": rows, "by_kind": by_kind, "correct_share": ratio(sum(x["correct"] for x in judged), len(judged))}


def scorecard(result):
    """The headline numbers of one result, the ones the history index shows."""
    syn, opt = result["synthetic"], result.get("optical", {}).get("summary", {})
    gauge, field = result.get("gauge", {}), result.get("field", {})
    return {
        "synthetic_correct_share": syn["correct_share"],
        "synthetic_dangerous": syn["totals"]["dangerous"],
        "synthetic_conservative": syn["totals"]["conservative"],
        "optical_iou": opt.get("iou"),
        "optical_recall_narrow": (opt.get("recall_by_width") or {}).get("narrow_lt60m"),
        "optical_false_water_shore": (opt.get("false_water") or {}).get("shore"),
        "status_agreement": opt.get("status_agreement"),
        "false_route": opt.get("false_route"),
        "false_isolated": opt.get("false_isolated"),
        "gauge_rho_lost_route": (gauge.get("lost_route_vs_level") or {}).get("rho"),
        "field_correct_share": field.get("correct_share"),
    }


def run(area, label, cache_dir, workers=2, exam_path=None, truth_path=None, history_dir=HISTORY_DIR,
        skip_real=False, now=None):
    """Run the whole exam and write its result to history_dir. Returns (result, json path, markdown path)."""
    exam = load_json(exam_path or os.path.join(BENCHMARK_DIR, "exam.json"))
    truth = load_json(truth_path or os.path.join(BENCHMARK_DIR, "ground_truth.json"))
    commit, dirty = git_state()
    now = now or dt.datetime.now(dt.timezone.utc)
    result = {"exam_version": exam["version"], "label": label, "created_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
              "commit": commit, "dirty": dirty,
              "method": {k: v for k, v in area.items() if k not in ("nx", "ny", "px_m", "bbox", "hub", "river")}}
    log("benchmark: synthetic scenes")
    result["synthetic"] = synthetic.run(area, exam["synthetic"]["looks"], exam["synthetic"]["seeds"],
                                        workdir=cache_dir)
    if not skip_real:
        run_dir = os.path.join(cache_dir, "runs", area["id"])
        log(f"benchmark: real record ({len(exam['passes'])} passes)")
        cat = run_record(area, frozen_passes(area, exam, cache_dir), cache_dir, run_dir, workers)
        communities = places.load_communities(area)
        result["optical"] = optical_section(area, cat, communities, run_dir, cache_dir, exam["optical"])
        result["gauge"] = gauge_section(area, cat, cache_dir)
        result["field"] = field_section(cat, communities, truth)
        result["classes"] = cat.get("community_classes")
    result["scorecard"] = scorecard(result)
    stem = f"{now.strftime('%Y%m%dT%H%M%SZ')}_{label}"
    json_path = os.path.join(history_dir, stem + ".json")
    md_path = os.path.join(history_dir, stem + ".md")
    save_json(json_path, result)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(report.markdown(result))
    report.update_index(history_dir, result, stem)
    return result, json_path, md_path
