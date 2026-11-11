# ADR-003: Water threshold measured on every pass (M2)

- Status: **proposed**, pending the project lead's decision with the benchmark results (2026-11-11)
- Component: river lifeline monitor, `processing/src/lifeline/analysis/water.py` (`pass_thresholds`,
  `ki_threshold`, `mixed_tiles`), area key `water_db_adaptive`

## Context

The water threshold was fixed at −15 dB (−12 dB for the hysteresis), tuned on two passes of the box-filtered
backscatter. It is applied the same to every track, incidence angle and date, while NISAR data are provisional and
their calibration may shift with the validated reprocessing. The refined Lee filter (ADR-002) also changes the value
distribution the threshold was tuned on.

## Method

Split-based selection (Martinis et al. 2009): the filtered image is cut into 4 km tiles; the tiles with 20–80 % of
their pixels under the prior threshold (−15 dB) and at least 90 % valid hold both water and land. The
Kittler-Illingworth minimum-error threshold of their pixels (each class modelled as a Gaussian; middle of the
plateau when the classes are fully separated) is clamped to `range_db` and the hysteresis threshold keeps its offset
(+3 dB). Fewer than `min_tiles` (5) mixed tiles: the fixed threshold. Each pass entry records the threshold it used
(`threshold` in `catalog.json`).

## What it measures on Tefé

On four passes (refined Lee output, 2026-11-11) the measured threshold is −11.4 to −12.5 dB, above the upper bound,
so all four are clamped to **−13 dB** (hysteresis −10 dB): with the proposed range M2 behaves as a threshold 2 dB
higher than before on every pass. More pixels become water: channels come out wider (fewer conservative misses), but
shores, smooth mud and wind-roughened water also join more easily, which can create false routes.

## Options

| Option | Expected effect |
|---|---|
| A. Range [−20, −13] (implemented here) | Effectively −13 dB: wider channels, more shore and mud as water; risk of false routes |
| B. Adaptive but never above the fixed −15 dB (range [−20, −15]) | Effectively −15 dB on Tefé today; still adapts if the calibration shifts darker |
| C. No M2: fixed −15 dB | Unchanged from the M4 result |

## Decision

Pending. The benchmark compares A (`m2-adaptive-threshold`) with C (`m4-refined-lee`); B gives C's result on the
current data.
