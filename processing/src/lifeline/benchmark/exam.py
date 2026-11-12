"""The benchmark run: synthetic scenes, the real NISAR record against Sentinel-2 and the river gauge, and the field
checks, all on the method of the current checkout. Writes one result (JSON + Markdown) to the history folder.

The exam definition (processing/benchmark/exam.json) fixes the passes, the reference rules and the synthetic
settings, so two results of the same exam version are comparable: only the method changed between them.

Exam version 1 scores against Sentinel-2 alone (`optical_section`). From version 2 (`reference_section`) the
reference is the consensus of Sentinel-2, OPERA DSWx-HLS and OPERA DSWx-S1, each trusted only where it can see
(benchmark.consensus); every disagreement gets a probable cause, the cases a person has to check are listed with
links (benchmark.causes), and the verdicts of those checks (processing/benchmark/reviews.json) are counted.
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
from lifeline.benchmark import causes, consensus, opera, optical, report, reviews, static_layers, synthetic
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
from lifeline.output.layers import load_backscatter
from lifeline.geometry.area import area_mask, to_px
from lifeline.geometry.geo import fold
from lifeline.output.catalog import hub_target, pass_dir
from lifeline.sources import asf, places
from lifeline.sources.remote import earthdata_token

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
    # the backscatter of every pass is kept to explain the disagreements (benchmark.causes)
    with synthetic.environment(MONITOR_CACHE_DIR=cache_dir, MONITOR_KEEP_BACKSCATTER="1"):
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


def targets_of(area, communities):
    return [to_px(area, *(c.get("access") or (c["lon"], c["lat"]))) for c in communities]


def optional_token(token=earthdata_token):
    """The Earthdata token, or None: without it the OPERA files not in the cache yet are skipped, not the exam."""
    try:
        return token()
    except SystemExit:
        return None


def pass_sources(area, date, in_mask, cache_dir, refs, token, get, opera_ref=opera.reference_for_pass):
    """{product: reference or None} of the OPERA products of exam["references"] for one pass. A product that cannot
    be read (network, token) is None for this run and the reason is logged."""
    out = {}
    for product, cfg in refs.items():
        if product not in opera.PRODUCTS:
            continue
        try:
            out[product] = opera_ref(product, area, date, in_mask, cache_dir, cfg["max_days"], token, get)
        except (requests.RequestException, PermissionError, OSError) as e:
            log(f"benchmark: {product} skipped for {date}: {e}")
            out[product] = None
    return out


def source_votes(s2, refs, statics):
    """Votes of every reference of a pass (benchmark.consensus), each with its blind spots removed."""
    blind = None if statics is None else static_layers.optical_blind(statics["worldcover"])
    out = [consensus.votes("sentinel2", "optical", s2["water"], s2["valid"] & ~s2["water"], blind)]
    for product, ref in refs.items():
        if ref is not None:
            optical_family = opera.PRODUCTS[product]["family"] == "optical"
            out.append(consensus.votes(product, opera.PRODUCTS[product]["family"], ref["water"], ref["land"],
                                       blind if optical_family else None))
    return out


def level_change_cm(gauge, date_a, date_b):
    """River level on date_a minus on date_b (cm), None when either is unknown."""
    if not gauge:
        return None
    a, b = gauge_level(gauge["series"], date_a), gauge_level(gauge["series"], date_b)
    return None if a is None or b is None else round(a - b, 1)


def pass_thresholds_of(area, p):
    """(strong, weak) water thresholds the pass used (catalog entry), else the area's."""
    th = p.get("threshold") or {}
    return th.get("strong_db", area["water_db"]), th.get("weak_db", area.get("water_db_weak"))


def _count(items, key):
    out = {}
    for it in items:
        out[it[key]] = out.get(it[key], 0) + 1
    return out


def _pool(dst, counts):
    for k, v in counts.items():
        dst[k] = dst.get(k, 0) + v
    return dst


def reference_section(area, cat, communities, run_dir, cache_dir, exam, gauge=None, statics=None, review_list=(),
                      token=None, post=requests.post, get=requests.get, reference=None, opera_ref=None):
    """Every evaluated pass against the consensus of the references of exam["references"] (exam version 2)."""
    reference = reference or optical.reference_for_pass
    opera_ref = opera_ref or opera.reference_for_pass
    rules, crules = exam["optical"], exam["causes"]
    in_mask = area_mask(area)
    ids = [c["id"] for c in communities]
    targets, hub = targets_of(area, communities), hub_target(area)
    px = area["px_m"]
    km2 = (px / 1000) ** 2
    pooled, pooled_s2 = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}, {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    width_pooled, false_pooled, source_pooled = {}, {}, {}
    cause_pooled = {"commission": {}, "omission": {}}
    rows, all_cases, status_pooled, undecided_total = [], [], [], 0
    for p in sorted(cat["passes"], key=lambda p: p["date"]):
        if not p.get("evaluated"):
            continue
        s2 = reference(area, p["date"], in_mask, cache_dir, rules["max_days"], rules["min_clear"], post)
        if s2 is None:
            continue
        refs = pass_sources(area, p["date"], in_mask, cache_dir, exam.get("references", {}), token, get, opera_ref)
        votes = source_votes(s2, refs, statics)
        cons = consensus.combine(votes, in_mask)
        pdir = pass_dir(area, p["id"], run_dir)
        layers = unpack_layers(os.path.join(pdir, "water.npz"))
        nisar, nvalid = layers["water"], layers["valid"]
        hh, _ = load_backscatter(os.path.join(pdir, "backscatter.npz"))
        common = nvalid & (cons["water"] | cons["land"]) & in_mask
        w = water_scores(nisar, cons["water"], common, px)
        w_s2 = water_scores(nisar, s2["water"], nvalid & s2["valid"] & in_mask, px)

        def status_of(water, known):
            return reference_status(area, communities, water, known, in_mask)
        decided, _, _ = consensus.status_bounds(status_of, cons)
        ref_st = {cid: r for cid, r in decided.items() if r is not None}
        pred = p.get("status") or {}
        undecided = [cid for cid, r in decided.items()
                     if r is None and pred.get(cid) and pred[cid][0] != STATUS["no_data"]]
        st = status_scores(pred, ref_st, ids, area["access_radius_m"])
        strong, weak = pass_thresholds_of(area, p)
        s1 = refs.get("dswx_s1")
        ctx = {"ref_water": cons["water"], "ref_known": cons["known"], "nisar_valid": nvalid, "in_area": in_mask,
               "hh": hh, "strong_db": strong, "weak_db": weak, "cloudy": s2.get("cloudy"),
               "occurrence": None if statics is None else statics["occurrence"],
               "worldcover": None if statics is None else statics["worldcover"],
               "vegetated": layers.get("vegetated"), "s1_vegetated": None if s1 is None else s1["vegetated"],
               "level_change_cm": level_change_cm(gauge, p["date"], s2["date"])}
        cond = causes.conditions(ctx, crules, px)
        pix = {kind: causes.cause_counts(causes.pixel_causes(kind, mask, cond)) for kind, mask in
               (("commission", nisar & cons["land"] & common), ("omission", cons["water"] & ~nisar & common))}
        found = causes.cases(area, communities, pred, ref_st, nisar, cons["water"], cond, targets, hub, s2["date"],
                             None if s1 is None else s1["date"], crules["max_bridge_px"])
        reviews.attach(p["id"], found, review_list)
        for c in found:
            c["pass"] = p["id"]
        all_cases += found
        undecided_total += len(undecided)
        agree = consensus.agreement_by_source(votes, cons)
        for name, a in agree.items():
            sp = source_pooled.setdefault(name, {"family": a["family"], "passes": 0, "voted_px": 0, "agree_px": 0})
            sp["passes"] += 1
            sp["voted_px"] += a["voted_px"]
            sp["agree_px"] += round((a["agrees_share"] or 0) * a["voted_px"])
        pooled = add_counts(pooled, w["counts"])
        pooled_s2 = add_counts(pooled_s2, w_s2["counts"])
        status_pooled.append(st)
        for k, v in w["recall_by_width"].items():
            hit = 0 if v["recall"] is None else round(v["recall"] * v["pixels"])
            width_pooled[k] = add_counts(width_pooled.get(k, {}), {"hit": hit, "n": v["pixels"]})
        for k, v in w["false_water"].items():
            bad = 0 if v["rate"] is None else round(v["rate"] * v["pixels"])
            false_pooled[k] = add_counts(false_pooled.get(k, {}), {"bad": bad, "n": v["pixels"]})
        for kind, counts in pix.items():
            _pool(cause_pooled[kind], counts)
        rows.append({
            "pass": p["id"], "s2_date": s2["date"], "days_apart": s2["days_apart"], "clear_share": s2["clear_share"],
            "sources": {name: (None if r is None else {"date": r["date"], "days_apart": r["days_apart"],
                                                       "coverage": r["coverage"]}) for name, r in refs.items()},
            "source_agreement": agree,
            "consensus": {"known_km2": round(float(cons["known"].sum()) * km2, 1),
                          "disputed_km2": round(float(cons["disputed"].sum()) * km2, 3),
                          "two_families_share": ratio(int((cons["families"] >= 2).sum()),
                                                      int((cons["water"] | cons["land"]).sum()))},
            "level_change_cm": ctx["level_change_cm"], "backscatter": hh is not None,
            "water": w, "water_s2_only": {k: w_s2[k] for k in ("iou", "precision", "recall")}, "status": st,
            "undecided": undecided, "pixel_causes": pix, "cases": len(found)})
        log(f"benchmark: {p['id']} vs consensus (S2 {s2['date']}, "
            f"{', '.join(k for k, r in refs.items() if r) or 'no OPERA'}): IoU {w['iou']}, "
            f"status agreement {st['agreement']}, {len(found)} cases, {len(undecided)} undecided")
    n = sum(s["n"] for s in status_pooled)
    kappas = [s["kappa"] for s in status_pooled if s["kappa"] is not None]
    summary = {"passes": len(rows), "px_m": px, **rates(pooled), "s2_only": rates(pooled_s2),
               "recall_by_width": {k: ratio(v["hit"], v["n"]) for k, v in width_pooled.items()},
               "false_water": {k: ratio(v["bad"], v["n"]) for k, v in false_pooled.items()},
               "status_pairs": n,
               "status_agreement": ratio(sum(round((s["agreement"] or 0) * s["n"]) for s in status_pooled), n),
               "status_kappa_mean": round(float(np.mean(kappas)), 4) if kappas else None,
               "false_route": sum(s["false_route"] for s in status_pooled),
               "overconfident": sum(s["overconfident"] for s in status_pooled),
               "false_isolated": sum(s["false_isolated"] for s in status_pooled),
               "undecided": undecided_total,
               "sources": {k: {**v, "agrees_share": ratio(v["agree_px"], v["voted_px"])}
                           for k, v in source_pooled.items()},
               "pixel_causes": cause_pooled,
               "pixel_families": {k: causes.by_family(v) for k, v in cause_pooled.items()},
               "case_causes": _count(all_cases, "cause"), "case_families": _count(all_cases, "family"),
               "reviews": reviews.summary(all_cases),
               "review_needed": sum(1 for c in all_cases if c["review"])}
    return {"rules": {"optical": rules, "references": exam.get("references", {}), "causes": crules},
            "summary": summary, "passes": rows, "cases": all_cases}


def load_gauge(area, cat, cache_dir):
    """The gauge series of the catalog (saved to the cache), else the cached one, else None."""
    path = os.path.join(cache_dir, f"gauge_{area['id']}.json")
    if cat.get("gauge"):
        save_json(path, cat["gauge"])
    return cat.get("gauge") or (load_json(path) if os.path.exists(path) else None)


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
    gauge = load_gauge(area, cat, cache_dir)
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
    syn = result["synthetic"]
    opt = (result.get("reference") or result.get("optical") or {}).get("summary", {})
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
        "status_undecided": opt.get("undecided"),
        "review_needed": opt.get("review_needed"),
        "false_route_confirmed": ((opt.get("reviews") or {}).get("false_route") or {}).get("confirmed"),
    }


def run_reference(area, cat, communities, run_dir, cache_dir, exam, reviews_path=None, token=earthdata_token,
                  load_statics=static_layers.load):
    """reference_section with its inputs: static maps (skipped if they cannot be read), the gauge, the reviews and
    the Earthdata token (None: OPERA files not cached yet are skipped)."""
    statics = None
    try:
        statics = load_statics(area, cache_dir)
    except Exception as e:   # rasterio and GDAL raise their own error types: run on without the static maps
        log(f"benchmark: static maps skipped: {e}")
    tok = optional_token(token)
    if tok is None:
        log("benchmark: no EARTHDATA_TOKEN: OPERA files missing from the cache are skipped")
    return reference_section(area, cat, communities, run_dir, cache_dir, exam, load_gauge(area, cat, cache_dir),
                             statics, reviews.load(reviews_path or os.path.join(BENCHMARK_DIR, "reviews.json")), tok)


def run(area, label, cache_dir, workers=2, exam_path=None, truth_path=None, history_dir=HISTORY_DIR,
        skip_real=False, now=None, reviews_path=None, token=earthdata_token):
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
        if "references" in exam:
            result["reference"] = run_reference(area, cat, communities, run_dir, cache_dir, exam, reviews_path, token)
        else:
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
