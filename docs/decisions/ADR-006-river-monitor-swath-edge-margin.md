# ADR-006: No data along the last kilometre of the swath

- Status: proposed (2026-11-12), benchmarked; pending the project lead's decision
- Component: river lifeline monitor, `processing/src/lifeline/analysis/radar.py` (`trim_swath_edge`), called by
  `pipeline.process_pass`; area key `edge_margin_m`

## Context

The first run of exam version 2 (`v2-first-run`) traced 7 of its 13 false routes to one place, near −64.316,
−3.587, always on track 097D and always linking the same communities (Itauba, Prainha, Marajó). The cause rule
was `swath_edge`.

The backscatter of the three 097D passes, by distance to the edge of the data:

| Distance to the edge | 2025-11-04 median HH | 2026-08-19 | 2026-08-31 | Mapped as water |
|---|---|---|---|---|
| 0–100 m | −25.5 dB | −18.5 dB | −35.2 dB | 97–100 % |
| 100–200 m | −23.3 | −17.4 | −29.3 | 94–100 % |
| 200–400 m | −20.9 | −15.8 | −23.5 | 77–100 % |
| 400–800 m | −17.8 | −13.5 | −18.0 | 44–100 % |
| 800–1600 m | −13.6 | −10.4 | −12.9 | 21–43 % |
| 1.6–5 km | −8.0 | −6.1 | −6.7 | 9–10 % |

The signal rolls off to the noise floor towards the edge of the swath, past the −40 dB fill that ADR-001 already
removes. A band several hundred metres wide reads as water along the whole edge: a fake channel that links every
community near it. Track 161A sees the same place as land.

## Decision

Pixels within `edge_margin_m` (1000 m on Tefé) of the edge of the data become no data, after the speckle filter and
before the water mask. The edge is no data inside the area; the corners of the circular area are not an edge. HV is
masked with HH.

1 km is where the median falls back near the interior's on two of the three passes; the third still reads darker
at 800–1600 m, partly because real water lies there. The cost is 1 km of coverage at each edge of every pass, which
other tracks cover.

## Benchmark result

Exam version 2, before (`v2-first-run`, commit `ae84dd9`) and after (`v2-swath-edge-margin`, commit `99bfc68`):

| Metric | Before | After |
|---|---|---|
| Water IoU vs consensus | 0.922 | 0.931 |
| Status agreement (kappa) | 0.947 (0.880) | 0.955 (0.898) |
| False routes | 13 | 6 |
| False isolated | 14 | 14 |
| Undecided pairs | 86 | 85 |
| Cases to review (places) | 23 | 16 (6) |

The 7 false routes at the edge of track 097D are gone and nothing got worse. The 6 left all lie near clouds of the
Sentinel-2 reference (`cloud_edge`) and wait for a manual review.

## Consequences

- The fake channel along the edge disappears; communities near an edge are judged on the passes that see them well.
- A community whose surroundings lose more than 20 % of their coverage to the margin becomes "no data" on that pass
  instead of getting a status (MIN_COVERAGE_AROUND).
- A margin measured per pass (where the median departs from the interior) could keep more data; left for later.
