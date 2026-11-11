# Benchmark: develop-baseline

Exam version 1 · 2026-11-11T18:55:32Z · commit `d9d01ee`

## Scorecard

| Metric | Value | Meaning |
|---|---|---|
| Synthetic correct | 0.800 | share of lane results that are right (higher is better) |
| Synthetic dangerous | 5 | lane results showing a route that does not exist or is too narrow |
| Water IoU vs S2 | 0.850 | agreement of the water mask with Sentinel-2 (higher is better) |
| Narrow recall | 0.545 | share of Sentinel-2 channels under 60 m mapped as water |
| False water at shore | 0.110 | share of shoreline land mapped as water (lower is better) |
| Status agreement | 0.919 | community status equal to the one from Sentinel-2 water |
| False routes | 20 | community shown with a route Sentinel-2 water does not have (lower is better) |
| False isolated | 12 | community shown isolated while Sentinel-2 water links it |
| Gauge rho | -0.735 | rank correlation of lost routes with the river level (more negative is better) |
| Field checks | 1.000 | share of field and report checks the record gets right |

## Synthetic scenes

5 speckle draws with 9 looks. Expected status per lane and how often each grade came out.

| Lane | Expected | Correct | Conservative | Dangerous | No data |
|---|---|---|---|---|---|
| channel_20m | narrow | 5 | 0 | 0 | 0 |
| channel_40m | narrow | 5 | 0 | 0 | 0 |
| channel_60m | connected | 0 | 5 | 0 | 0 |
| channel_100m | connected | 5 | 0 | 0 | 0 |
| channel_200m | connected | 5 | 0 | 0 | 0 |
| zigzag_100m | connected | 5 | 0 | 0 | 0 |
| vegetation_block | isolated | 5 | 0 | 0 | 0 |
| mud_bar | isolated | 0 | 0 | 5 | 0 |
| wind_stretch | connected | 5 | 0 | 0 | 0 |
| channel_400m | connected | 5 | 0 | 0 | 0 |

| Surface | HH / HV (dB) | Mapped as water | Mapped as vegetated water |
|---|---|---|---|
| forest | -7 / -12.5 | 0.003 | – |
| water | -23 / -30 | 0.901 | – |
| wind | -13 / -26 | 0.794 | – |
| flooded_vegetation | -1 / -9.5 | 0.000 | – |
| mud | -17 / -27 | 0.821 | – |

## Real passes against Sentinel-2

Reference: MNDWI of the clearest Sentinel-2 L2A date within 2 days of the pass, at least 30% of the area clear. 7 passes had one. Pixel counts pooled over all of them.

| IoU | F1 | Precision | Recall | Recall < 60 m | Recall 60-200 m | Recall >= 200 m | False water shore | False water far |
|---|---|---|---|---|---|---|---|---|
| 0.850 | 0.919 | 0.873 | 0.970 | 0.545 | 0.872 | 0.985 | 0.110 | 0.012 |

Community status against the status the monitor's own route rule gives on the Sentinel-2 water (444 community-pass pairs; inland places left out):

| Agreement | Mean kappa | False routes | Overconfident | False isolated |
|---|---|---|---|---|
| 0.919 | 0.649 | 20 | 3 | 12 |

| Pass | Sentinel-2 | Days | Clear | IoU | Recall < 60 m | Agreement | False routes | False isolated |
|---|---|---|---|---|---|---|---|---|
| 2025-11-04_t097D | 2025-11-05 | 1 | 0.385 | 0.872 | 0.635 | 0.867 | 2 | 0 |
| 2026-07-07_t161A | 2026-07-06 | 1 | 0.596 | 0.692 | 0.612 | 0.871 | 1 | 0 |
| 2026-08-19_t097D | 2026-08-20 | 1 | 0.732 | 0.923 | 0.578 | 0.868 | 2 | 10 |
| 2026-08-24_t161A | 2026-08-25 | 1 | 0.795 | 0.941 | 0.424 | 0.896 | 11 | 1 |
| 2026-08-31_t097D | 2026-08-30 | 1 | 0.997 | 0.887 | 0.489 | 0.970 | 3 | 1 |
| 2026-10-11_t161A | 2026-10-11 | 0 | 0.559 | 0.812 | 0.604 | 1.000 | 0 | 0 |
| 2026-10-23_t161A | 2026-10-21 | 2 | 0.443 | 0.767 | 0.714 | 0.900 | 1 | 0 |

## River gauge

ANA telemetry, station 12900001.

| Correlation | Spearman rho | Passes | Expected sign |
|---|---|---|---|
| water area vs level | 0.846 | 15 | + |
| lost routes vs level | -0.735 | 15 | - |

## Field and report checks

| Community | Expected | Kind | Found | Passes judged | Correct | Source |
|---|---|---|---|---|---|---|
| Caiambé | linked | sanity | True | 14 | 14 | Team plausibility check (docs/river-monitor.md): settlement on the Solimões main channel, used as the boat landing in the 2023 and 2024 droughts. Not an observation of 2026. |
| Alvarães | linked | sanity | True | 14 | 14 | Team plausibility check (docs/river-monitor.md): municipal seat reached through its port; no 2026 report of the town being cut off was found. Not an observation of 2026. |

## Community classes

| monitored | unresolved | inland | no_data |
|---|---|---|---|
| 132 | 39 | 33 | 0 |
