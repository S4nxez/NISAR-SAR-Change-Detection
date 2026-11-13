# ADR-001: Radar values below −40 dB are no data, not water

- Status: accepted (2026-11-11)
- Component: river lifeline monitor, `processing/src/lifeline/analysis/radar.py` (`mask_fill`), area key
  `valid_floor_db`

## Context

The GCOV windows over Tefé carry near-zero fill at the edge of the imaged swath. Inside the 55 km circle it covers
3 to 6 % of the area on the high-water passes of track 161 (25 June, 7 and 19 July 2026: −57 to −100 dB) and about
3 % on the descending passes of track 169 (−130 to −168 dB), and 0.7 % on 31 August (track 97). The project lead had
also seen it on the map, in the lower right of the circle on descending passes.

No radar measurement is that dark: NISAR's noise-equivalent backscatter is about −25 dB and open water on the same
passes does not go below −20 to −22 dB (1st percentile). Before this change only zero, negative and non-finite values
were no data, so the fill counted as valid and, being far below the −15 dB threshold, as **water**. That can create
water, and routes, that do not exist.

## Options

| Option | Effect on accuracy |
|---|---|
| Leave it | False water and possible false routes at the swath edge on the affected passes |
| No data below −40 dB | Removes all the fill seen; 15 dB below the noise floor, so no real water pixel is lost |
| No data below −35 dB | Also removes a few isolated pixels between −35 and −40 dB; a small risk of dropping very calm water |

## Decision

No data below **−40 dB** (`valid_floor_db` in the area file, default −40). The project lead chose the rule ("if
there is no data, better mark it as no data"); −40 dB was the recommended floor. The mask is applied before the
speckle filter, so fill is not averaged into its neighbours.

## Consequences

- The affected stretches become gaps. A route that may run through a gap gives **no data** for that community on
  that pass, never connected (existing rule of `analysis.water.undetermined_targets`), and a pass whose coverage
  drops under 80 % is not evaluated.
- Coverage figures of those passes go down.
- Measured with the benchmark: see `processing/benchmark/history/` (result `fill-as-no-data` against
  `develop-baseline`).
