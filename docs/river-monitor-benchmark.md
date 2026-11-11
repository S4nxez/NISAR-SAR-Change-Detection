# River monitor accuracy benchmark ("exam")

`river-monitor benchmark` measures how right the monitor is, so every change to the method can be judged by numbers
instead of by eye. It runs **the method of the current checkout** end to end, as a black box, and scores what comes
out (`catalog.json` and the stored water masks). The same exam run before and after a change tells whether the
change helped. Every run is kept in `processing/benchmark/history/`, with an index in its `README.md`.

## Run it

```bash
python -m pip install -e "processing[benchmark]"      # adds rasterio, to read Sentinel-2
export MONITOR_CACHE_DIR=/path/with/space              # ~250 MB per granule; ~15 GB for the Tefé exam
export EARTHDATA_TOKEN=...                             # only while the cache still misses windows
river-monitor benchmark --label develop-baseline       # synthetic + real; --skip-real for synthetic only
```

The first run downloads the area window of every exam pass (HH and HV) and the Sentinel-2 scenes into the cache.
Later runs read only the cache, the Earth Search catalogue and the ANA gauge (whose last series is cached too).
Commit the two files a run writes to `processing/benchmark/history/` together with the change they measure.

## What is fixed and what is measured

`processing/benchmark/exam.json` fixes the passes, the reference rules and the synthetic settings. Two results are
comparable only when they share the exam `version`; change any value of that file only together with the version.

| Part | Question | Reference |
|---|---|---|
| Synthetic scenes | Does the method give the right answer where the answer is known? | Scenes built with known channels and obstacles |
| Real passes vs Sentinel-2 | Is the water mask right, and does it lead to the right community status? | MNDWI of a clear Sentinel-2 date within 2 days |
| River gauge | Does the record follow the river? | ANA telemetry, Tefé-Missões (12900001) |
| Field checks | Are named communities right? | `processing/benchmark/ground_truth.json` |

### Synthetic scenes

Ten lanes on a 20 m UTM grid: a wide river with the hub on the west edge, and in every lane a channel to a lake with
one community. The scene is written as cached granule windows and processed by `pipeline.update`, so filter,
threshold, classes and routes are all the checkout's own. Five speckle draws (seeds) per run.

| Lane | Tests | Expected status |
|---|---|---|
| `channel_20m`, `channel_40m` | channels narrower than the safe width (60 m) | `narrow`: at risk or isolated are correct, connected is dangerous |
| `channel_60m`, `channel_100m`, `channel_200m`, `channel_400m` | resolvable channels | connected |
| `zigzag_100m` | a channel running at 45 degrees | connected |
| `vegetation_block` | 400 m of flooded vegetation across a 200 m channel | isolated (vegetated water is not a navigable route) |
| `mud_bar` | 300 m of smooth wet mud across a 200 m channel | isolated |
| `wind_stretch` | 800 m of wind-roughened water in a 200 m channel | connected |

Grades: **correct**; **conservative** (a route that exists is reported narrower or missing: the safe-side error the
project accepts); **dangerous** (a route is reported that does not exist or is narrower than the safe width).

Surface backscatter (mean, dB), chosen inside the L-band ranges reported for the central Amazon floodplain
(Hess et al. 1995, IEEE TGRS 33(4), SIR-C; Hess et al. 2003, Remote Sensing of Environment 87, JERS-1). They are
assumptions of the exam, not measurements of NISAR over Tefé:

| Surface | HH | HV |
|---|---|---|
| Forest (not flooded) | −7 | −12.5 |
| Calm open water | −23 | −30 |
| Wind-roughened water | −13 | −26 |
| Flooded vegetation (double bounce) | −1 | −9.5 |
| Smooth wet mud or sand | −17 | −27 |

Speckle is gamma distributed with the exam's number of looks (`synthetic.looks`). It is set to the equivalent number
of looks (ENL = (mean / standard deviation)² over homogeneous open water) measured on the real GCOV windows.

### Real passes against Sentinel-2

For every evaluated pass, the Sentinel-2 L2A date within `max_days` (2) with the largest clear share of the area is
used if at least `min_clear` (30 %) is clear. Scenes come from the public Earth Search catalogue (Element 84, COGs on
AWS). Reflectance = DN × scale + offset (from the scene metadata; baseline 04.00 and later carry a −0.1 offset).
MNDWI = (B03 − B11) / (B03 + B11) at 20 m; water = MNDWI above an Otsu threshold of the clear pixels, clamped to
[−0.2, 0.3]; clouds, cirrus and cloud shadows (SCL 3, 8, 9, 10) are masked with a 100 m margin.

Scores, on the pixels both cover, pooled over all passes:

- **IoU, F1, precision, recall** of water.
- **Recall by width**: share of Sentinel-2 water in channels < 60 m, 60–200 m and ≥ 200 m (the monitor's own width
  rule) mapped as water.
- **False water** at the shore (land within 100 m of Sentinel-2 water) and far from it.
- **Community status** against the status the monitor's own route rule gives on the Sentinel-2 water: agreement,
  Cohen's kappa, **false routes** (a route Sentinel-2 water does not have: the dangerous error), **overconfident**
  (connected where Sentinel-2 only finds a narrow route) and **false isolated** (the safe-side error). Places inland in
  both are left out.

### River gauge

Spearman rank correlation, over the evaluated passes, of the gauge level with the detected water area (expected
positive) and with the number of communities that lost their route (isolated with water within the access radius;
expected negative).

### Field checks

`ground_truth.json` holds dated checks: `field` (people on the ground: civil defence, Instituto Mamirauá, health or
school boats, community leaders), `report` (dated news or official report naming the community) and `sanity`
(plausibility checks of the team, **not** independent truth). The score is the share of evaluated passes inside each
check's dates where the status matches (`linked` = connected or at risk).

## Limitations

- **There is no independent field truth yet.** No per-community, dated list of isolated communities exists for the
  NISAR period (from late 2025). The two checks present are sanity checks. The most valuable addition is a dated list
  from Defesa Civil or the Instituto Mamirauá.
- **Sentinel-2 is a reference, not the truth.** It also misses channels narrower than ~20–40 m, cannot see water
  under forest or floating vegetation, and is up to 2 days away from the pass (the river can move tens of centimetres
  a day in the dry season). Its status is computed with the monitor's own route rule, so it scores the water mask's
  consequences, not the route rule itself.
- **The synthetic scene is idealised**: uniform surfaces, straight channels, assumed backscatter. It catches
  regressions and known weak points (narrow channels, mud, vegetation, wind) but its numbers do not transfer to Tefé.
- Sanity checks and the gauge correlation cannot tell which community is wrong, only whether the record is coherent.
- NISAR data are provisional: a future reprocessing changes the inputs, and the exam version must change with them.
