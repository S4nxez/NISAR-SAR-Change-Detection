# Benchmark history

One row per run of `river-monitor benchmark` (see docs/river-monitor-benchmark.md). Compare rows of the same exam version only. `*` after a commit: the run had uncommitted changes.

| Result | Date | Exam | Commit | Synthetic correct | Synthetic dangerous | Water IoU vs reference | Narrow recall | False water at shore | Status agreement | False routes | False isolated | Gauge rho | Field checks | Undecided | To review | Confirmed false routes | NISAR-S1 agreement | NISAR-S1 places |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [develop-baseline](20261111T185532Z_develop-baseline.md) | 2026-11-11 | 1 | `d9d01ee` | 0.800 | 5 | 0.850 | 0.545 | 0.110 | 0.919 | 20 | 12 | -0.735 | 1.000 | – | – | – | – | – |
| [fill-as-no-data](20261111T191323Z_fill-as-no-data.md) | 2026-11-11 | 1 | `1bdaacb` | 0.800 | 5 | 0.901 | 0.545 | 0.109 | 0.919 | 20 | 12 | -0.735 | 1.000 | – | – | – | – | – |
| [m4-refined-lee](20261111T202019Z_m4-refined-lee.md) | 2026-11-11 | 1 | `b3859ef` | 0.900 | 5 | 0.891 | 0.767 | 0.198 | 0.877 | 43 | 1 | -0.401 | 1.000 | – | – | – | – | – |
| [m2-adaptive-threshold](20261111T203501Z_m2-adaptive-threshold.md) | 2026-11-11 | 1 | `03ada68` | 0.900 | 5 | 0.859 | 0.909 | 0.265 | 0.842 | 61 | 0 | -0.416 | 1.000 | – | – | – | – | – |
| [m1-vegetated-water](20261111T225431Z_m1-vegetated-water.md) | 2026-11-11 | 1 | `fa491fc` | 0.900 | 5 | 0.859 | 0.909 | 0.265 | 0.842 | 61 | 0 | -0.416 | 1.000 | – | – | – | – | – |
| [m4-m1-no-m2](20261112T075504Z_m4-m1-no-m2.md) | 2026-11-12 | 1 | `c102d69` | 0.900 | 5 | 0.891 | 0.767 | 0.198 | 0.877 | 43 | 1 | -0.401 | 1.000 | – | – | – | – | – |
| [lee-thresholds-16-14](20261112T084145Z_lee-thresholds-16-14.md) | 2026-11-12 | 1 | `f8ec2a9` | 0.800 | 5 | 0.909 | 0.497 | 0.136 | 0.937 | 8 | 13 | -0.767 | 1.000 | – | – | – | – | – |
| [v2-first-run](20261112T125959Z_v2-first-run.md) | 2026-11-12 | 2 | `ae84dd9` | 0.800 | 5 | 0.922 | 0.414 | 0.087 | 0.947 | 13 | 14 | -0.767 | 1.000 | 86 | 23 | 0 | – | – |
| [v2-swath-edge-margin](20261112T140815Z_v2-swath-edge-margin.md) | 2026-11-12 | 2 | `99bfc68` | 0.800 | 5 | 0.931 | 0.410 | 0.082 | 0.955 | 6 | 14 | -0.773 | 1.000 | 85 | 16 | 0 | – | – |
| [low-water-seasonal-beds](20261112T231749Z_low-water-seasonal-beds.md) | 2026-11-12 | 2 | `21a1e94` | 0.800 | 5 | 0.931 | 0.410 | 0.082 | 0.936 | 0 | 28 | -0.889 | 1.000 | 85 | 0 | – | – | – |
| [v3-sentinel1-mud-veto](20261113T100324Z_v3-sentinel1-mud-veto.md) | 2026-11-13 | 3 | `21a1e94`* | 0.800 | 5 | 0.929 | 0.388 | 0.074 | 0.961 | 0 | 15 | -0.759 | 1.000 | 47 | 1 | – | 0.983 | 67 |

Columns:

- **Synthetic correct**: share of lane results that are right (higher is better).
- **Synthetic dangerous**: lane results showing a route that does not exist or is too narrow.
- **Water IoU vs reference**: agreement of the water mask with the reference: Sentinel-2 in exam 1, the consensus of the references from exam 2 (higher is better).
- **Narrow recall**: share of reference channels under 60 m mapped as water.
- **False water at shore**: share of shoreline land mapped as water (lower is better).
- **Status agreement**: community status equal to the one from the reference water.
- **False routes**: community shown with a route the reference water does not have (lower is better; not yet checked by a person).
- **False isolated**: community shown isolated while the reference water links it.
- **Gauge rho**: rank correlation of lost routes with the river level (more negative is better).
- **Field checks**: share of field and report checks the record gets right.
- **Undecided**: community-pass pairs the references cannot decide (exam 2), left unscored.
- **To review**: disagreements a person has to check (exam 2; see Manual review in the report).
- **Confirmed false routes**: false routes a person confirmed in processing/benchmark/reviews.json (exam 2).
- **NISAR-S1 agreement**: share of the pixels both radars judged on which NISAR and Sentinel-1 agree (exam 3, not scored).
- **NISAR-S1 places**: places where the two radars give a community different statuses, to check by hand (exam 3).
