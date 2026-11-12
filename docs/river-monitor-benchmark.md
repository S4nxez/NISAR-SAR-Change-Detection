# River monitor accuracy benchmark ("exam")

`river-monitor benchmark` measures how right the monitor is, so every change to the method can be judged by numbers
instead of by eye. It runs **the method of the current checkout** end to end, as a black box, and scores what comes
out (`catalog.json` and the stored water masks). The same exam run before and after a change tells whether the
change helped. Every run is kept in `processing/benchmark/history/`, with an index in its `README.md`.

## Run it

```bash
python -m pip install -e "processing[benchmark]"      # adds rasterio, to read Sentinel-2
export MONITOR_CACHE_DIR=/path/with/space              # ~250 MB per granule; ~15 GB for the Tefé exam
export EARTHDATA_TOKEN=...                             # while the cache still misses NISAR windows or OPERA tiles
river-monitor benchmark --label develop-baseline       # synthetic + real; --skip-real for synthetic only
```

The first run downloads the area window of every exam pass (HH and HV), the Sentinel-2 scenes, the OPERA DSWx tiles
and the static maps into the cache. Later runs read only the cache, the Earth Search and CMR catalogues and the ANA
gauge (whose last series is cached too). Without a token the exam still runs: OPERA files missing from the cache are
skipped and the report says which references each pass had. Commit the two files a run writes to
`processing/benchmark/history/` together with the change they measure.

All sources are free. Sentinel-2, WorldCover and JRC Global Surface Water need no account; OPERA needs the free NASA
Earthdata account the monitor already uses.

## What is fixed and what is measured

`processing/benchmark/exam.json` fixes the passes, the reference rules and the synthetic settings. Two results are
comparable only when they share the exam `version`; change any value of that file only together with the version.

| Part | Question | Reference |
|---|---|---|
| Synthetic scenes | Does the method give the right answer where the answer is known? | Scenes built with known channels and obstacles |
| Real passes vs references | Is the water mask right, and does it lead to the right community status? | Exam 1: MNDWI of a clear Sentinel-2 date within 2 days. Exam 2: consensus of Sentinel-2, OPERA DSWx-HLS and OPERA DSWx-S1 |
| Disagreements (exam 2) | What went wrong, why, and which cases must a person check? | Probable cause of every disagreeing pixel and community; verdicts in `processing/benchmark/reviews.json` |
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

### Real passes against Sentinel-2 (exam 1, and the anchor of exam 2)

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

### Exam 2: references, consensus and where each one is trusted

Sentinel-2 alone is not the truth: it misses channels narrower than 20 to 40 m, cannot see water under plants or
clouds, and may be two days away from the pass. Exam 2 uses several free references and trusts each one only where it
can see:

| Source | Family | Resolution | Strong where | Blind where |
|---|---|---|---|---|
| Sentinel-2 L2A MNDWI (Earth Search) | optical | 20 m | open water on clear days | clouds and shadows (masked with a 100 m margin), water under plants |
| OPERA DSWx-HLS (NASA/JPL; Landsat 8/9 and Sentinel-2) | optical | 30 m | its own cloud mask and classifier; more dates | same physics as Sentinel-2; partial-water pixels (mixed) |
| OPERA DSWx-S1 (NASA/JPL; Sentinel-1) | radar (C-band) | 30 m | through clouds; a processing independent of ours | shares radar blind spots with NISAR (smooth mud, wind) |
| ESA WorldCover 2021 | static land cover | 10 m | marks herbaceous wetlands and mangroves | – |
| JRC Global Surface Water occurrence 1984-2021 | static | 30 m | tells seasonal banks from permanent water | – |

Rules (`benchmark/consensus.py`):

- Each source votes "water" or "land" per pixel; an optical "land" under WorldCover wetlands or mangroves is dropped
  (plants hide the water), and DSWx-HLS partial-water pixels do not vote. DSWx-S1 inundated vegetation votes land:
  it is not a boat route, as NISAR's own vegetated class is not.
- **Reference water**: some source says water and none says land; **reference land**: the opposite; **disputed**:
  they disagree. Disputed pixels are not scored. The report also gives the share of pixels both families (optical and
  radar) agree on, and how often each source agrees with the consensus.
- **Community status**: computed on the consensus twice, with disputed pixels as land and as water. Where both give
  the same status it is the reference; otherwise the pair is **undecided** and left out of the status scores (counted
  in the scorecard).
- The Sentinel-2-only IoU is kept in the report, to compare with exam 1.

SWOT is not used yet: its free water mask over Tefé is a 100 m raster (too coarse for these channels) and its pixel
cloud is sparse in time. Commercial imagery (PlanetScope, Maxar) is left out: the project cannot pay for it.

### Exam 2: disagreements and probable causes

Every pixel where the water mask and the consensus disagree gets the first cause whose rule it meets, in this order
(`benchmark/causes.py`; thresholds in `exam.json`, `causes`):

| Cause | Family | Rule | Needs a person |
|---|---|---|---|
| `cloud_edge` | reference may be wrong | within 500 m of a Sentinel-2 cloud or shadow | yes |
| `river_level_change` | timing | seasonal ground (JRC occurrence 5-90 %) and the gauge moved 20 cm or more between the pass and the Sentinel-2 date | no |
| `swath_edge` | processing | within 1 km of the edge of the NISAR data | yes |
| `narrow_channel` | resolution | omission in a reference channel under 60 m | no |
| `shore_mixed_pixel` | resolution | within one pixel of the reference shore | no |
| `vegetation` | radar physics | omission under plants (NISAR vegetated class, DSWx-S1 inundated vegetation, WorldCover wetland) | no |
| `threshold` | processing | NISAR HH within 1 dB of the water threshold | no |
| `smooth_ground` | radar physics | commission on seasonal ground clearly dark in L-band (mud, sand) | yes |
| `wind_roughness` | radar physics | omission on permanent water (occurrence 90 % or more) clearly brighter than the threshold | no |
| `unexplained` | – | none of the above | yes |

The rules use the filtered backscatter of every pass, which the exam keeps (`backscatter.npz`, only when the exam
runs: `MONITOR_KEEP_BACKSCATTER=1`).

**Cases.** Every community whose status differs from a decided reference is a case: a false route (the method shows
a route the reference does not have), an overconfident or underconfident width, or a false isolation. Its culprit
pixels are the fewest disputed pixels a route has to cross between the hub and the community (a breadth-first search
where agreed water costs nothing). The case takes their most common cause, their centre as its location and links to
look at it. A case needs a person when it is a false route (the dangerous error) or when its cause says so.

### Manual review

The report's "Manual review" section lists the **places** to check. Cases of the same side (a route shown that the
reference does not have, or a route missed) whose culprit pixels lie within 1.5 km of one another are one place, named
after the nearest community ("Near Itauba", with the distance), so it can be found by name on any map. Each place
lists the communities and passes it explains and has, for each pass, links that open the map on the culprit point:

- **Sentinel-2** and **Sentinel-1** in the [Copernicus Browser](https://browser.dataspace.copernicus.eu/) (free; an
  account, also free, unlocks more tools), opened on the place and on the reference date. If the layer does not show,
  pick it in the left panel: Sentinel-2 L2A "True color" and "False color (urban)" (water is dark blue or black,
  plants red), Sentinel-1 "VV" (water is black). Move the dates a few days around the pass to see clouds come and go
  and the river move.
- **OpenStreetMap** at the place, to see the community, the channels and the paths around it.
- The NISAR images of the pass are in the cache, under `runs/<area>/` (`radar.webp`, `water.png`).

How to decide:

1. Find the culprit place (the case's location) on the Sentinel-2 true colour image of the reference date.
2. Clouds or haze over it, or a cloud shadow: the reference may be wrong; look at Sentinel-1 and other clear dates.
3. Green or brown texture (floating plants, grass, forest) where NISAR shows water: the route may be closed by
   plants; NISAR saw the water under them, but it is not a boat route.
4. A pale bank or sandbar: smooth ground that L-band sees dark; the reference is right.
5. A thin dark line of water that Sentinel-2 at 20 m blurs: NISAR may be right.
6. If the community or the place is not visible or the images contradict each other: undecidable.

Every place in the report ends with a verdict ready to paste: copy it into `processing/benchmark/reviews.json`,
fill in the verdict, your initials, the date and a note, and commit it. One verdict covers every pass and community of
the place; the next exam attaches it to each case and counts confirmed and rejected errors:

```json
{"reviews": [
 {"passes": ["2025-11-04_t097D", "2026-08-19_t097D"], "community_ids": ["osm-node-123", "osm-node-456"],
  "verdict": "reference", "cause": "smooth_ground", "reviewer": "initials", "date": "2026-11-12",
  "note": "sandbar across the channel on the Sentinel-2 image of 20 August"}
]}
```

`verdict`: `nisar` (the method was right), `reference` (the reference was right: a confirmed error) or `undecidable`.
`cause` is optional and replaces the cause the rules found. A single case can also be reviewed with `pass` and
`community_id`.

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
- **The references are not the truth either.** Exam 2 reduces the errors of each one by asking several and
  leaving disputed pixels out, but where all of them are wrong in the same way (for example a channel under 30 m that
  none resolves) the exam cannot tell. Only field checks and manual reviews give truth.
- **The cause rules are evidence, not proof**: a pixel near a cloud may still be a real error of the method.
- **Sentinel-2 is a reference, not the truth.** It also misses channels narrower than ~20–40 m, cannot see water
  under forest or floating vegetation, and is up to 2 days away from the pass (the river can move tens of centimetres
  a day in the dry season). Its status is computed with the monitor's own route rule, so it scores the water mask's
  consequences, not the route rule itself.
- **The synthetic scene is idealised**: uniform surfaces, straight channels, assumed backscatter. It catches
  regressions and known weak points (narrow channels, mud, vegetation, wind) but its numbers do not transfer to Tefé.
- Sanity checks and the gauge correlation cannot tell which community is wrong, only whether the record is coherent.
- NISAR data are provisional: a future reprocessing changes the inputs, and the exam version must change with them.
