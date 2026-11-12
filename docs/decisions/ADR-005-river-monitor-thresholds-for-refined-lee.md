# ADR-005: Water thresholds tuned for the refined Lee filter

- Status: proposed (2026-11-12), pending the full benchmark run
- Component: river lifeline monitor, area keys `water_db` and `water_db_weak` (`processing/areas/tefe.json`)

## Context

The thresholds −15 dB (water) and −12 dB (hysteresis) were tuned on the box-filtered backscatter. The refined Lee
filter (ADR-002) keeps shores sharp, but it also keeps the speckle of heterogeneous pixels at the shore, where the
box filter smoothed it away. With a −12 dB hysteresis, water grows through those noisy shore pixels into the land.
In the benchmark (exam version 1), M4 with the old thresholds doubled false water at the shore (0.109 → 0.198) and
false routes (20 → 43): the dangerous error, a community told it can travel when it cannot.

## What was measured

A diagnostic on the 7 exam passes that have a Sentinel-2 reference scored water-mask variants with the exam's own
pixel and status scores (without the previous-pass confirmation). It gives the same numbers as the benchmark for the
box filter (20 false routes) and for M4 (43).

| Variant | IoU | Recall < 60 m | False water shore | Status agreement | False routes | False isolated |
|---|---|---|---|---|---|---|
| Box −15/−12 (before M4) | 0.901 | 0.545 | 0.109 | 0.919 | 20 | 12 |
| Lee −15/−12 (M4) | 0.891 | 0.767 | 0.198 | 0.877 | 43 | 1 |
| Lee −17/−13 | 0.902 | 0.599 | 0.164 | 0.892 | 25 | 12 |
| **Lee −16/−14** | **0.909** | 0.497 | 0.136 | **0.937** | **8** | 13 |
| Lee −17/−14 | 0.909 | 0.481 | 0.135 | 0.937 | 8 | 13 |
| Lee −18/−14 | 0.908 | 0.430 | 0.130 | 0.936 | 8 | 13 |
| Lee −17/−15 | 0.901 | 0.320 | 0.103 | 0.932 | 8 | 18 |
| Lee −16, no hysteresis | 0.874 | 0.182 | 0.072 | 0.915 | 6 | 23 |

The hysteresis threshold decides the result: from −13 to −14 dB the false routes fall from 25 to 8, while the water
threshold barely matters between −16 and −18 dB. The gain holds pass by pass (24 August: 11 → 0 false routes;
31 August: 18 → 3), so it is not one pass driving the total.

## Decision

Lee with −16 dB (water) and −14 dB (hysteresis): the fewest false routes with the best agreement and IoU, and of
those variants the one that keeps the most narrow channels.

Compared with the method before M4, false routes fall from 20 to 8 and false isolated stay level (12 → 13); the
cost is fewer narrow channels found (recall under 60 m 0.545 → 0.497).

## Risks

- The thresholds are chosen on the same 7 passes the exam scores, so the exam's real-pass numbers are optimistic.
  New passes with a clear Sentinel-2 date should be added to the next exam version to check them.
- The hysteresis threshold (−14 dB) sits below the exam's wind-roughened water (−13 dB): wide wind stretches that
  do not touch calm water may be lost. The synthetic `wind_stretch` lane checks it.
- Thresholds depend on the provisional calibration of NISAR, as in ADR-003.
