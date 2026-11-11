# Benchmark history

One row per run of `river-monitor benchmark` (see docs/river-monitor-benchmark.md). Compare rows of the same exam version only. `*` after a commit: the run had uncommitted changes.

| Result | Date | Exam | Commit | Synthetic correct | Synthetic dangerous | Water IoU vs S2 | Narrow recall | False water at shore | Status agreement | False routes | False isolated | Gauge rho | Field checks |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [develop-baseline](20261111T185532Z_develop-baseline.md) | 2026-11-11 | 1 | `d9d01ee` | 0.800 | 5 | 0.850 | 0.545 | 0.110 | 0.919 | 20 | 12 | -0.735 | 1.000 |
| [fill-as-no-data](20261111T191323Z_fill-as-no-data.md) | 2026-11-11 | 1 | `1bdaacb` | 0.800 | 5 | 0.901 | 0.545 | 0.109 | 0.919 | 20 | 12 | -0.735 | 1.000 |

Columns:

- **Synthetic correct**: share of lane results that are right (higher is better).
- **Synthetic dangerous**: lane results showing a route that does not exist or is too narrow.
- **Water IoU vs S2**: agreement of the water mask with Sentinel-2 (higher is better).
- **Narrow recall**: share of Sentinel-2 channels under 60 m mapped as water.
- **False water at shore**: share of shoreline land mapped as water (lower is better).
- **Status agreement**: community status equal to the one from Sentinel-2 water.
- **False routes**: community shown with a route Sentinel-2 water does not have (lower is better).
- **False isolated**: community shown isolated while Sentinel-2 water links it.
- **Gauge rho**: rank correlation of lost routes with the river level (more negative is better).
- **Field checks**: share of field and report checks the record gets right.
