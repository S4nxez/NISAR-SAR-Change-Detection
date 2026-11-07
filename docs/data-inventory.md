# Data inventory (plan phase 1)

Checked on 2026-11-07. Area: Tule and Tulare Lake subbasins (search bbox -120.05, 35.75, -118.85, 36.45).

## NISAR L2 GUNW

221 products (`python -m irrigation_footprint.inventory`), all provisional (`NISAR_L2_GUNW_PROVISIONAL_V1`), frequency A,
mode 4000, single polarization HH (`SH`).

| Geometry | Track | Frame | Covers the bbox | Pairs | Dates | Long pairs (> 12 d) | Gaps |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Ascending | 34 | 20 | **100 %** | 26 | 2025-11-24 → 2026-10-14 | 3 × 24 d, incl. 07-22 → 08-15 | none |
| Descending | 114 | 70 | **99–100 %** | 22 | 2025-11-30 → 2026-10-20 | 3 × 24 d, 1 × 36 d (07-16 → 08-21) | none |
| Ascending | 34 | 19 | 0–1 % | 26 | 2025-11-24 → 2026-10-14 | 3 | none |
| Ascending | 106 | 20 | 5 % | 22 | 2025-12-23 → 2026-10-19 | 3 | none |
| Ascending | 135 | 19 / 20 | 1–3 % | 26 / 27 | 2025-11-19 → 2026-10-21 | 3 | 06-23 → 07-05 (f19) |
| Descending | 42 | 70 | 16–24 % | 26 | 2025-11-01 → 2026-10-15 | 2 | 06-17 → 06-29 |
| Descending | 114 | 71 | 2–9 % | 22 | 2025-11-30 → 2026-10-20 | 4 | none |

Findings that change the plan's assumptions:

1. **Series start in November 2025**, not 17 June 2026: about 11 months, including winter (no irrigation) and the
   2026 irrigation season. Risk 6 (short series) is much smaller.
2. **The 27 Jul – 10 Aug 2026 gap is bridged** by 24-day (A034) and 36-day (D114) GUNW pairs: the network is
   connected end to end on both main tracks. The plan assumed only 12-day pairs.
3. **Ascending and descending geometries both cover the whole area in one frame** (A034 f20, D114 f70): vertical /
   east-west decomposition is possible, no mosaicking needed.
4. Some pairs exist in several versions (CRID `P05023` vs `X05010`, `f13` N vs F): a choice to make (ADR).

## Support data

| Source | Access | Coverage | Notes |
| --- | --- | --- | --- |
| DWR / TRE Altamira InSAR (Sentinel-1) | Public: ArcGIS image services `gis.water.ca.gov/arcgisimg/rest/services/SAR` (monthly rasters "Total since 2015-06-13"), point CSV time series (`verticaldisplacementpointdata.zip`, WY2026Q3) on data.cnra.ca.gov | 2015-06 → **2026-04-01** (rasters); 433 054 points (100 m) in the bbox | Newer than the plan assumed (Jan 2026): overlaps NISAR Nov 2025 – Apr 2026 for validation |
| OPERA DISP-S1 | Public (CMR, Earthdata login to download) | Frames F11116, F16942; **last date 2026-04-26** | No summer 2026: the NISAR vs Sentinel-1 comparison can only use Nov 2025 – Apr 2026 |
| GNSS | Public: Nevada Geodetic Laboratory (NGL) daily series | 30 stations active after 2026-09-01 near the area: in the basin (CAHA, HANF, QCAP, TLBN, P566, CAD1, P565, P544, Q174, Q189…), Sierra foothills (P571, P572, WLHG, ISLK, WASG) | Foothill stations are candidates for the stable reference |
| OpenET | API `openet-api.org` requires an **API key** (`APIKeyHeader`) | — | Needs an account; alternative: OpenET on Google Earth Engine or ET from Sentinel-2 |
| Crop map | Public: DWR Statewide Crop Mapping, 2024 (provisional) and 2023, shapefile / geodatabase | Statewide, per field | USDA CDL 2025 also reachable (CropScape) |
| Irrigation / water districts | Public: DWR `i03 WaterDistricts` (GeoJSON, shapefile) | Statewide | Surface water deliveries per district: not found yet |
| Oil fields | Public: CalGEM field admin boundaries (516 fields), ArcGIS REST | Statewide | — |
| Subbasins / SGMA | Public: DWR B118 subbasins (5-022.12 Tulare Lake, 5-022.13 Tule), SGMA basin prioritization | — | Probation status from the State Water Board pages |

## Pending

- GUNW structure documented in `docs/components/gunw.md`. Open: whether the `...CorrectionApplied = True` flags
  mean the phase is already corrected, and the phase sign convention (both checked in phase 2).
- Surface water deliveries per irrigation district (class C depends on them).
