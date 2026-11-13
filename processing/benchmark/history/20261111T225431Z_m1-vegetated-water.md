# Benchmark: m1-vegetated-water

Exam version 1 · 2026-11-11T22:54:31Z · commit `fa491fc`

## Scorecard

| Metric | Value | Meaning |
|---|---|---|
| Synthetic correct | 0.900 | share of lane results that are right (higher is better) |
| Synthetic dangerous | 5 | lane results showing a route that does not exist or is too narrow |
| Water IoU vs S2 | 0.859 | agreement of the water mask with Sentinel-2 (higher is better) |
| Narrow recall | 0.909 | share of Sentinel-2 channels under 60 m mapped as water |
| False water at shore | 0.265 | share of shoreline land mapped as water (lower is better) |
| Status agreement | 0.842 | community status equal to the one from Sentinel-2 water |
| False routes | 61 | community shown with a route Sentinel-2 water does not have (lower is better) |
| False isolated | 0 | community shown isolated while Sentinel-2 water links it |
| Gauge rho | -0.416 | rank correlation of lost routes with the river level (more negative is better) |
| Field checks | 1.000 | share of field and report checks the record gets right |

## Synthetic scenes

5 speckle draws with 9 looks. Expected status per lane and how often each grade came out.

| Lane | Expected | Correct | Conservative | Dangerous | No data |
|---|---|---|---|---|---|
| channel_20m | narrow | 5 | 0 | 0 | 0 |
| channel_40m | narrow | 5 | 0 | 0 | 0 |
| channel_60m | connected | 5 | 0 | 0 | 0 |
| channel_100m | connected | 5 | 0 | 0 | 0 |
| channel_200m | connected | 5 | 0 | 0 | 0 |
| zigzag_100m | connected | 5 | 0 | 0 | 0 |
| vegetation_block | isolated | 5 | 0 | 0 | 0 |
| mud_bar | isolated | 0 | 0 | 5 | 0 |
| wind_stretch | connected | 5 | 0 | 0 | 0 |
| channel_400m | connected | 5 | 0 | 0 | 0 |

| Surface | HH / HV (dB) | Mapped as water | Mapped as vegetated water |
|---|---|---|---|
| forest | -7 / -12.5 | 0.012 | 0.000 |
| water | -23 / -30 | 1.000 | 0.000 |
| wind | -13 / -26 | 0.997 | 0.000 |
| flooded_vegetation | -1 / -9.5 | 0.000 | 0.972 |
| mud | -17 / -27 | 0.999 | 0.000 |

## Real passes against Sentinel-2

Reference: MNDWI of the clearest Sentinel-2 L2A date within 2 days of the pass, at least 30% of the area clear. 7 passes had one. Pixel counts pooled over all of them.

| IoU | F1 | Precision | Recall | Recall < 60 m | Recall 60-200 m | Recall >= 200 m | False water shore | False water far |
|---|---|---|---|---|---|---|---|---|
| 0.859 | 0.924 | 0.863 | 0.994 | 0.909 | 0.980 | 0.997 | 0.265 | 0.008 |

Community status against the status the monitor's own route rule gives on the Sentinel-2 water (475 community-pass pairs; inland places left out):

| Agreement | Mean kappa | False routes | Overconfident | False isolated |
|---|---|---|---|---|
| 0.842 | 0.471 | 61 | 14 | 0 |

| Pass | Sentinel-2 | Days | Clear | IoU | Recall < 60 m | Agreement | False routes | False isolated |
|---|---|---|---|---|---|---|---|---|
| 2025-11-04_t097D | 2025-11-05 | 1 | 0.385 | 0.819 | 0.919 | 0.722 | 3 | 0 |
| 2026-07-07_t161A | 2026-07-06 | 1 | 0.596 | 0.899 | 0.889 | 0.794 | 3 | 0 |
| 2026-08-19_t097D | 2026-08-20 | 1 | 0.732 | 0.879 | 0.928 | 0.925 | 6 | 0 |
| 2026-08-24_t161A | 2026-08-25 | 1 | 0.795 | 0.917 | 0.887 | 0.849 | 16 | 0 |
| 2026-08-31_t097D | 2026-08-30 | 1 | 0.997 | 0.845 | 0.907 | 0.829 | 25 | 0 |
| 2026-10-11_t161A | 2026-10-11 | 0 | 0.559 | 0.762 | 0.917 | 0.773 | 5 | 0 |
| 2026-10-23_t161A | 2026-10-21 | 2 | 0.443 | 0.699 | 0.967 | 0.786 | 3 | 0 |

## River gauge

ANA telemetry, station 12900001.

| Correlation | Spearman rho | Passes | Expected sign |
|---|---|---|---|
| water area vs level | 0.729 | 15 | + |
| lost routes vs level | -0.416 | 15 | - |

## Field and report checks

| Community | Expected | Kind | Found | Passes judged | Correct | Source |
|---|---|---|---|---|---|---|
| Caiambé | linked | sanity | True | 14 | 14 | Team plausibility check (docs/river-monitor.md): settlement on the Solimões main channel, used as the boat landing in the 2023 and 2024 droughts. Not an observation of 2026. |
| Alvarães | linked | sanity | True | 14 | 14 | Team plausibility check (docs/river-monitor.md): municipal seat reached through its port; no 2026 report of the town being cut off was found. Not an observation of 2026. |

## Community classes

| monitored | unresolved | inland | no_data |
|---|---|---|---|
| 135 | 53 | 16 | 0 |
