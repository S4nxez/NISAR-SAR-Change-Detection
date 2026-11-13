"""
River lifeline monitor.

Tracks, pass by pass, whether riverside communities keep a water connection to their hub
town, using NISAR L2 GCOV radar backscatter. Radar sees water through clouds and smoke,
and L-band reaches water under the forest canopy.

  river-monitor communities [--area tefe]   fetch places from OpenStreetMap
  river-monitor occurrence [--area tefe]    save the JRC water occurrence layer (once)
  river-monitor update [--area tefe] [--workers 2] [--limit N] [--redo]
  river-monitor reevaluate [--area tefe]    recompute status from stored masks
  river-monitor watch [--area tefe] [--hours 6]
  river-monitor benchmark --label NAME [--area tefe] [--workers 2] [--skip-real]
                                            accuracy exam of the current method (needs MONITOR_CACHE_DIR;
                                            see docs/river-monitor-benchmark.md)

(river-monitor is installed with `pip install -e processing`; `python -m lifeline` is the same.)

Data access: NISAR GCOV products from the ASF DAAC. Searching needs no account; reading
needs a NASA Earthdata user token in the EARTHDATA_TOKEN environment variable (on Windows
the user-level variable is also read from the registry, so no restart is needed). Only the
area of interest is read from each remote product with HTTP range requests, never the
whole ~2 GB file.

Method, for every pass (all frames of one track on one day, mosaicked):
  1. HH backscatter below valid_floor_db (swath-edge fill) and within edge_margin_m of the edge of
     the data is no data. The rest is speckle-filtered (speckle_filter: refined Lee, or a box of
     speckle_m) and resampled to a fixed lon/lat grid (~20 m) shared by all passes.
  2. Water = filtered HH below water_db, plus pixels below water_db_weak touching that water.
     Specks under 1 ha are dropped and holes under 2 ha inside water are filled. Water under
     vegetation (vegetated_water: bright HH, high HH - HV, near open water) is its own class and
     never a route.
  3. For every channel width W in widths_m, the water mask is reduced to the pixels at
     least W/2 from the shore; a community is connected at width W when, within
     access_radius_m of it, one of those pixels belongs to the same component as the
     water around the hub. Its bottleneck is the widest W that still connects it.
  4. Sentinel-1 (C band) scenes within sentinel1.max_days are read too. At low water (river gauge at most
     low_water.gauge_max_cm), NISAR water on seasonal ground (JRC occurrence in low_water.seasonal_pct) that
     Sentinel-1 sees as land carries no route: L band reads a drained bed as dark as open water, C band sees the
     mud. A route through a broad seasonal patch no Sentinel-1 scene covers is at most at risk.
  5. Status: connected (bottleneck >= safe_width_m), at_risk (connected, narrower),
     isolated (no water path, or no water within access_radius_m), no_data.

Output (MONITOR_DATA_DIR/<area>/, processing/output/<area>/ by default): catalog.json and,
per pass, radar.webp, water.png, change.png, water.npz and sentinel1.npz. In the stack the folder is the
monitor_data volume and the backend serves it under api/monitor; see docs/river-monitor.md.
"""
import argparse
import re

from lifeline import config, pipeline
from lifeline.geometry.area import load_area

COMMANDS = ("communities", "occurrence", "update", "reevaluate", "watch", "benchmark")


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=COMMANDS)
    ap.add_argument("--area", default="tefe")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--limit", type=int, help="process only the N most recent pending passes")
    ap.add_argument("--redo", action="store_true", help="reprocess passes already in the catalog")
    ap.add_argument("--hours", type=float, default=6.0, help="watch: hours between searches")
    ap.add_argument("--label", help="benchmark: name of the result in the history (letters, digits, - and _)")
    ap.add_argument("--skip-real", action="store_true", help="benchmark: synthetic scenes only (no real passes)")
    a = ap.parse_args(argv)
    if a.command == "benchmark" and not re.fullmatch(r"[A-Za-z0-9_-]+", a.label or ""):
        ap.error("benchmark needs --label made of letters, digits, - and _")
    return a


def benchmark(area, a, environ=None):
    from lifeline.benchmark import exam
    cache = config.cache_dir(environ) if environ is not None else config.cache_dir()
    if not cache:
        raise SystemExit("benchmark needs MONITOR_CACHE_DIR: the exam reads every pass from the local cache.")
    result, json_path, md_path = exam.run(area, a.label, cache, a.workers, skip_real=a.skip_real)
    config.log(f"benchmark written to {md_path}")
    return result


def main(argv=None):
    a = parse_args(argv)
    area = load_area(a.area)
    if a.command == "communities":
        pipeline.communities(area)
    elif a.command == "occurrence":
        pipeline.occurrence(area)
    elif a.command == "update":
        pipeline.update(area, a.workers, a.limit, a.redo)
    elif a.command == "reevaluate":
        pipeline.reevaluate(area)
    elif a.command == "benchmark":
        benchmark(area, a)
    else:
        pipeline.watch(area, a.hours, a.workers)


if __name__ == "__main__":
    main()
