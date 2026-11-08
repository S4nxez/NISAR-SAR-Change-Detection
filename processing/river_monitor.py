"""
River lifeline monitor.

Tracks, pass by pass, whether riverside communities keep a water connection to their hub
town, using NISAR L2 GCOV radar backscatter. Radar sees water through clouds and smoke,
and L-band reaches water under the forest canopy.

  python processing/river_monitor.py communities [--area tefe]   fetch places from OpenStreetMap
  python processing/river_monitor.py update [--area tefe] [--workers 2] [--limit N] [--redo]
  python processing/river_monitor.py reevaluate [--area tefe]   recompute status from stored masks
  python processing/river_monitor.py watch [--area tefe] [--hours 6]

Data access: NISAR GCOV products from the ASF DAAC. Searching needs no account; reading
needs a NASA Earthdata user token in the EARTHDATA_TOKEN environment variable (on Windows
the user-level variable is also read from the registry, so no restart is needed). Only the
area of interest is read from each remote product with HTTP range requests, never the
whole ~2 GB file.

Method, for every pass (all frames of one track on one day, mosaicked):
  1. HH backscatter is speckle-filtered (speckle_m window) and resampled to a fixed lon/lat
     grid (~20 m) shared by all passes.
  2. Water = filtered HH below water_db, plus pixels below water_db_weak touching that water.
     Specks under 1 ha are dropped and holes under 2 ha inside water are filled.
  3. For every channel width W in widths_m, the water mask is reduced to the pixels at
     least W/2 from the shore; a community is connected at width W when, within
     access_radius_m of it, one of those pixels belongs to the same component as the
     water around the hub. Its bottleneck is the widest W that still connects it.
  4. Status: connected (bottleneck >= safe_width_m), at_risk (connected, narrower),
     isolated (no water path, or no water within access_radius_m), no_data.

Output (frontend/public/data/monitor/<area>/): catalog.json and, per pass, radar.webp,
water.png, change.png and water.npz. The code lives in the `lifeline` package next to this
file; see docs/river-monitor.md.
"""
import argparse

from lifeline import pipeline
from lifeline.area import load_area

COMMANDS = ("communities", "update", "reevaluate", "watch")


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=COMMANDS)
    ap.add_argument("--area", default="tefe")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--limit", type=int, help="process only the N most recent pending passes")
    ap.add_argument("--redo", action="store_true", help="reprocess passes already in the catalog")
    ap.add_argument("--hours", type=float, default=6.0, help="watch: hours between searches")
    return ap.parse_args(argv)


def main(argv=None):
    a = parse_args(argv)
    area = load_area(a.area)
    if a.command == "communities":
        pipeline.communities(area)
    elif a.command == "update":
        pipeline.update(area, a.workers, a.limit, a.redo)
    elif a.command == "reevaluate":
        pipeline.reevaluate(area)
    else:
        pipeline.watch(area, a.hours, a.workers)


if __name__ == "__main__":
    main()
