"""The monitor's commands: communities, update, reevaluate and watch."""
import concurrent.futures as cf
import datetime as dt
import os
import time
import traceback

import numpy as np

from lifeline.analysis.radar import read_pass_bands, trim_swath_edge
from lifeline.analysis.water import pass_thresholds, vegetated_water, water_mask
from lifeline.config import AREAS_DIR, OUT_ROOT, keep_backscatter, log
from lifeline.geometry.area import area_mask
from lifeline.output.catalog import (
    catalog_path,
    classify_communities,
    evaluate,
    load_catalog,
    pass_dir,
    refresh_changes,
    save_catalog,
    wide_water_of,
)
from lifeline.output.layers import load_mask, load_vegetated, save_backscatter, save_mask, save_radar, save_water
from lifeline.sources import asf, places
from lifeline.sources.gauge import refresh_gauge
from lifeline.sources.remote import earthdata_token

ENTRY_KEYS = ("id", "date", "time_utc", "track", "direction", "frames", "modes", "beta")


def read_layers(area, ps, token):
    """The bands the area's method needs: HH, plus HV when the area flags water under vegetation."""
    bands = ("HHHH", "HVHV") if area.get("vegetated_water") else ("HHHH",)
    return read_pass_bands(area, ps, token, bands)


def process_pass(area, communities, ps, out_root, token, read=None):
    """Read one pass (with read_layers unless `read` is given; it returns ({band: db} or the HH array, megabytes,
    spacing)), write its layers and return its catalog entry."""
    t0 = time.time()
    bands, read_mb, spacing = (read or read_layers)(area, ps, token)
    if not isinstance(bands, dict):
        bands = {"HHHH": bands}
    inside = area_mask(area)
    db, hv = bands["HHHH"], bands.get("HVHV")
    db[~inside] = np.nan   # outside a circular area: transparent in the images, never water
    trim_swath_edge(db, inside, area.get("edge_margin_m", 0), area["px_m"])
    if hv is not None:
        hv[~np.isfinite(db)] = np.nan
    strong_db, weak_db, threshold = pass_thresholds(area, db)
    water, valid = water_mask(db, strong_db, weak_db)
    wide = wide_water_of(area, water)
    vegetated = vegetated_water(db, hv, water, area.get("vegetated_water"), area["px_m"])
    pdir = pass_dir(area, ps["id"], out_root)
    os.makedirs(pdir, exist_ok=True)
    save_radar(db, os.path.join(pdir, "radar.webp"))
    save_water(water, wide, os.path.join(pdir, "water.png"), vegetated)
    save_mask(water, valid, os.path.join(pdir, "water.npz"), vegetated)
    if keep_backscatter():
        save_backscatter(db, hv, os.path.join(pdir, "backscatter.npz"))
    entry = {k: ps[k] for k in ENTRY_KEYS}
    pix_km2 = (area["px_m"] / 1000.0) ** 2
    entry.update(read_mb=round(read_mb, 1), spacing_m=spacing, files={"radar": "radar.webp", "water": "water.png"},
                 threshold=threshold,
                 vegetated_km2=None if vegetated is None else round(float(vegetated.sum()) * pix_km2, 2))
    evaluate(area, communities, water, valid, wide, entry)
    entry["seconds"] = round(time.time() - t0, 1)
    return entry


def _process_job(job):
    """process_pass in a worker process: (pass id, entry or None, error text or None)."""
    area, communities, ps, out_root, token = job
    try:
        return ps["id"], process_pass(area, communities, ps, out_root, token), None
    except Exception:  # keep the batch running; the pass is retried on the next update
        return ps["id"], None, traceback.format_exc(limit=3)


def pending_passes(found, cat, redo=False, limit=None):
    """Passes to process, oldest first: the ones not in the catalog (all with redo), the last
    `limit` of them when given."""
    done = {p["id"] for p in cat["passes"]}
    todo = sorted((p for pid, p in found.items() if redo or pid not in done), key=lambda p: p["date"])
    return todo[-limit:] if limit else todo


def describe(entry):
    c = entry.get("counts")
    counts = (f", connected {c['connected']} / at risk {c['at_risk']} / isolated {c['isolated']}" if c
              else ", not evaluated (partial coverage)")
    return (f"{entry['id']}: coverage {entry['coverage'] * 100:.0f} %, water {entry['water_km2']} km², "
            f"read {entry['read_mb']} MB in {entry['seconds']} s{counts}")


def put_entry(cat, entry):
    cat["passes"] = [p for p in cat["passes"] if p["id"] != entry["id"]] + [entry]


def update(area, workers=2, limit=None, redo=False, out_root=OUT_ROOT, areas_dir=AREAS_DIR,
           search=asf.search, token=earthdata_token, executor=cf.ProcessPoolExecutor):
    """Search ASF and process every pass not in the catalog yet, then refresh the whole record."""
    communities = places.load_communities(area, areas_dir)
    cat = load_catalog(area, communities, out_root)
    log(f"Searching ASF for NISAR GCOV over {area['name']} ...")
    found = search(area)
    todo = pending_passes(found, cat, redo, limit)
    log(f"{len(found)} passes found, {len(todo)} to process")
    cat["last_search"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if todo:
        tok = token()
        jobs = [(area, communities, ps, out_root, tok) for ps in todo]
        with executor(max_workers=max(1, workers)) as ex:
            for pid, entry, err in ex.map(_process_job, jobs):
                if err:
                    log(f"FAILED {pid}:\n{err}")
                    continue
                put_entry(cat, entry)
                log(describe(entry))
                # the page may read the catalog meanwhile: keep its counts and classes consistent
                classify_communities(area, cat)
                save_catalog(area, cat, out_root)
    refresh_changes(area, cat, out_root)
    classify_communities(area, cat)
    refresh_gauge(area, cat)
    save_catalog(area, cat, out_root)
    log(f"Catalog: {catalog_path(area, out_root)} ({len(cat['passes'])} passes); "
        f"communities {cat['community_classes']}")
    return cat


def reevaluate(area, out_root=OUT_ROOT, areas_dir=AREAS_DIR):
    """Recompute water layers and community status from the stored masks (no download)."""
    communities = places.load_communities(area, areas_dir)
    cat = load_catalog(area, communities, out_root)
    for entry in cat["passes"]:
        pdir = pass_dir(area, entry["id"], out_root)
        path = os.path.join(pdir, "water.npz")
        if not os.path.exists(path):
            continue
        water, valid = load_mask(path)
        wide = wide_water_of(area, water)
        save_water(water, wide, os.path.join(pdir, "water.png"), load_vegetated(path))
        evaluate(area, communities, water, valid, wide, entry)
        log(f"{entry['id']}: re-evaluated")
    refresh_changes(area, cat, out_root)
    classify_communities(area, cat)
    save_catalog(area, cat, out_root)
    log(f"Catalog: {len(cat['passes'])} passes; communities {cat['community_classes']}")
    return cat


def communities(area, areas_dir=AREAS_DIR, query=places.overpass):
    """Fetch the area's places and landings from OpenStreetMap and write the communities file."""
    found = places.fetch_places(area, query)
    landings = places.fetch_landings(area, query)
    kept = places.assign_access(found, landings, area.get("access_snap_m", {}))
    collection = places.communities_collection(area, kept)
    places.save_communities(area, collection, areas_dir)
    moved = sum("access" in f["properties"] for f in collection["features"])
    log(f"{len(collection['features'])} places saved to {places.communities_path(area, areas_dir)} "
        f"({len(landings)} landings; {moved} places use a landing or port as their water access)")
    return collection


def watch(area, hours=6.0, workers=2, run=update, sleep=time.sleep, rounds=None):
    """Run update every `hours` (forever unless `rounds` is given); a failed round is logged."""
    done = 0
    while rounds is None or done < rounds:
        try:
            run(area, workers)
        except Exception:
            log("update failed:\n" + traceback.format_exc(limit=3))
        done += 1
        log(f"next search in {hours} h")
        sleep(hours * 3600)
