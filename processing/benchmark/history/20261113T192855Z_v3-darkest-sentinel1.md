# Benchmark: v3-darkest-sentinel1

Exam version 3 · 2026-11-13T19:28:55Z · commit `7a3d95e`

## Scorecard

| Metric | Value | Meaning |
|---|---|---|
| Synthetic correct | 0.800 | share of lane results that are right (higher is better) |
| Synthetic dangerous | 5 | lane results showing a route that does not exist or is too narrow |
| Water IoU vs reference | 0.929 | agreement of the water mask with the reference: Sentinel-2 in exam 1, the consensus of the references from exam 2 (higher is better) |
| Narrow recall | 0.388 | share of reference channels under 60 m mapped as water |
| False water at shore | 0.074 | share of shoreline land mapped as water (lower is better) |
| Status agreement | 0.957 | community status equal to the one from the reference water |
| False routes | 1 | community shown with a route the reference water does not have (lower is better; not yet checked by a person) |
| False isolated | 14 | community shown isolated while the reference water links it |
| Gauge rho | -0.757 | rank correlation of lost routes with the river level (more negative is better) |
| Field checks | 1.000 | share of field and report checks the record gets right |
| Undecided | 47 | community-pass pairs the references cannot decide (exam 2), left unscored |
| To review | 2 | disagreements a person has to check (exam 2; see Manual review in the report) |
| Confirmed false routes | 0 | false routes a person confirmed in processing/benchmark/reviews.json (exam 2) |
| NISAR-S1 agreement | 0.985 | share of the pixels both radars judged on which NISAR and Sentinel-1 agree (exam 3, not scored) |
| NISAR-S1 places | 62 | places where the two radars give a community different statuses, to check by hand (exam 3) |

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

Anchor: the clearest Sentinel-2 L2A date within 2 days of the pass, at least 30% of the area clear (7 passes). Other references: dswx_hls (within 2 days). A pixel is reference water or land when the sources that can see it agree, and disputed (not scored) when they do not; optical "not water" under wetlands and mangroves is not trusted.

| IoU | F1 | Precision | Recall | Recall < 60 m | Recall 60-200 m | Recall >= 200 m | False water shore | False water far | IoU vs Sentinel-2 only |
|---|---|---|---|---|---|---|---|---|---|
| 0.929 | 0.963 | 0.961 | 0.966 | 0.388 | 0.856 | 0.987 | 0.074 | 0.002 | 0.922 |

Community status against the status the monitor's own route rule gives on the consensus water (463 decided community-pass pairs; inland places left out). Undecided: the status changes depending on whether the disputed pixels are water or land.

| Agreement | Mean kappa | False routes | Overconfident | False isolated | Undecided |
|---|---|---|---|---|---|
| 0.957 | 0.910 | 1 | 3 | 14 | 47 |

How often each source agrees with the consensus where it votes (a source that often disagrees is less trustworthy over this area):

| Source | Family | Passes | Votes (km²) | Agrees |
|---|---|---|---|---|
| sentinel2 | optical | 7 | 42884.540 | 0.997 |
| dswx_hls | optical | 7 | 36643.000 | 0.996 |

| Pass | Sentinel-2 | DSWx-HLS | DSWx-S1 | Disputed km² | Both families | Level change cm | IoU | Agreement | False routes | Undecided | Cases |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2025-11-04_t097D | 2025-11-05 | 2025-11-06 | – | 5.361 | 0.000 | -7.000 | 0.924 | 1.000 | 0 | 7 | 0 |
| 2026-07-07_t161A | 2026-07-06 | 2026-07-06 | – | 45.798 | 0.000 | -2.000 | 0.956 | 1.000 | 0 | 9 | 0 |
| 2026-08-19_t097D | 2026-08-20 | 2026-08-20 | – | 19.625 | 0.000 | 17.500 | 0.948 | 0.868 | 0 | 1 | 12 |
| 2026-08-24_t161A | 2026-08-25 | 2026-08-25 | – | 25.978 | 0.000 | 14.500 | 0.943 | 0.990 | 0 | 16 | 1 |
| 2026-08-31_t097D | 2026-08-30 | 2026-08-30 | – | 29.106 | 0.000 | -23.000 | 0.935 | 0.975 | 0 | 13 | 4 |
| 2026-10-11_t161A | 2026-10-11 | 2026-10-09 | – | 5.699 | 0.000 | 0.000 | 0.899 | 0.919 | 1 | 1 | 3 |
| 2026-10-23_t161A | 2026-10-21 | 2026-10-25 | – | 5.925 | 0.000 | -14.000 | 0.836 | 1.000 | 0 | 0 | 0 |

## Disagreements and probable causes

Every pixel where the water mask and the consensus disagree gets the first cause whose rule it meets (commission: NISAR water on reference land; omission: reference water NISAR misses). The rules are evidence, not proof.

| Cause | Family | Commission km² | Omission km² | Meaning |
|---|---|---|---|---|
| cloud_edge | reference | 98.530 | 56.850 | near a cloud or cloud shadow of the Sentinel-2 scene: the optical reference may be wrong |
| shore_mixed_pixel | resolution | 29.600 | 42.550 | within one pixel of the shore: a 20 m pixel holds both water and land |
| river_level_change | timing | 12.520 | 24.890 | seasonal ground, and the river level changed between the pass and the reference date |
| threshold | processing | 30.740 | 4.140 | backscatter within the margin of the water threshold: a small change of threshold flips it |
| narrow_channel | resolution | 0.000 | 18.730 | reference channel narrower than 60 m |
| vegetation | radar_physics | 0.000 | 14.020 | plants on the water (NISAR vegetated class, DSWx-S1 inundated vegetation or a WorldCover wetland): L-band double bounce, not open water |
| unexplained | unexplained | 4.350 | 2.300 | no rule explains it |
| smooth_ground | radar_physics | 6.290 | 0.000 | seasonal ground (bank, mud, sand) clearly dark in L-band |
| swath_edge | processing | 4.810 | 0.140 | near the edge of the NISAR swath or a data gap |
| wind_roughness | radar_physics | 0.000 | 0.730 | permanent water clearly brighter than the threshold: wind or rain roughens it |

| Family | Commission km² | Omission km² | Meaning |
|---|---|---|---|
| reference | 98.530 | 56.850 | the reference itself may be wrong |
| timing | 12.520 | 24.890 | the river changed between the pass and the reference |
| processing | 35.550 | 4.280 | a step of our processing |
| resolution | 29.600 | 61.280 | the 20 m grid cannot resolve it |
| radar_physics | 6.290 | 14.760 | L-band radar sees the surface differently from optical sensors |
| unexplained | 4.350 | 2.300 | no rule explains it |

Cases: communities whose status differs from the decided reference. The culprit pixels are the fewest disputed pixels a route crosses between the hub and the community.

| Pass | Community | Kind | NISAR | Reference | Cause | Family | Culprit px | Lon, lat | Review | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-08-19_t097D | Acapu | false_isolated | isolated | at_risk | narrow_channel | resolution | 6 | -64.41757, -3.52583 | no | – |
| 2026-08-19_t097D | Barreirinha | false_isolated | isolated | at_risk | narrow_channel | resolution | 6 | -64.41757, -3.52583 | no | – |
| 2026-08-19_t097D | Cacai | false_isolated | isolated | at_risk | narrow_channel | resolution | 6 | -64.41757, -3.52583 | no | – |
| 2026-08-19_t097D | Cairara | false_isolated | isolated | at_risk | narrow_channel | resolution | 6 | -64.41757, -3.52583 | no | – |
| 2026-08-19_t097D | Feliciana | false_isolated | isolated | at_risk | narrow_channel | resolution | 6 | -64.41757, -3.52583 | no | – |
| 2026-08-19_t097D | Jaguarí | false_isolated | isolated | at_risk | shore_mixed_pixel | resolution | 37 | -64.88143, -3.09635 | no | – |
| 2026-08-19_t097D | Macedo | false_isolated | isolated | at_risk | narrow_channel | resolution | 6 | -64.41757, -3.52583 | no | – |
| 2026-08-19_t097D | Marajo | false_isolated | isolated | at_risk | narrow_channel | resolution | 6 | -64.41757, -3.52583 | no | – |
| 2026-08-19_t097D | Miriti | false_isolated | isolated | at_risk | narrow_channel | resolution | 7 | -64.41793, -3.52601 | no | – |
| 2026-08-19_t097D | Moura | false_isolated | isolated | at_risk | narrow_channel | resolution | 6 | -64.41757, -3.52583 | no | – |
| 2026-08-19_t097D | São Jose | false_isolated | isolated | at_risk | shore_mixed_pixel | resolution | 1 | -64.84111, -3.05567 | no | – |
| 2026-08-19_t097D | Uirapuru | false_isolated | isolated | at_risk | narrow_channel | resolution | 6 | -64.41757, -3.52583 | no | – |
| 2026-08-24_t161A | Jaguarí | false_isolated | isolated | at_risk | narrow_channel | resolution | 20 | -64.88251, -3.09743 | no | – |
| 2026-08-31_t097D | Alencar | overconfident | connected | at_risk | narrow_channel | resolution | 6 | -64.79845, -3.12803 | no | – |
| 2026-08-31_t097D | Canaman | overconfident | connected | at_risk | narrow_channel | resolution | 3 | -64.80745, -3.41711 | no | nisar |
| 2026-08-31_t097D | Caru | underconfident | at_risk | connected | narrow_channel | resolution | 2 | -64.98295, -3.56417 | no | – |
| 2026-08-31_t097D | Jaguarí | false_isolated | isolated | at_risk | river_level_change | timing | 40 | -64.88125, -3.09617 | no | – |
| 2026-10-11_t161A | Canaman | false_route | at_risk | isolated | cloud_edge | reference | 3 | -64.80781, -3.41711 | yes | – |
| 2026-10-11_t161A | Nova Esperança | underconfident | at_risk | connected | sentinel1_mud | radar_physics | 2 | -64.88215, -3.47435 | no | reference |
| 2026-10-11_t161A | São Jose do Madureira | overconfident | connected | at_risk | cloud_edge | reference | 22 | -64.79755, -3.41459 | yes | – |

| Kind | Cases | Confirmed | Rejected | Undecidable | Pending |
|---|---|---|---|---|---|
| false_isolated | 14 | 0 | 0 | 0 | 14 |
| overconfident | 3 | 0 | 1 | 0 | 2 |
| underconfident | 2 | 1 | 0 | 0 | 1 |
| false_route | 1 | 0 | 0 | 0 | 1 |

## Manual review

2 cases need a person (every false route, the dangerous error, and every case whose cause says the reference may be wrong, points at our processing or is unexplained). They come from 1 places, each named after the nearest community. How to check a place: docs/river-monitor-benchmark.md, "Manual review"; one verdict covers every community and pass of the place.

### 1. Near Nova Jerusalem: route the reference does not have; route wider than the reference's

- Where: 0.4 km from Nova Jerusalem (-64.80427, -3.41627); the links open the map on that point.
- Probable cause: `cloud_edge` (reference): near a cloud or cloud shadow of the Sentinel-2 scene: the optical reference may be wrong
- Communities: Canaman, São Jose do Madureira
- Passes (3 cases): 2026-08-31_t097D, 2026-10-11_t161A
  - 2026-10-11_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.41459&lng=-64.79755&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-10-11T00%3A00%3A00.000Z&toTime=2026-10-11T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.41459&mlon=-64.79755#map=15/-3.41459/-64.79755) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.41459&lng=-64.79755&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-10-13T00%3A00%3A00.000Z&toTime=2026-10-13T23%3A59%3A59.999Z)
  - 2026-08-31_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.41711&lng=-64.80745&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-08-30T00%3A00%3A00.000Z&toTime=2026-08-30T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.41711&mlon=-64.80745#map=15/-3.41711/-64.80745) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.41711&lng=-64.80745&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-09-02T00%3A00%3A00.000Z&toTime=2026-09-02T23%3A59%3A59.999Z)
- Reviewed: nisar
- Verdict to add to `processing/benchmark/reviews.json`:

```json
{"passes": ["2026-08-31_t097D", "2026-10-11_t161A"], "community_ids": ["osm3986860562", "osm3986860636"], "verdict": "nisar | reference | undecidable", "cause": "cloud_edge", "reviewer": "", "date": "", "note": ""}
```

Other places with disagreements (cause known, no review needed):

| Near | Kinds | Cause | Communities | Passes |
|---|---|---|---|---|
| Boca do Mamiraua | overconfident | narrow_channel | Alencar | 2026-08-31_t097D |
| Caiambé | false_isolated | narrow_channel | Acapu, Barreirinha, Cacai, Cairara, Feliciana, Macedo, Marajo, Miriti, Moura, Uirapuru | 2026-08-19_t097D |
| Jaquiri | false_isolated | river_level_change | Jaguarí | 2026-08-19_t097D, 2026-08-24_t161A, 2026-08-31_t097D |
| São Jose | false_isolated | shore_mixed_pixel | São Jose | 2026-08-19_t097D |
| São João do Mulato | underconfident | narrow_channel | Caru | 2026-08-31_t097D |
| Nova Esperança | underconfident | sentinel1_mud | Nova Esperança | 2026-10-11_t161A |

## NISAR and Sentinel-1 (not scored)

Sentinel-1 is part of the method (ADR-007), so it is not a reference of the exam. Here the two radars check each other: where both see water or both see land the result is confirmed by two satellites; the places where they give a community different statuses are listed for a person to check. The verdicts (processing/benchmark/crosscheck_reviews.json) count per zone type and tell which radar to trust where.

| Passes | Judged km² | Agreement | NISAR-only water km² | Sentinel-1-only water km² | Mud left out of routes km² | Status cases | Places |
|---|---|---|---|---|---|---|---|
| 6 | 43365.700 | 0.985 | 596.000 | 55.300 | 165.600 | 170 | 62 |

| Pass | Sentinel-1 dates | Agreement | Both water km² | NISAR only km² | Sentinel-1 only km² | Mud km² | Status cases |
|---|---|---|---|---|---|---|---|
| 2025-11-04_t097D | 2025-11-04 | 0.966 | 366.210 | 208.040 | 2.200 | 43.250 | 88 |
| 2026-07-07_t161A | 2026-07-09 | 0.986 | 576.270 | 70.930 | 9.440 | 0.000 | 58 |
| 2026-08-24_t161A | 2026-08-26 | 0.992 | 570.450 | 39.050 | 10.480 | 0.000 | 7 |
| 2026-08-31_t097D | 2026-09-02 | 0.993 | 620.450 | 33.980 | 9.020 | 0.000 | 1 |
| 2026-10-11_t161A | 2026-10-13, 2026-10-08 | 0.989 | 740.360 | 93.980 | 14.820 | 53.830 | 5 |
| 2026-10-23_t161A | 2026-10-25, 2026-10-20 | 0.983 | 676.550 | 150.050 | 9.380 | 68.490 | 11 |

Verdicts per zone type (the probable cause of each case):

| Zone | Cases | NISAR right | Sentinel-1 right | Undecidable | Pending |
|---|---|---|---|---|---|
| narrow_channel | 91 | 78 | 0 | 0 | 13 |
| shore_mixed_pixel | 26 | 15 | 0 | 0 | 11 |
| unexplained | 22 | 0 | 0 | 0 | 22 |
| threshold | 17 | 0 | 0 | 0 | 17 |
| wind_roughness | 13 | 13 | 0 | 0 | 0 |
| smooth_ground | 1 | 0 | 0 | 0 | 1 |

Which radar the published status follows in those cases: neither 1, nisar 155, sentinel1 14.

### Places to check (32)

Open both links of a pass: the Sentinel-1 image (10 m, VV/VH) and the Sentinel-2 image of the nearest clear day. A verdict covers every community and pass of the place.

#### 1. Near Santa Clara: NISAR links it, Sentinel-1 does not; NISAR's route is wider

- Where: 0.7 km from Santa Clara (-64.6843, -3.2915)
- Zone: `narrow_channel`: reference channel narrower than 60 m
- Communities: Comunidade São Francisco do Aratamã, Gloria, Santa Clara, Santa Cruz, São Francisco do Piranhal
- Passes (6 cases): 2025-11-04_t097D, 2026-07-07_t161A
  - 2026-07-07_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.30605&lng=-64.69189&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-07-06T00%3A00%3A00.000Z&toTime=2026-07-06T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.30605&mlon=-64.69189#map=15/-3.30605/-64.69189) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.30605&lng=-64.69189&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-07-09T00%3A00%3A00.000Z&toTime=2026-07-09T23%3A59%3A59.999Z)
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.28411&lng=-64.67970&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.28411&mlon=-64.67970#map=15/-3.28411/-64.67970) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.28411&lng=-64.67970&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D", "2026-07-07_t161A"], "community_ids": ["osm3986860573", "osm3986860614", "osm3986860615", "osm3986860632", "osm9755637967"], "verdict": "nisar | sentinel1 | undecidable", "cause": "narrow_channel", "reviewer": "", "date": "", "note": ""}
```

#### 2. Near Vista Alegre: NISAR links it, Sentinel-1 does not

- Where: 2.2 km from Vista Alegre (-64.82896, -3.39998)
- Zone: `shore_mixed_pixel`: within one pixel of the shore: a 20 m pixel holds both water and land
- Communities: Caru, Fe Em Deus, Nova Esperança, São Jose do Tuiuca, São João do Mulato, Tauary
- Passes (6 cases): 2025-11-04_t097D, 2026-10-23_t161A
  - 2026-10-23_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.41153&lng=-64.82797&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-10-21T00%3A00%3A00.000Z&toTime=2026-10-21T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.41153&mlon=-64.82797#map=15/-3.41153/-64.82797) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.41153&lng=-64.82797&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-10-25T00%3A00%3A00.000Z&toTime=2026-10-25T23%3A59%3A59.999Z)
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.39659&lng=-64.82671&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.39659&mlon=-64.82671#map=15/-3.39659/-64.82671) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.39659&lng=-64.82671&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D", "2026-10-23_t161A"], "community_ids": ["osm3984833616", "osm3984833652", "osm3984833655", "osm3986860569", "osm3986860646", "osm8583554431"], "verdict": "nisar | sentinel1 | undecidable", "cause": "shore_mixed_pixel", "reviewer": "", "date": "", "note": ""}
```

#### 3. Near Santa Maria: NISAR links it, Sentinel-1 does not

- Where: 0.6 km from Santa Maria (-64.675, -3.31616)
- Zone: `threshold`: backscatter within the margin of the water threshold: a small change of threshold flips it
- Communities: Boara de Cima, Boara do Meio, Boarazinho, Santa Maria
- Passes (4 cases): 2025-11-04_t097D, 2026-07-07_t161A
  - 2026-07-07_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.31775&lng=-64.67425&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-07-06T00%3A00%3A00.000Z&toTime=2026-07-06T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.31775&mlon=-64.67425#map=15/-3.31775/-64.67425) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.31775&lng=-64.67425&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-07-09T00%3A00%3A00.000Z&toTime=2026-07-09T23%3A59%3A59.999Z)
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.31140&lng=-64.67725&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.31140&mlon=-64.67725#map=15/-3.31140/-64.67725) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.31140&lng=-64.67725&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D", "2026-07-07_t161A"], "community_ids": ["osm3986858853", "osm3986858854", "osm3986860619", "osm9829129139"], "verdict": "nisar | sentinel1 | undecidable", "cause": "threshold", "reviewer": "", "date": "", "note": ""}
```

#### 4. Near São Francisco do Mapitirini: NISAR links it, Sentinel-1 does not

- Where: 0.5 km from São Francisco do Mapitirini (-64.74137, -2.95555)
- Zone: `unexplained`: no rule explains it
- Communities: Belo Horizonte, São Francisco do Mapitirini
- Passes (4 cases): 2025-11-04_t097D, 2026-07-07_t161A
  - 2026-07-07_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-2.95951&lng=-64.73840&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-07-06T00%3A00%3A00.000Z&toTime=2026-07-06T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-2.95951&mlon=-64.73840#map=15/-2.95951/-64.73840) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-2.95951&lng=-64.73840&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-07-09T00%3A00%3A00.000Z&toTime=2026-07-09T23%3A59%3A59.999Z)
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-2.95951&lng=-64.73840&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-2.95951&mlon=-64.73840#map=15/-2.95951/-64.73840) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-2.95951&lng=-64.73840&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D", "2026-07-07_t161A"], "community_ids": ["osm3924267758", "osm3924267817"], "verdict": "nisar | sentinel1 | undecidable", "cause": "unexplained", "reviewer": "", "date": "", "note": ""}
```

#### 5. Near Sitio Luiz: NISAR links it, Sentinel-1 does not

- Where: 0.7 km from Sitio Luiz (-64.67588, -2.989)
- Zone: `unexplained`: no rule explains it
- Communities: Sitio Luiz, São Sebastião
- Passes (4 cases): 2025-11-04_t097D, 2026-07-07_t161A
  - 2026-07-07_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-2.98638&lng=-64.67014&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-07-06T00%3A00%3A00.000Z&toTime=2026-07-06T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-2.98638&mlon=-64.67014#map=15/-2.98638/-64.67014) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-2.98638&lng=-64.67014&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-07-09T00%3A00%3A00.000Z&toTime=2026-07-09T23%3A59%3A59.999Z)
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-2.98638&lng=-64.67014&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-2.98638&mlon=-64.67014#map=15/-2.98638/-64.67014) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-2.98638&lng=-64.67014&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D", "2026-07-07_t161A"], "community_ids": ["osm3924267813", "osm3924267831"], "verdict": "nisar | sentinel1 | undecidable", "cause": "unexplained", "reviewer": "", "date": "", "note": ""}
```

#### 6. Near São Francisco do Bauana: NISAR links it, Sentinel-1 does not

- Where: 0.9 km from São Francisco do Bauana (-64.98722, -3.48277)
- Zone: `threshold`: backscatter within the margin of the water threshold: a small change of threshold flips it
- Communities: Jauarituba, São Francisco do Bauana
- Passes (4 cases): 2025-11-04_t097D, 2026-08-24_t161A
  - 2026-08-24_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.48119&lng=-64.98259&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-08-25T00%3A00%3A00.000Z&toTime=2026-08-25T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.48119&mlon=-64.98259#map=15/-3.48119/-64.98259) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.48119&lng=-64.98259&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-08-26T00%3A00%3A00.000Z&toTime=2026-08-26T23%3A59%3A59.999Z)
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.48227&lng=-64.98133&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.48227&mlon=-64.98133#map=15/-3.48227/-64.98133) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.48227&lng=-64.98133&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D", "2026-08-24_t161A"], "community_ids": ["osm3984833626", "osm3984833648"], "verdict": "nisar | sentinel1 | undecidable", "cause": "threshold", "reviewer": "", "date": "", "note": ""}
```

#### 7. Near Boara do Meio: NISAR links it, Sentinel-1 does not

- Where: 0.1 km from Boara do Meio (-64.63925, -3.35448)
- Zone: `narrow_channel`: reference channel narrower than 60 m
- Communities: Boara de Cima, Boara do Meio, Boarazinho
- Passes (3 cases): 2025-11-04_t097D
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.35927&lng=-64.63600&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.35927&mlon=-64.63600#map=15/-3.35927/-64.63600) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.35927&lng=-64.63600&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D"], "community_ids": ["osm3986858853", "osm3986858854", "osm9829129139"], "verdict": "nisar | sentinel1 | undecidable", "cause": "narrow_channel", "reviewer": "", "date": "", "note": ""}
```

#### 8. Near Boca do Mamiraua: NISAR links it, Sentinel-1 does not

- Where: 1.6 km from Boca do Mamiraua (-64.78111, -3.12647)
- Zone: `narrow_channel`: reference channel narrower than 60 m
- Communities: Alencar, Boca do Mamiraua, São Jose
- Passes (3 cases): 2025-11-04_t097D
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.12623&lng=-64.78171&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.12623&mlon=-64.78171#map=15/-3.12623/-64.78171) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.12623&lng=-64.78171&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D"], "community_ids": ["osm3984711996", "osm3984711997", "osm3984712031"], "verdict": "nisar | sentinel1 | undecidable", "cause": "narrow_channel", "reviewer": "", "date": "", "note": ""}
```

#### 9. Near Alvarães: NISAR links it, Sentinel-1 does not

- Where: 0.3 km from Alvarães (-64.80662, -3.20997)
- Zone: `narrow_channel`: reference channel narrower than 60 m
- Communities: Alvarães, Castanheirinha, Olaria
- Passes (3 cases): 2025-11-04_t097D, 2026-07-07_t161A
  - 2026-07-07_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.20813&lng=-64.81285&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-07-06T00%3A00%3A00.000Z&toTime=2026-07-06T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.20813&mlon=-64.81285#map=15/-3.20813/-64.81285) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.20813&lng=-64.81285&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-07-09T00%3A00%3A00.000Z&toTime=2026-07-09T23%3A59%3A59.999Z)
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.21080&lng=-64.80257&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.21080&mlon=-64.80257#map=15/-3.21080/-64.80257) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.21080&lng=-64.80257&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D", "2026-07-07_t161A"], "community_ids": ["osm3984833617", "osm3984833637", "osm415524054"], "verdict": "nisar | sentinel1 | undecidable", "cause": "narrow_channel", "reviewer": "", "date": "", "note": ""}
```

#### 10. Near Tauary: NISAR links it, Sentinel-1 does not; NISAR's route is wider

- Where: 2.8 km from Tauary (-64.96705, -3.61577)
- Zone: `narrow_channel`: reference channel narrower than 60 m
- Communities: São Jose do Tuiuca, Tauary
- Passes (3 cases): 2026-07-07_t161A, 2026-08-24_t161A
  - 2026-08-24_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.61385&lng=-64.96765&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-08-25T00%3A00%3A00.000Z&toTime=2026-08-25T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.61385&mlon=-64.96765#map=15/-3.61385/-64.96765) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.61385&lng=-64.96765&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-08-26T00%3A00%3A00.000Z&toTime=2026-08-26T23%3A59%3A59.999Z)
  - 2026-07-07_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.62411&lng=-64.96459&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-07-06T00%3A00%3A00.000Z&toTime=2026-07-06T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.62411&mlon=-64.96459#map=15/-3.62411/-64.96459) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.62411&lng=-64.96459&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-07-09T00%3A00%3A00.000Z&toTime=2026-07-09T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2026-07-07_t161A", "2026-08-24_t161A"], "community_ids": ["osm3984833652", "osm3986860646"], "verdict": "nisar | sentinel1 | undecidable", "cause": "narrow_channel", "reviewer": "", "date": "", "note": ""}
```

#### 11. Near Acarazinho: NISAR links it, Sentinel-1 does not

- Where: at Acarazinho (-64.61394, -3.17941)
- Zone: `unexplained`: no rule explains it
- Communities: Acarazinho
- Passes (2 cases): 2025-11-04_t097D, 2026-07-07_t161A
  - 2026-07-07_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.17941&lng=-64.61394&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-07-06T00%3A00%3A00.000Z&toTime=2026-07-06T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.17941&mlon=-64.61394#map=15/-3.17941/-64.61394) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.17941&lng=-64.61394&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-07-09T00%3A00%3A00.000Z&toTime=2026-07-09T23%3A59%3A59.999Z)
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.17941&lng=-64.61394&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.17941&mlon=-64.61394#map=15/-3.17941/-64.61394) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.17941&lng=-64.61394&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D", "2026-07-07_t161A"], "community_ids": ["osm3924302372"], "verdict": "nisar | sentinel1 | undecidable", "cause": "unexplained", "reviewer": "", "date": "", "note": ""}
```

#### 12. Near Cupuacu: NISAR links it, Sentinel-1 does not

- Where: at Cupuacu (-64.6956, -2.98229)
- Zone: `unexplained`: no rule explains it
- Communities: Cupuacu
- Passes (2 cases): 2025-11-04_t097D, 2026-07-07_t161A
  - 2026-07-07_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-2.98229&lng=-64.69560&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-07-06T00%3A00%3A00.000Z&toTime=2026-07-06T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-2.98229&mlon=-64.69560#map=15/-2.98229/-64.69560) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-2.98229&lng=-64.69560&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-07-09T00%3A00%3A00.000Z&toTime=2026-07-09T23%3A59%3A59.999Z)
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-2.98229&lng=-64.69560&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-2.98229&mlon=-64.69560#map=15/-2.98229/-64.69560) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-2.98229&lng=-64.69560&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D", "2026-07-07_t161A"], "community_ids": ["osm3924267772"], "verdict": "nisar | sentinel1 | undecidable", "cause": "unexplained", "reviewer": "", "date": "", "note": ""}
```

#### 13. Near Santa Tereza do Rio Cubua: NISAR links it, Sentinel-1 does not

- Where: at Santa Tereza do Rio Cubua (-64.59994, -3.15162)
- Zone: `unexplained`: no rule explains it
- Communities: Santa Tereza do Rio Cubua
- Passes (2 cases): 2025-11-04_t097D, 2026-07-07_t161A
  - 2026-07-07_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.15162&lng=-64.59994&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-07-06T00%3A00%3A00.000Z&toTime=2026-07-06T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.15162&mlon=-64.59994#map=15/-3.15162/-64.59994) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.15162&lng=-64.59994&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-07-09T00%3A00%3A00.000Z&toTime=2026-07-09T23%3A59%3A59.999Z)
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.15162&lng=-64.59994&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.15162&mlon=-64.59994#map=15/-3.15162/-64.59994) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.15162&lng=-64.59994&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D", "2026-07-07_t161A"], "community_ids": ["osm3924302390"], "verdict": "nisar | sentinel1 | undecidable", "cause": "unexplained", "reviewer": "", "date": "", "note": ""}
```

#### 14. Near Sao Raimundo do Rio Cubua: NISAR links it, Sentinel-1 does not

- Where: at Sao Raimundo do Rio Cubua (-64.59192, -3.08329)
- Zone: `unexplained`: no rule explains it
- Communities: Sao Raimundo do Rio Cubua
- Passes (2 cases): 2025-11-04_t097D, 2026-07-07_t161A
  - 2026-07-07_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.08329&lng=-64.59192&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-07-06T00%3A00%3A00.000Z&toTime=2026-07-06T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.08329&mlon=-64.59192#map=15/-3.08329/-64.59192) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.08329&lng=-64.59192&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-07-09T00%3A00%3A00.000Z&toTime=2026-07-09T23%3A59%3A59.999Z)
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.08329&lng=-64.59192&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.08329&mlon=-64.59192#map=15/-3.08329/-64.59192) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.08329&lng=-64.59192&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D", "2026-07-07_t161A"], "community_ids": ["osm3924302391"], "verdict": "nisar | sentinel1 | undecidable", "cause": "unexplained", "reviewer": "", "date": "", "note": ""}
```

#### 15. Near Rio Grande: NISAR links it, Sentinel-1 does not

- Where: 3.1 km from Rio Grande (-64.7071, -3.21416)
- Zone: `threshold`: backscatter within the margin of the water threshold: a small change of threshold flips it
- Communities: Caburinim de Baixo, São Francisco
- Passes (2 cases): 2026-07-07_t161A
  - 2026-07-07_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.21713&lng=-64.70287&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-07-06T00%3A00%3A00.000Z&toTime=2026-07-06T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.21713&mlon=-64.70287#map=15/-3.21713/-64.70287) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.21713&lng=-64.70287&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-07-09T00%3A00%3A00.000Z&toTime=2026-07-09T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2026-07-07_t161A"], "community_ids": ["osm3924302375", "osm3924302392"], "verdict": "nisar | sentinel1 | undecidable", "cause": "threshold", "reviewer": "", "date": "", "note": ""}
```

#### 16. Near Sao Joaquim do Içe: NISAR links it, Sentinel-1 does not; NISAR's route is wider

- Where: 0.2 km from Sao Joaquim do Içe (-64.70481, -3.26893)
- Zone: `narrow_channel`: reference channel narrower than 60 m
- Communities: Sao Joaquim do Içe, São Francisco do Piranhal
- Passes (2 cases): 2025-11-04_t097D, 2026-07-07_t161A
  - 2026-07-07_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.26915&lng=-64.70629&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-07-06T00%3A00%3A00.000Z&toTime=2026-07-06T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.26915&mlon=-64.70629#map=15/-3.26915/-64.70629) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.26915&lng=-64.70629&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-07-09T00%3A00%3A00.000Z&toTime=2026-07-09T23%3A59%3A59.999Z)
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.26871&lng=-64.70333&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.26871&mlon=-64.70333#map=15/-3.26871/-64.70333) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.26871&lng=-64.70333&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D", "2026-07-07_t161A"], "community_ids": ["osm3984833647", "osm3986860632"], "verdict": "nisar | sentinel1 | undecidable", "cause": "narrow_channel", "reviewer": "", "date": "", "note": ""}
```

#### 17. Near São João: NISAR links it, Sentinel-1 does not

- Where: at São João (-64.59615, -3.17652)
- Zone: `unexplained`: no rule explains it
- Communities: São João
- Passes (2 cases): 2025-11-04_t097D, 2026-07-07_t161A
  - 2026-07-07_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.17652&lng=-64.59615&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-07-06T00%3A00%3A00.000Z&toTime=2026-07-06T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.17652&mlon=-64.59615#map=15/-3.17652/-64.59615) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.17652&lng=-64.59615&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-07-09T00%3A00%3A00.000Z&toTime=2026-07-09T23%3A59%3A59.999Z)
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.17652&lng=-64.59615&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.17652&mlon=-64.59615#map=15/-3.17652/-64.59615) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.17652&lng=-64.59615&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D", "2026-07-07_t161A"], "community_ids": ["osm3924302395"], "verdict": "nisar | sentinel1 | undecidable", "cause": "unexplained", "reviewer": "", "date": "", "note": ""}
```

#### 18. Near São Raimundo: NISAR links it, Sentinel-1 does not

- Where: 0.5 km from São Raimundo (-64.80667, -2.99032)
- Zone: `narrow_channel`: reference channel narrower than 60 m
- Communities: Promessa, São Raimundo
- Passes (2 cases): 2025-11-04_t097D, 2026-08-24_t161A
  - 2026-08-24_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-2.99285&lng=-64.81069&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-08-25T00%3A00%3A00.000Z&toTime=2026-08-25T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-2.99285&mlon=-64.81069#map=15/-2.99285/-64.81069) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-2.99285&lng=-64.81069&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-08-26T00%3A00%3A00.000Z&toTime=2026-08-26T23%3A59%3A59.999Z)
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-2.98779&lng=-64.80266&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-2.98779&mlon=-64.80266#map=15/-2.98779/-64.80266) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-2.98779&lng=-64.80266&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D", "2026-08-24_t161A"], "community_ids": ["osm3924267828", "osm3984712023"], "verdict": "nisar | sentinel1 | undecidable", "cause": "narrow_channel", "reviewer": "", "date": "", "note": ""}
```

#### 19. Near Boca do Mamiraua: NISAR's route is wider

- Where: 1.3 km from Boca do Mamiraua (-64.79836, -3.12812)
- Zone: `narrow_channel`: reference channel narrower than 60 m
- Communities: Alencar
- Passes (2 cases): 2026-08-24_t161A, 2026-08-31_t097D
  - 2026-08-31_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.12821&lng=-64.79845&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-08-30T00%3A00%3A00.000Z&toTime=2026-08-30T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.12821&mlon=-64.79845#map=15/-3.12821/-64.79845) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.12821&lng=-64.79845&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-09-02T00%3A00%3A00.000Z&toTime=2026-09-02T23%3A59%3A59.999Z)
  - 2026-08-24_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.12803&lng=-64.79827&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-08-25T00%3A00%3A00.000Z&toTime=2026-08-25T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.12803&mlon=-64.79827#map=15/-3.12803/-64.79827) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.12803&lng=-64.79827&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-08-26T00%3A00%3A00.000Z&toTime=2026-08-26T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2026-08-24_t161A", "2026-08-31_t097D"], "community_ids": ["osm3984711996"], "verdict": "nisar | sentinel1 | undecidable", "cause": "narrow_channel", "reviewer": "", "date": "", "note": ""}
```

#### 20. Near Nova Esperança: NISAR links it, Sentinel-1 does not; NISAR's route is wider

- Where: 1.3 km from Nova Esperança (-64.88287, -3.47066)
- Zone: `narrow_channel`: reference channel narrower than 60 m
- Communities: Nova Esperança
- Passes (2 cases): 2026-10-11_t161A, 2026-10-23_t161A
  - 2026-10-23_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.46697&lng=-64.88359&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-10-21T00%3A00%3A00.000Z&toTime=2026-10-21T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.46697&mlon=-64.88359#map=15/-3.46697/-64.88359) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.46697&lng=-64.88359&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-10-25T00%3A00%3A00.000Z&toTime=2026-10-25T23%3A59%3A59.999Z)
  - 2026-10-11_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.47435&lng=-64.88215&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-10-11T00%3A00%3A00.000Z&toTime=2026-10-11T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.47435&mlon=-64.88215#map=15/-3.47435/-64.88215) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.47435&lng=-64.88215&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-10-13T00%3A00%3A00.000Z&toTime=2026-10-13T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2026-10-11_t161A", "2026-10-23_t161A"], "community_ids": ["osm8583554431"], "verdict": "nisar | sentinel1 | undecidable", "cause": "narrow_channel", "reviewer": "", "date": "", "note": ""}
```

#### 21. Near São Benedito: NISAR links it, Sentinel-1 does not

- Where: 0.3 km from São Benedito (-64.80421, -3.41135)
- Zone: `threshold`: backscatter within the margin of the water threshold: a small change of threshold flips it
- Communities: Canaman, São Jose do Madureira
- Passes (2 cases): 2026-10-23_t161A
  - 2026-10-23_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.41171&lng=-64.80205&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-10-21T00%3A00%3A00.000Z&toTime=2026-10-21T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.41171&mlon=-64.80205#map=15/-3.41171/-64.80205) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.41171&lng=-64.80205&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-10-25T00%3A00%3A00.000Z&toTime=2026-10-25T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2026-10-23_t161A"], "community_ids": ["osm3986860562", "osm3986860636"], "verdict": "nisar | sentinel1 | undecidable", "cause": "threshold", "reviewer": "", "date": "", "note": ""}
```

#### 22. Near São João do Mulato: NISAR links it, Sentinel-1 does not; NISAR's route is wider

- Where: 3.4 km from São João do Mulato (-64.96765, -3.55094)
- Zone: `shore_mixed_pixel`: within one pixel of the shore: a 20 m pixel holds both water and land
- Communities: Campo Novo, São João do Mulato
- Passes (2 cases): 2025-11-04_t097D, 2026-10-23_t161A
  - 2026-10-23_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.54761&lng=-64.97305&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-10-21T00%3A00%3A00.000Z&toTime=2026-10-21T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.54761&mlon=-64.97305#map=15/-3.54761/-64.97305) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.54761&lng=-64.97305&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-10-25T00%3A00%3A00.000Z&toTime=2026-10-25T23%3A59%3A59.999Z)
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.55427&lng=-64.96225&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.55427&mlon=-64.96225#map=15/-3.55427/-64.96225) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.55427&lng=-64.96225&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D", "2026-10-23_t161A"], "community_ids": ["osm3984833612", "osm3984833655"], "verdict": "nisar | sentinel1 | undecidable", "cause": "shore_mixed_pixel", "reviewer": "", "date": "", "note": ""}
```

#### 23. Near Caburinim de Baixo: NISAR links it, Sentinel-1 does not

- Where: at Caburinim de Baixo (-64.68438, -3.23497)
- Zone: `narrow_channel`: reference channel narrower than 60 m
- Communities: Caburinim de Baixo
- Passes (1 cases): 2025-11-04_t097D
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.23497&lng=-64.68438&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.23497&mlon=-64.68438#map=15/-3.23497/-64.68438) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.23497&lng=-64.68438&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D"], "community_ids": ["osm3924302375"], "verdict": "nisar | sentinel1 | undecidable", "cause": "narrow_channel", "reviewer": "", "date": "", "note": ""}
```

#### 24. Near Comunidade São Francisco do Aratamã: NISAR links it, Sentinel-1 does not

- Where: at Comunidade São Francisco do Aratamã (-64.65657, -3.29792)
- Zone: `narrow_channel`: reference channel narrower than 60 m
- Communities: Comunidade São Francisco do Aratamã
- Passes (1 cases): 2025-11-04_t097D
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.29792&lng=-64.65657&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.29792&mlon=-64.65657#map=15/-3.29792/-64.65657) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.29792&lng=-64.65657&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D"], "community_ids": ["osm9755637967"], "verdict": "nisar | sentinel1 | undecidable", "cause": "narrow_channel", "reviewer": "", "date": "", "note": ""}
```

#### 25. Near Gloria: NISAR links it, Sentinel-1 does not

- Where: at Gloria (-64.66019, -3.33153)
- Zone: `narrow_channel`: reference channel narrower than 60 m
- Communities: Gloria
- Passes (1 cases): 2025-11-04_t097D
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.33153&lng=-64.66019&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.33153&mlon=-64.66019#map=15/-3.33153/-64.66019) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.33153&lng=-64.66019&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D"], "community_ids": ["osm3986860573"], "verdict": "nisar | sentinel1 | undecidable", "cause": "narrow_channel", "reviewer": "", "date": "", "note": ""}
```

#### 26. Near Itapiranema: NISAR's route is wider

- Where: 3.3 km from Itapiranema (-64.79899, -3.33017)
- Zone: `unexplained`: no rule explains it
- Communities: Itapiranema
- Passes (1 cases): 2025-11-04_t097D
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.33017&lng=-64.79899&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.33017&mlon=-64.79899#map=15/-3.33017/-64.79899) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.33017&lng=-64.79899&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D"], "community_ids": ["osm3984833624"], "verdict": "nisar | sentinel1 | undecidable", "cause": "unexplained", "reviewer": "", "date": "", "note": ""}
```

#### 27. Near Porto Natal: NISAR links it, Sentinel-1 does not

- Where: at Porto Natal (-64.6635, -3.26469)
- Zone: `narrow_channel`: reference channel narrower than 60 m
- Communities: Porto Natal
- Passes (1 cases): 2025-11-04_t097D
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.26469&lng=-64.66350&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.26469&mlon=-64.66350#map=15/-3.26469/-64.66350) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.26469&lng=-64.66350&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D"], "community_ids": ["osm3924302386"], "verdict": "nisar | sentinel1 | undecidable", "cause": "narrow_channel", "reviewer": "", "date": "", "note": ""}
```

#### 28. Near São Francisco: NISAR links it, Sentinel-1 does not

- Where: at São Francisco (-64.62125, -3.2814)
- Zone: `narrow_channel`: reference channel narrower than 60 m
- Communities: São Francisco
- Passes (1 cases): 2025-11-04_t097D
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.28140&lng=-64.62125&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.28140&mlon=-64.62125#map=15/-3.28140/-64.62125) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.28140&lng=-64.62125&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D"], "community_ids": ["osm3924302392"], "verdict": "nisar | sentinel1 | undecidable", "cause": "narrow_channel", "reviewer": "", "date": "", "note": ""}
```

#### 29. Near Vila Nova: NISAR's route is wider

- Where: 1.0 km from Vila Nova (-64.69009, -3.32531)
- Zone: `shore_mixed_pixel`: within one pixel of the shore: a 20 m pixel holds both water and land
- Communities: Vila Nova
- Passes (1 cases): 2025-11-04_t097D
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.32531&lng=-64.69009&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.32531&mlon=-64.69009#map=15/-3.32531/-64.69009) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.32531&lng=-64.69009&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D"], "community_ids": ["osm3986860650"], "verdict": "nisar | sentinel1 | undecidable", "cause": "shore_mixed_pixel", "reviewer": "", "date": "", "note": ""}
```

#### 30. Near Sao Joaquim do Içe: NISAR links it, Sentinel-1 does not

- Where: 2.3 km from Sao Joaquim do Içe (-64.68631, -3.25727)
- Zone: `threshold`: backscatter within the margin of the water threshold: a small change of threshold flips it
- Communities: Porto Natal
- Passes (1 cases): 2026-07-07_t161A
  - 2026-07-07_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.25727&lng=-64.68631&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-07-06T00%3A00%3A00.000Z&toTime=2026-07-06T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.25727&mlon=-64.68631#map=15/-3.25727/-64.68631) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.25727&lng=-64.68631&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-07-09T00%3A00%3A00.000Z&toTime=2026-07-09T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2026-07-07_t161A"], "community_ids": ["osm3924302386"], "verdict": "nisar | sentinel1 | undecidable", "cause": "threshold", "reviewer": "", "date": "", "note": ""}
```

#### 31. Near São Raimundo do Sapia: NISAR links it, Sentinel-1 does not

- Where: 4.7 km from São Raimundo do Sapia (-65.01913, -3.70925)
- Zone: `threshold`: backscatter within the margin of the water threshold: a small change of threshold flips it
- Communities: Campo Novo
- Passes (1 cases): 2026-10-23_t161A
  - 2026-10-23_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.70925&lng=-65.01913&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-10-21T00%3A00%3A00.000Z&toTime=2026-10-21T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.70925&mlon=-65.01913#map=15/-3.70925/-65.01913) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.70925&lng=-65.01913&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-10-25T00%3A00%3A00.000Z&toTime=2026-10-25T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2026-10-23_t161A"], "community_ids": ["osm3984833612"], "verdict": "nisar | sentinel1 | undecidable", "cause": "threshold", "reviewer": "", "date": "", "note": ""}
```

#### 32. Near Novo Amparo: Sentinel-1 links it, NISAR does not

- Where: 2.2 km from Novo Amparo (-64.80619, -2.9033)
- Zone: `shore_mixed_pixel`: within one pixel of the shore: a 20 m pixel holds both water and land
- Communities: Novo Amparo
- Passes (4 cases): 2026-07-07_t161A, 2026-08-24_t161A, 2026-10-11_t161A, 2026-10-23_t161A
  - 2026-10-23_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-2.90339&lng=-64.80619&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-10-21T00%3A00%3A00.000Z&toTime=2026-10-21T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-2.90339&mlon=-64.80619#map=15/-2.90339/-64.80619) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-2.90339&lng=-64.80619&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-10-25T00%3A00%3A00.000Z&toTime=2026-10-25T23%3A59%3A59.999Z)
  - 2026-10-11_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-2.90339&lng=-64.80637&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-10-11T00%3A00%3A00.000Z&toTime=2026-10-11T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-2.90339&mlon=-64.80637#map=15/-2.90339/-64.80637) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-2.90339&lng=-64.80637&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-10-13T00%3A00%3A00.000Z&toTime=2026-10-13T23%3A59%3A59.999Z)
  - 2026-08-24_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-2.90321&lng=-64.80619&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-08-25T00%3A00%3A00.000Z&toTime=2026-08-25T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-2.90321&mlon=-64.80619#map=15/-2.90321/-64.80619) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-2.90321&lng=-64.80619&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-08-26T00%3A00%3A00.000Z&toTime=2026-08-26T23%3A59%3A59.999Z)
  - 2026-07-07_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-2.90321&lng=-64.80601&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-07-06T00%3A00%3A00.000Z&toTime=2026-07-06T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-2.90321&mlon=-64.80601#map=15/-2.90321/-64.80601) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-2.90321&lng=-64.80601&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-07-09T00%3A00%3A00.000Z&toTime=2026-07-09T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2026-07-07_t161A", "2026-08-24_t161A", "2026-10-11_t161A", "2026-10-23_t161A"], "community_ids": ["osm3924267794"], "verdict": "nisar | sentinel1 | undecidable", "cause": "shore_mixed_pixel", "reviewer": "", "date": "", "note": ""}
```

Places already checked:

| Near | Kinds | Zone | Verdicts | Passes |
|---|---|---|---|---|
| São Jorge | false_route, overconfident | narrow_channel | nisar | 2025-11-04_t097D, 2026-07-07_t161A |
| São Jose | false_route, overconfident | narrow_channel | nisar | 2025-11-04_t097D, 2026-07-07_t161A |
| Nogueira | false_route | wind_roughness | nisar | 2025-11-04_t097D |
| Itapiranema | overconfident | shore_mixed_pixel | nisar | 2025-11-04_t097D |
| Cauaçu de Baixo | false_route, overconfident | narrow_channel | nisar | 2025-11-04_t097D, 2026-10-11_t161A, 2026-10-23_t161A |
| Santa Terezinha_ | false_route | narrow_channel | nisar | 2025-11-04_t097D |
| Fonte da Luz | false_route | narrow_channel | nisar | 2025-11-04_t097D |
| Assunção | false_route | narrow_channel | nisar | 2025-11-04_t097D |
| Caburinim de Cima | false_route | narrow_channel | nisar | 2025-11-04_t097D |
| Canaria | false_route | narrow_channel | nisar | 2025-11-04_t097D |
| Coadi | false_route | narrow_channel | nisar | 2025-11-04_t097D |
| Jaquiri | false_route | narrow_channel | nisar | 2025-11-04_t097D |
| Juruama | false_route | narrow_channel | nisar | 2025-11-04_t097D |
| Juruari | false_route | narrow_channel | nisar | 2025-11-04_t097D |
| Laranjal | false_route | narrow_channel | nisar | 2025-11-04_t097D |
| Manixi | false_route | narrow_channel | nisar | 2025-11-04_t097D |
| São Sebastião do Ture | false_route | shore_mixed_pixel | nisar | 2025-11-04_t097D |
| Pau Rosa | false_route | narrow_channel | nisar | 2025-11-04_t097D |
| Perseverança | false_route | narrow_channel | nisar | 2025-11-04_t097D |
| Buna | false_route | narrow_channel | nisar | 2025-11-04_t097D |
| Rio Grande | false_route | narrow_channel | nisar | 2025-11-04_t097D |
| Santa Elena | false_route | narrow_channel | nisar | 2025-11-04_t097D |
| São Rafael | false_route | narrow_channel | nisar | 2025-11-04_t097D |
| Tapieira | false_route | narrow_channel | nisar | 2025-11-04_t097D |
| Itapiranema | overconfident | shore_mixed_pixel | nisar | 2025-11-04_t097D |
| Santa Luzia do Catuiri | false_route | shore_mixed_pixel | nisar | 2026-10-11_t161A |
| Vila Sião | overconfident | shore_mixed_pixel | nisar | 2026-10-11_t161A |
| São João do Mulato | false_route | shore_mixed_pixel | nisar | 2026-10-23_t161A |
| São Sebastião do Ture | false_route | shore_mixed_pixel | nisar | 2026-10-23_t161A |
| Vila Sião | false_route | shore_mixed_pixel | nisar | 2026-10-23_t161A |

## River gauge

ANA telemetry, station 12900001.

| Correlation | Spearman rho | Passes | Expected sign |
|---|---|---|---|
| water area vs level | 0.968 | 15 | + |
| lost routes vs level | -0.757 | 15 | - |

## Field and report checks

| Community | Expected | Kind | Found | Passes judged | Correct | Source |
|---|---|---|---|---|---|---|
| Caiambé | linked | sanity | True | 14 | 14 | Team plausibility check (docs/river-monitor.md): settlement on the Solimões main channel, used as the boat landing in the 2023 and 2024 droughts. Not an observation of 2026. |
| Alvarães | linked | sanity | True | 14 | 14 | Team plausibility check (docs/river-monitor.md): municipal seat reached through its port; no 2026 report of the town being cut off was found. Not an observation of 2026. |

## Community classes

| monitored | unresolved | inland | no_data |
|---|---|---|---|
| 130 | 39 | 35 | 0 |
