# ADR-007: Sentinel-1 tells drained beds from water at low water

- Status: proposed (2026-11-13)
- Component: river lifeline monitor, `processing/src/lifeline/sources/sentinel1.py`,
  `analysis/water.py` (`low_water_route`), `output/catalog.py` (`hold_unverified`), called by
  `pipeline.judge`; area keys `low_water` and `sentinel1`

## Context

The manual review of exam 2 (`processing/benchmark/reviews.json`) confirmed 4 false routes, all over the bed of a
drained lake or side channel at low water. In NISAR's L band (24 cm) wet, smooth mud is as smooth as water: it reads
about −17 dB in HH and is mapped as water, so the monitor showed wide routes where only a creek or nothing was left.
This is the dangerous error of the monitor: a community shown connected that is not.

### First attempt: historical occurrence alone (commit `21a1e94`)

At low water (river gauge at most 1200 cm), water on seasonal ground (JRC Global Surface Water occurrence 30–90 %)
carried no route where it formed a broad patch. Exam 2 (`low-water-seasonal-beds` against `v2-swath-edge-margin`):
false routes 6 → 0, but false isolated 14 → 28 and status agreement 0.955 → 0.936. The occurrence says where the
river *can* drain, not whether it *has*: seasonal lakes that still hold water lost their routes too.

### Evidence for Sentinel-1

Sentinel-1 (C band, 5.6 cm) sees the same mud as rough. VV backscatter on the pass of 2026-10-23 against the
Sentinel-1 scene of 2026-10-20, on NISAR water over seasonal ground:

| Surface (by the optical reference) | Median VV | p10 VV |
|---|---|---|
| Drained bed (reference land) | −11.4 dB | −17.7 dB |
| Seasonal lake still holding water | −20.8 dB | |
| Permanent river | −21.0 dB | |
| Land elsewhere | −6.7 dB | |

The two kinds of seasonal ground the occurrence cannot split are about 10 dB apart in C band. NASA has no ready
10 m Sentinel-1 product (OPERA RTC-S1 is 30 m); Microsoft Planetary Computer serves the radiometrically
terrain-corrected Sentinel-1 scenes at 10 m pixels without an account.

## Decision

Every pass reads the Sentinel-1 VV scenes within `sentinel1.max_days` (4) of it, closest first, skipping a scene
taken after the river fell more than `level_tolerance_cm` (30) below its level on the pass day. They are averaged to
the 20 m grid, filtered (refined Lee, 6 looks) and classed as water (hysteresis −18 / −16 dB), land (≥ −16 dB) or
undecided, and cached per date.

When the gauge on the day of the pass is at most `low_water.gauge_max_cm`, on seasonal ground:

- NISAR water that Sentinel-1 sees as land, in patches at least 60 m across (an opening with a 20 m disc), carries no
  route (mud veto);
- a broad seasonal patch (holding a 60 m disc) that no usable Sentinel-1 scene sees is *unverified*: a route through
  it makes a community at most *at risk*, and the pass lists it in `unverified_route`;
- a seasonal lake Sentinel-1 still sees as water keeps its route.

Above the gauge threshold, or without a gauge level, nothing changes. Each pass records the agreement of the two
radars (`sentinel1` in the catalog) and stores the classes it used (`sentinel1.npz`) for `reevaluate`.

The thresholds came from a prototype over the reviewed places: with −16 dB and a 20 m veto radius the 7 manual
verdicts all come out right, and 3–6 statuses per low-water pass change against no rule, against 9–12 with the
occurrence rule.

Because the method now uses Sentinel-1, exam 3 drops OPERA DSWx-S1 from its references (Sentinel-2 and DSWx-HLS
remain) and adds a section, not scored, where NISAR and Sentinel-1 check each other and the places where they give a
community different statuses are listed for manual verdicts (`processing/benchmark/crosscheck_reviews.json`).

## Benchmark result

Exam 3 (`v3-sentinel1-mud-veto`). Its references differ from exam 2, so the numbers are not strictly comparable:

| Metric | v2-swath-edge-margin (exam 2, no rule) | low-water-seasonal-beds (exam 2, occurrence) | v3-sentinel1-mud-veto (exam 3) |
|---|---|---|---|
| Water IoU vs consensus | 0.931 | 0.931 | 0.929 |
| Status agreement | 0.955 | 0.936 | 0.961 |
| False routes | 6 | 0 | 0 |
| False isolated | 14 | 28 | 15 |
| Gauge rho | −0.773 | −0.889 | −0.759 |
| Undecided pairs | 85 | 85 | 47 |
| Cases to review | 16 | 0 | 1 |

The false routes stay at 0 and the false isolated fall back to the level of no rule. One case is new and waits for a
person: Nova Esperança on 2026-10-11, cut off by the mud veto while the optical reference links it.

NISAR and Sentinel-1 agree on 98.3 % of the 46 749 km² both judged over 6 passes. They give a community different
statuses in 227 community-pass pairs at 67 places. The largest group is narrow channels (104 pairs), probably where
Sentinel-1, about 20 m of real resolution, loses channels NISAR keeps; the published status follows NISAR in 200 of
the 227. These places wait for verdicts.

## Consequences

- No route over a bed Sentinel-1 sees drained; communities by seasonal lakes that still hold water keep theirs.
- Without a usable Sentinel-1 scene at low water, routes through broad seasonal patches are capped at *at risk*:
  cautious, never a false *connected*.
- The worker depends on `rasterio` (moved from the benchmark extra to the main dependencies; the aarch64 wheel of the
  Raspberry Pi image is still to be checked) and on Planetary Computer: about 1 min of download per new Sentinel-1
  date. A failure skips Sentinel-1 for that pass and falls back to the unverified cap.
- Only descending tracks (54 and 156, every 5–7 days) are terrain-corrected over Tefé; some passes have no scene
  within 4 days.
- Next steps: weigh the two radars per zone type (NISAR under vegetation and on wind-roughened water, Sentinel-1 on
  mud and in narrow channels) with weights measured from the crosscheck verdicts; ASF HyP3 can produce 10 m RTC from
  Sentinel-1 on demand if a NASA source is preferred.
