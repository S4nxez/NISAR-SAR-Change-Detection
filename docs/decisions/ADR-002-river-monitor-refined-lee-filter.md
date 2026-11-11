# ADR-002: Refined Lee speckle filter instead of the 60 m box mean

- Status: accepted (2026-11-11)
- Component: river lifeline monitor, `processing/src/lifeline/analysis/radar.py` (`refined_lee`, `filter_db`),
  area keys `speckle_filter`, `speckle_looks`

## Context

The monitor averaged HH over a 3 × 3 box (60 m) before thresholding. In linear power one forest pixel (about −7 dB)
weighs as much as 30 water pixels (about −22 dB), so the box blurs every shore: a 40 m channel comes out around
−11.5 dB (land), a 60 m channel keeps only its centre line, and every channel shrinks by about two pixels. This was
one cause of the "no water" areas that Sentinel-2 NDWI shows as water (review of 2026-11-10).

The equivalent number of looks of the GCOV windows over open water is 9 to 10 (measured on the cached 20 MHz passes,
2026-11-11), so the products arrive already well averaged.

## Options

| Option | Effect on accuracy |
|---|---|
| Keep the 60 m box | Shores blurred, channels of 40–100 m narrowed or lost |
| Lee (local statistics) | No blur at edges, but no smoothing there either |
| **Refined Lee** (edge-aligned half windows) | Shores kept and smoothed along the edge; lines 1–2 pixels wide (≤ 40 m) are still partly blurred |
| Multitemporal (Quegan–Yu) | Most speckle reduction without spatial blur, but water that dried in the last weeks can survive as a "ghost channel": a false route, the most dangerous error. Left for later, with a change test |

## Decision

Refined Lee with a 7 × 7 window and `speckle_looks` = 9 (the measured ENL), chosen by the project lead from the
recommendation (M4 of `docs/river-monitor-accuracy-review.md`). The box filter remains available
(`speckle_filter: "box"`) for comparisons.

## Consequences

- Channels of about 60–150 m keep their width; the narrowest ones (≤ 40 m) improve but stay unreliable, which the
  project accepts (narrow or shallow routes may be shown as not passable).
- Thresholds were tuned on the box output; the filter changes the value distribution, so M2 (per-pass threshold)
  follows.
- About 40 s more per granule on a desktop.
- Measured with the benchmark: result `m4-refined-lee` in `processing/benchmark/history/`.
