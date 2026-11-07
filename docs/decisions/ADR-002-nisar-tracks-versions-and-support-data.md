# ADR-002: NISAR tracks, duplicated product versions and support data periods

- Status: **Accepted** (plan step 1.5)
- Date: 2026-11-07

## Context

The phase 1 inventory (`docs/data-inventory.md`) found 221 provisional GUNW products over the area from November 2025
to October 2026, on 8 track/frame combinations. Only ascending track 34 frame 20 and descending track 114 frame 70
cover the whole area in one frame. Some pairs exist in two versions (CRID `P05023` vs `X05010`, name field 13 `N` vs
`F`). OpenET needs an API key. OPERA DISP-S1 ends on 2026-04-26 over the area.

## Decisions

1. **Tracks:** A034 f20 and D114 f70. Two geometries allow the vertical / east-west decomposition (plan problem 9)
   and a consistency check between tracks; no mosaicking. Other tracks are not used.
2. **Duplicated versions:** both versions of each duplicated pair are kept and processed, and their difference is
   measured (phase 2) before choosing which one enters the time series. The choice is recorded in a later ADR.
   On the selected tracks this concerns A034 f20 (2025-12-30 → 2026-01-11, 2026-06-28 → 2026-07-10) and D114 f70
   (2025-11-30 → 2025-12-24, 2025-12-24 → 2026-01-17, `P05023` vs `X05010`).
3. **Evapotranspiration:** OpenET API with a free account; the key goes in `.env` as `OPENET_API_KEY`.
4. **NISAR vs Sentinel-1 comparison (phase 6):** November 2025 – April 2026, the real overlap of NISAR and OPERA
   DISP-S1, which also matches the DWR monthly rasters (to 2026-04-01).

## Effect on accuracy

- Two geometries remove the ambiguity between horizontal and vertical motion; the area keeps full coverage on both.
- Processing both versions of duplicated pairs quantifies the version-to-version error instead of assuming it.
- The comparison period is winter and spring, with less active irrigation: the expected L-band advantage over
  cultivated fields will be underestimated. This must be stated with the comparison results.

## Alternatives considered

- Descending only: half the data, but results in line of sight only.
- All tracks: more redundancy at the edges, mosaicking and about 4× the volume for little gain.
- Pick the production release and the most precise orbit without comparing: simpler, no measured version error.
- OpenET through Google Earth Engine, or ET from Sentinel-2: extra account or a less accurate, unvalidated estimate.
- Waiting for summer 2026 DISP-S1 or processing Sentinel-1 ourselves: uncertain availability or out of scope.
