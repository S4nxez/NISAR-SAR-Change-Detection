# Benchmark: v2-swath-edge-margin

Exam version 2 · 2026-11-12T14:08:15Z · commit `99bfc68`

## Scorecard

| Metric | Value | Meaning |
|---|---|---|
| Synthetic correct | 0.800 | share of lane results that are right (higher is better) |
| Synthetic dangerous | 5 | lane results showing a route that does not exist or is too narrow |
| Water IoU vs reference | 0.931 | agreement of the water mask with the reference: Sentinel-2 in exam 1, the consensus of the references from exam 2 (higher is better) |
| Narrow recall | 0.410 | share of reference channels under 60 m mapped as water |
| False water at shore | 0.082 | share of shoreline land mapped as water (lower is better) |
| Status agreement | 0.955 | community status equal to the one from the reference water |
| False routes | 6 | community shown with a route the reference water does not have (lower is better; not yet checked by a person) |
| False isolated | 14 | community shown isolated while the reference water links it |
| Gauge rho | -0.773 | rank correlation of lost routes with the river level (more negative is better) |
| Field checks | 1.000 | share of field and report checks the record gets right |
| Undecided | 85 | community-pass pairs the references cannot decide (exam 2), left unscored |
| To review | 16 | disagreements a person has to check (exam 2; see Manual review in the report) |
| Confirmed false routes | 0 | false routes a person confirmed in processing/benchmark/reviews.json (exam 2) |

## Synthetic scenes

5 speckle draws with 9 looks. Expected status per lane and how often each grade came out.

| Lane | Expected | Correct | Conservative | Dangerous | No data |
|---|---|---|---|---|---|
| channel_20m | narrow | 5 | 0 | 0 | 0 |
| channel_40m | narrow | 5 | 0 | 0 | 0 |
| channel_60m | connected | 5 | 0 | 0 | 0 |
| channel_100m | connected | 5 | 0 | 0 | 0 |
| channel_200m | connected | 5 | 0 | 0 | 0 |
| zigzag_100m | connected | 5 | 0 | 0 | 0 |
| vegetation_block | isolated | 5 | 0 | 0 | 0 |
| mud_bar | isolated | 0 | 0 | 5 | 0 |
| wind_stretch | connected | 0 | 5 | 0 | 0 |
| channel_400m | connected | 5 | 0 | 0 | 0 |

| Surface | HH / HV (dB) | Mapped as water | Mapped as vegetated water |
|---|---|---|---|
| forest | -7 / -12.5 | 0.012 | 0.000 |
| water | -23 / -30 | 0.999 | 0.000 |
| wind | -13 / -26 | 0.016 | 0.000 |
| flooded_vegetation | -1 / -9.5 | 0.000 | 0.972 |
| mud | -17 / -27 | 0.996 | 0.000 |

## Real passes against the reference consensus

Anchor: the clearest Sentinel-2 L2A date within 2 days of the pass, at least 30% of the area clear (7 passes). Other references: dswx_hls (within 2 days), dswx_s1 (within 3 days). A pixel is reference water or land when the sources that can see it agree, and disputed (not scored) when they do not; optical "not water" under wetlands and mangroves is not trusted.

| IoU | F1 | Precision | Recall | Recall < 60 m | Recall 60-200 m | Recall >= 200 m | False water shore | False water far | IoU vs Sentinel-2 only |
|---|---|---|---|---|---|---|---|---|---|
| 0.931 | 0.965 | 0.961 | 0.968 | 0.410 | 0.859 | 0.988 | 0.082 | 0.002 | 0.922 |

Community status against the status the monitor's own route rule gives on the consensus water (740 decided community-pass pairs; inland places left out). Undecided: the status changes depending on whether the disputed pixels are water or land.

| Agreement | Mean kappa | False routes | Overconfident | False isolated | Undecided |
|---|---|---|---|---|---|
| 0.955 | 0.898 | 6 | 12 | 14 | 85 |

How often each source agrees with the consensus where it votes (a source that often disagrees is less trustworthy over this area):

| Source | Family | Passes | Votes (km²) | Agrees |
|---|---|---|---|---|
| sentinel2 | optical | 7 | 42884.540 | 0.996 |
| dswx_hls | optical | 7 | 36643.000 | 0.994 |
| dswx_s1 | sar | 3 | 19103.300 | 0.994 |

| Pass | Sentinel-2 | DSWx-HLS | DSWx-S1 | Disputed km² | Both families | Level change cm | IoU | Agreement | False routes | Undecided | Cases |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2025-11-04_t097D | 2025-11-05 | 2025-11-06 | 2025-11-04 | 45.525 | 0.438 | -7.000 | 0.932 | 0.975 | 3 | 12 | 3 |
| 2026-07-07_t161A | 2026-07-06 | 2026-07-06 | – | 45.798 | 0.000 | -2.000 | 0.956 | 1.000 | 0 | 9 | 0 |
| 2026-08-19_t097D | 2026-08-20 | 2026-08-20 | – | 19.625 | 0.000 | 17.500 | 0.948 | 0.868 | 0 | 1 | 12 |
| 2026-08-24_t161A | 2026-08-25 | 2026-08-25 | – | 25.978 | 0.000 | 14.500 | 0.943 | 0.990 | 0 | 16 | 1 |
| 2026-08-31_t097D | 2026-08-30 | 2026-08-30 | – | 29.106 | 0.000 | -23.000 | 0.935 | 0.975 | 0 | 13 | 4 |
| 2026-10-11_t161A | 2026-10-11 | 2026-10-09 | 2026-10-08 | 39.169 | 0.625 | 0.000 | 0.903 | 1.000 | 0 | 26 | 0 |
| 2026-10-23_t161A | 2026-10-21 | 2026-10-25 | 2026-10-20 | 40.498 | 0.554 | -14.000 | 0.894 | 0.891 | 3 | 8 | 13 |

## Disagreements and probable causes

Every pixel where the water mask and the consensus disagree gets the first cause whose rule it meets (commission: NISAR water on reference land; omission: reference water NISAR misses). The rules are evidence, not proof.

| Cause | Family | Commission km² | Omission km² | Meaning |
|---|---|---|---|---|
| cloud_edge | reference | 118.190 | 63.800 | near a cloud or cloud shadow of the Sentinel-2 scene: the optical reference may be wrong |
| shore_mixed_pixel | resolution | 26.760 | 40.770 | within one pixel of the shore: a 20 m pixel holds both water and land |
| threshold | processing | 36.480 | 3.920 | backscatter within the margin of the water threshold: a small change of threshold flips it |
| river_level_change | timing | 12.520 | 24.890 | seasonal ground, and the river level changed between the pass and the reference date |
| narrow_channel | resolution | 0.000 | 18.250 | reference channel narrower than 60 m |
| vegetation | radar_physics | 0.000 | 13.150 | plants on the water (NISAR vegetated class, DSWx-S1 inundated vegetation or a WorldCover wetland): L-band double bounce, not open water |
| smooth_ground | radar_physics | 6.410 | 0.000 | seasonal ground (bank, mud, sand) clearly dark in L-band |
| unexplained | unexplained | 3.510 | 1.980 | no rule explains it |
| swath_edge | processing | 4.810 | 0.140 | near the edge of the NISAR swath or a data gap |
| wind_roughness | radar_physics | 0.000 | 0.620 | permanent water clearly brighter than the threshold: wind or rain roughens it |

| Family | Commission km² | Omission km² | Meaning |
|---|---|---|---|
| reference | 118.190 | 63.800 | the reference itself may be wrong |
| timing | 12.520 | 24.890 | the river changed between the pass and the reference |
| processing | 41.290 | 4.060 | a step of our processing |
| resolution | 26.760 | 59.020 | the 20 m grid cannot resolve it |
| radar_physics | 6.410 | 13.770 | L-band radar sees the surface differently from optical sensors |
| unexplained | 3.510 | 1.980 | no rule explains it |

Cases: communities whose status differs from the decided reference. The culprit pixels are the fewest disputed pixels a route crosses between the hub and the community.

| Pass | Community | Kind | NISAR | Reference | Cause | Family | Culprit px | Lon, lat | Review | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| 2025-11-04_t097D | Boca do Mamiraua | false_route | at_risk | isolated | cloud_edge | reference | 3 | -64.77919, -3.12731 | yes | – |
| 2025-11-04_t097D | São Jose | false_route | at_risk | isolated | cloud_edge | reference | 3 | -64.77919, -3.12731 | yes | – |
| 2025-11-04_t097D | São Jose do Tuiuca | false_route | connected | isolated | cloud_edge | reference | 3 | -65.03623, -3.66155 | yes | – |
| 2026-08-19_t097D | Acapu | false_isolated | isolated | at_risk | narrow_channel | resolution | 6 | -64.41757, -3.52583 | no | – |
| 2026-08-19_t097D | Barreirinha | false_isolated | isolated | at_risk | narrow_channel | resolution | 6 | -64.41757, -3.52583 | no | – |
| 2026-08-19_t097D | Cacai | false_isolated | isolated | at_risk | narrow_channel | resolution | 6 | -64.41757, -3.52583 | no | – |
| 2026-08-19_t097D | Cairara | false_isolated | isolated | at_risk | narrow_channel | resolution | 6 | -64.41757, -3.52583 | no | – |
| 2026-08-19_t097D | Feliciana | false_isolated | isolated | at_risk | narrow_channel | resolution | 6 | -64.41757, -3.52583 | no | – |
| 2026-08-19_t097D | Jaguarí | false_isolated | isolated | at_risk | shore_mixed_pixel | resolution | 37 | -64.88107, -3.09671 | no | – |
| 2026-08-19_t097D | Macedo | false_isolated | isolated | at_risk | narrow_channel | resolution | 6 | -64.41757, -3.52583 | no | – |
| 2026-08-19_t097D | Marajo | false_isolated | isolated | at_risk | narrow_channel | resolution | 6 | -64.41757, -3.52583 | no | – |
| 2026-08-19_t097D | Miriti | false_isolated | isolated | at_risk | narrow_channel | resolution | 7 | -64.43413, -3.54239 | no | – |
| 2026-08-19_t097D | Moura | false_isolated | isolated | at_risk | narrow_channel | resolution | 6 | -64.41757, -3.52583 | no | – |
| 2026-08-19_t097D | São Jose | false_isolated | isolated | at_risk | shore_mixed_pixel | resolution | 1 | -64.84111, -3.05567 | no | – |
| 2026-08-19_t097D | Uirapuru | false_isolated | isolated | at_risk | narrow_channel | resolution | 6 | -64.41757, -3.52583 | no | – |
| 2026-08-24_t161A | Jaguarí | false_isolated | isolated | at_risk | narrow_channel | resolution | 20 | -64.88233, -3.09761 | no | – |
| 2026-08-31_t097D | Alencar | overconfident | connected | at_risk | narrow_channel | resolution | 6 | -64.79845, -3.12803 | no | – |
| 2026-08-31_t097D | Canaman | overconfident | connected | at_risk | narrow_channel | resolution | 3 | -64.80745, -3.41711 | no | – |
| 2026-08-31_t097D | Caru | underconfident | at_risk | connected | narrow_channel | resolution | 2 | -64.98313, -3.56543 | no | – |
| 2026-08-31_t097D | Jaguarí | false_isolated | isolated | at_risk | river_level_change | timing | 40 | -64.88071, -3.09653 | no | – |
| 2026-10-23_t161A | Abacatal | overconfident | connected | at_risk | cloud_edge | reference | 21 | -64.53691, -3.17987 | yes | – |
| 2026-10-23_t161A | Boca do Atapi | overconfident | connected | at_risk | cloud_edge | reference | 13 | -64.56841, -3.17807 | yes | – |
| 2026-10-23_t161A | Canaman | false_route | at_risk | isolated | cloud_edge | reference | 20 | -64.80673, -3.41369 | yes | – |
| 2026-10-23_t161A | Cardoso | overconfident | connected | at_risk | cloud_edge | reference | 13 | -64.56841, -3.17807 | yes | – |
| 2026-10-23_t161A | Girassol | overconfident | connected | at_risk | cloud_edge | reference | 21 | -64.53691, -3.17987 | yes | – |
| 2026-10-23_t161A | Liocadio | overconfident | connected | at_risk | cloud_edge | reference | 17 | -64.55509, -3.17447 | yes | – |
| 2026-10-23_t161A | Mangueal | overconfident | connected | at_risk | cloud_edge | reference | 18 | -64.55023, -3.17573 | yes | – |
| 2026-10-23_t161A | Monte Sinai | overconfident | connected | at_risk | cloud_edge | reference | 11 | -64.57111, -3.18059 | yes | – |
| 2026-10-23_t161A | Nazaré | overconfident | connected | at_risk | cloud_edge | reference | 15 | -64.56193, -3.17447 | yes | – |
| 2026-10-23_t161A | Nova Esperança | false_route | connected | isolated | cloud_edge | reference | 32 | -64.88359, -3.47057 | yes | – |
| 2026-10-23_t161A | Renascer | overconfident | connected | at_risk | cloud_edge | reference | 22 | -64.53313, -3.18167 | yes | – |
| 2026-10-23_t161A | São Jose do Madureira | false_route | connected | isolated | cloud_edge | reference | 29 | -64.80097, -3.41243 | yes | – |
| 2026-10-23_t161A | Urcui | overconfident | connected | at_risk | cloud_edge | reference | 23 | -64.53025, -3.18311 | yes | – |

| Kind | Cases | Confirmed | Rejected | Undecidable | Pending |
|---|---|---|---|---|---|
| false_route | 6 | 0 | 0 | 0 | 6 |
| false_isolated | 14 | 0 | 0 | 0 | 14 |
| overconfident | 12 | 0 | 0 | 0 | 12 |
| underconfident | 1 | 0 | 0 | 0 | 1 |

## Manual review

16 cases need a person (every false route, the dangerous error, and every case whose cause says the reference may be wrong, points at our processing or is unexplained). They come from 6 places, each named after the nearest community. How to check a place: docs/river-monitor-benchmark.md, "Manual review"; one verdict covers every community and pass of the place.

### 1. Near Monte Sinai: route wider than the reference's

- Where: 1.4 km from Monte Sinai (-64.56253, -3.1769); the links open the map on that point.
- Probable cause: `cloud_edge` (reference): near a cloud or cloud shadow of the Sentinel-2 scene: the optical reference may be wrong
- Communities: Boca do Atapi, Cardoso, Liocadio, Mangueal, Monte Sinai, Nazaré
- Passes (6 cases): 2026-10-23_t161A
  - 2026-10-23_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.17447&lng=-64.56193&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-10-21T00%3A00%3A00.000Z&toTime=2026-10-21T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.17447&mlon=-64.56193#map=15/-3.17447/-64.56193) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.17447&lng=-64.56193&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-10-20T00%3A00%3A00.000Z&toTime=2026-10-20T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/reviews.json`:

```json
{"passes": ["2026-10-23_t161A"], "community_ids": ["osm3924302373", "osm3924302377", "osm3924302381", "osm3924302382", "osm3924302383", "osm416757398"], "verdict": "nisar | reference | undecidable", "cause": "cloud_edge", "reviewer": "", "date": "", "note": ""}
```

### 2. Near Nazaré: route wider than the reference's

- Where: 0.9 km from Nazaré (-64.5343, -3.18113); the links open the map on that point.
- Probable cause: `cloud_edge` (reference): near a cloud or cloud shadow of the Sentinel-2 scene: the optical reference may be wrong
- Communities: Abacatal, Girassol, Renascer, Urcui
- Passes (4 cases): 2026-10-23_t161A
  - 2026-10-23_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.18311&lng=-64.53025&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-10-21T00%3A00%3A00.000Z&toTime=2026-10-21T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.18311&mlon=-64.53025#map=15/-3.18311/-64.53025) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.18311&lng=-64.53025&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-10-20T00%3A00%3A00.000Z&toTime=2026-10-20T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/reviews.json`:

```json
{"passes": ["2026-10-23_t161A"], "community_ids": ["osm3924302370", "osm3924302379", "osm3924302387", "osm3924302396"], "verdict": "nisar | reference | undecidable", "cause": "cloud_edge", "reviewer": "", "date": "", "note": ""}
```

### 3. Near Nova Jerusalem: route the reference does not have; route wider than the reference's

- Where: 0.5 km from Nova Jerusalem (-64.80505, -3.41441); the links open the map on that point.
- Probable cause: `cloud_edge` (reference): near a cloud or cloud shadow of the Sentinel-2 scene: the optical reference may be wrong
- Communities: Canaman, São Jose do Madureira
- Passes (3 cases): 2026-08-31_t097D, 2026-10-23_t161A
  - 2026-10-23_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.41243&lng=-64.80097&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-10-21T00%3A00%3A00.000Z&toTime=2026-10-21T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.41243&mlon=-64.80097#map=15/-3.41243/-64.80097) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.41243&lng=-64.80097&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-10-20T00%3A00%3A00.000Z&toTime=2026-10-20T23%3A59%3A59.999Z)
  - 2026-08-31_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.41711&lng=-64.80745&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-08-30T00%3A00%3A00.000Z&toTime=2026-08-30T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.41711&mlon=-64.80745#map=15/-3.41711/-64.80745)
- Verdict to add to `processing/benchmark/reviews.json`:

```json
{"passes": ["2026-08-31_t097D", "2026-10-23_t161A"], "community_ids": ["osm3986860562", "osm3986860636"], "verdict": "nisar | reference | undecidable", "cause": "cloud_edge", "reviewer": "", "date": "", "note": ""}
```

### 4. Near Boca do Mamiraua: route the reference does not have

- Where: 1.9 km from Boca do Mamiraua (-64.77919, -3.12731); the links open the map on that point.
- Probable cause: `cloud_edge` (reference): near a cloud or cloud shadow of the Sentinel-2 scene: the optical reference may be wrong
- Communities: Boca do Mamiraua, São Jose
- Passes (2 cases): 2025-11-04_t097D
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.12731&lng=-64.77919&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.12731&mlon=-64.77919#map=15/-3.12731/-64.77919) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.12731&lng=-64.77919&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/reviews.json`:

```json
{"passes": ["2025-11-04_t097D"], "community_ids": ["osm3984711997", "osm3984712031"], "verdict": "nisar | reference | undecidable", "cause": "cloud_edge", "reviewer": "", "date": "", "note": ""}
```

### 5. Near São Jose do Tuiuca: route the reference does not have

- Where: 1.2 km from São Jose do Tuiuca (-65.03623, -3.66155); the links open the map on that point.
- Probable cause: `cloud_edge` (reference): near a cloud or cloud shadow of the Sentinel-2 scene: the optical reference may be wrong
- Communities: São Jose do Tuiuca
- Passes (1 cases): 2025-11-04_t097D
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.66155&lng=-65.03623&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.66155&mlon=-65.03623#map=15/-3.66155/-65.03623) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.66155&lng=-65.03623&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/reviews.json`:

```json
{"passes": ["2025-11-04_t097D"], "community_ids": ["osm3984833652"], "verdict": "nisar | reference | undecidable", "cause": "cloud_edge", "reviewer": "", "date": "", "note": ""}
```

### 6. Near Nova Esperança: route the reference does not have

- Where: 1.4 km from Nova Esperança (-64.88359, -3.47057); the links open the map on that point.
- Probable cause: `cloud_edge` (reference): near a cloud or cloud shadow of the Sentinel-2 scene: the optical reference may be wrong
- Communities: Nova Esperança
- Passes (1 cases): 2026-10-23_t161A
  - 2026-10-23_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.47057&lng=-64.88359&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-10-21T00%3A00%3A00.000Z&toTime=2026-10-21T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.47057&mlon=-64.88359#map=15/-3.47057/-64.88359) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.47057&lng=-64.88359&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-10-20T00%3A00%3A00.000Z&toTime=2026-10-20T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/reviews.json`:

```json
{"passes": ["2026-10-23_t161A"], "community_ids": ["osm8583554431"], "verdict": "nisar | reference | undecidable", "cause": "cloud_edge", "reviewer": "", "date": "", "note": ""}
```

Other places with disagreements (cause known, no review needed):

| Near | Kinds | Cause | Communities | Passes |
|---|---|---|---|---|
| Boca do Mamiraua | overconfident | narrow_channel | Alencar | 2026-08-31_t097D |
| Caiambé | false_isolated | narrow_channel | Acapu, Barreirinha, Cacai, Cairara, Feliciana, Macedo, Marajo, Moura, Uirapuru | 2026-08-19_t097D |
| Jaquiri | false_isolated | river_level_change | Jaguarí | 2026-08-19_t097D, 2026-08-24_t161A, 2026-08-31_t097D |
| Uirapuru | false_isolated | narrow_channel | Miriti | 2026-08-19_t097D |
| São Jose | false_isolated | shore_mixed_pixel | São Jose | 2026-08-19_t097D |
| São João do Mulato | underconfident | narrow_channel | Caru | 2026-08-31_t097D |

## River gauge

ANA telemetry, station 12900001.

| Correlation | Spearman rho | Passes | Expected sign |
|---|---|---|---|
| water area vs level | 0.968 | 15 | + |
| lost routes vs level | -0.773 | 15 | - |

## Field and report checks

| Community | Expected | Kind | Found | Passes judged | Correct | Source |
|---|---|---|---|---|---|---|
| Caiambé | linked | sanity | True | 14 | 14 | Team plausibility check (docs/river-monitor.md): settlement on the Solimões main channel, used as the boat landing in the 2023 and 2024 droughts. Not an observation of 2026. |
| Alvarães | linked | sanity | True | 14 | 14 | Team plausibility check (docs/river-monitor.md): municipal seat reached through its port; no 2026 report of the town being cut off was found. Not an observation of 2026. |

## Community classes

| monitored | unresolved | inland | no_data |
|---|---|---|---|
| 130 | 39 | 35 | 0 |
