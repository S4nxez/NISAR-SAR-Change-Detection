# Benchmark: v3-sentinel1-mud-veto

Exam version 3 · 2026-11-13T10:03:24Z · commit `21a1e94` (uncommitted changes)

## Scorecard

| Metric | Value | Meaning |
|---|---|---|
| Synthetic correct | 0.800 | share of lane results that are right (higher is better) |
| Synthetic dangerous | 5 | lane results showing a route that does not exist or is too narrow |
| Water IoU vs reference | 0.929 | agreement of the water mask with the reference: Sentinel-2 in exam 1, the consensus of the references from exam 2 (higher is better) |
| Narrow recall | 0.388 | share of reference channels under 60 m mapped as water |
| False water at shore | 0.074 | share of shoreline land mapped as water (lower is better) |
| Status agreement | 0.961 | community status equal to the one from the reference water |
| False routes | 0 | community shown with a route the reference water does not have (lower is better; not yet checked by a person) |
| False isolated | 15 | community shown isolated while the reference water links it |
| Gauge rho | -0.759 | rank correlation of lost routes with the river level (more negative is better) |
| Field checks | 1.000 | share of field and report checks the record gets right |
| Undecided | 47 | community-pass pairs the references cannot decide (exam 2), left unscored |
| To review | 1 | disagreements a person has to check (exam 2; see Manual review in the report) |
| Confirmed false routes | – | false routes a person confirmed in processing/benchmark/reviews.json (exam 2) |
| NISAR-S1 agreement | 0.983 | share of the pixels both radars judged on which NISAR and Sentinel-1 agree (exam 3, not scored) |
| NISAR-S1 places | 67 | places where the two radars give a community different statuses, to check by hand (exam 3) |

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
| 0.961 | 0.926 | 0 | 2 | 15 | 47 |

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
| 2026-10-11_t161A | 2026-10-11 | 2026-10-09 | – | 5.699 | 0.000 | 0.000 | 0.899 | 0.973 | 0 | 1 | 1 |
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
| 2026-10-11_t161A | Nova Esperança | false_isolated | isolated | connected | sentinel1_mud | radar_physics | 7 | -64.88215, -3.47309 | yes | – |

| Kind | Cases | Confirmed | Rejected | Undecidable | Pending |
|---|---|---|---|---|---|
| false_isolated | 15 | 0 | 0 | 0 | 15 |
| overconfident | 2 | 0 | 1 | 0 | 1 |
| underconfident | 1 | 0 | 0 | 0 | 1 |

## Manual review

1 cases need a person (every false route, the dangerous error, and every case whose cause says the reference may be wrong, points at our processing or is unexplained). They come from 1 places, each named after the nearest community. How to check a place: docs/river-monitor-benchmark.md, "Manual review"; one verdict covers every community and pass of the place.

### 1. Near Nova Esperança: isolated while the reference links it

- Where: 1.1 km from Nova Esperança (-64.88215, -3.47309); the links open the map on that point.
- Probable cause: `sentinel1_mud` (radar_physics): NISAR water left out of the routes at low water because Sentinel-1 saw mud there (ADR-007)
- Communities: Nova Esperança
- Passes (1 cases): 2026-10-11_t161A
  - 2026-10-11_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.47309&lng=-64.88215&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-10-11T00%3A00%3A00.000Z&toTime=2026-10-11T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.47309&mlon=-64.88215#map=15/-3.47309/-64.88215) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.47309&lng=-64.88215&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-10-13T00%3A00%3A00.000Z&toTime=2026-10-13T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/reviews.json`:

```json
{"passes": ["2026-10-11_t161A"], "community_ids": ["osm8583554431"], "verdict": "nisar | reference | undecidable", "cause": "sentinel1_mud", "reviewer": "", "date": "", "note": ""}
```

Other places with disagreements (cause known, no review needed):

| Near | Kinds | Cause | Communities | Passes |
|---|---|---|---|---|
| Boca do Mamiraua | overconfident | narrow_channel | Alencar | 2026-08-31_t097D |
| Nova Jerusalem | overconfident | narrow_channel | Canaman | 2026-08-31_t097D |
| Caiambé | false_isolated | narrow_channel | Acapu, Barreirinha, Cacai, Cairara, Feliciana, Macedo, Marajo, Miriti, Moura, Uirapuru | 2026-08-19_t097D |
| Jaquiri | false_isolated | river_level_change | Jaguarí | 2026-08-19_t097D, 2026-08-24_t161A, 2026-08-31_t097D |
| São Jose | false_isolated | shore_mixed_pixel | São Jose | 2026-08-19_t097D |
| São João do Mulato | underconfident | narrow_channel | Caru | 2026-08-31_t097D |

## NISAR and Sentinel-1 (not scored)

Sentinel-1 is part of the method (ADR-007), so it is not a reference of the exam. Here the two radars check each other: where both see water or both see land the result is confirmed by two satellites; the places where they give a community different statuses are listed for a person to check. The verdicts (processing/benchmark/crosscheck_reviews.json) count per zone type and tell which radar to trust where.

| Passes | Judged km² | Agreement | NISAR-only water km² | Sentinel-1-only water km² | Mud left out of routes km² | Status cases | Places |
|---|---|---|---|---|---|---|---|
| 6 | 46749.400 | 0.983 | 733.700 | 59.800 | 178.200 | 227 | 67 |

| Pass | Sentinel-1 dates | Agreement | Both water km² | NISAR only km² | Sentinel-1 only km² | Mud km² | Status cases |
|---|---|---|---|---|---|---|---|
| 2025-11-04_t097D | 2025-11-04 | 0.966 | 366.960 | 207.010 | 2.220 | 43.120 | 88 |
| 2026-07-07_t161A | 2026-07-09 | 0.986 | 576.270 | 70.930 | 9.440 | 0.000 | 58 |
| 2026-08-24_t161A | 2026-08-26, 2026-08-21 | 0.993 | 846.960 | 49.790 | 19.910 | 0.000 | 7 |
| 2026-08-31_t097D | 2026-09-02 | 0.993 | 620.490 | 33.930 | 9.040 | 0.000 | 1 |
| 2026-10-11_t161A | 2026-10-13, 2026-10-08 | 0.983 | 676.460 | 149.850 | 12.030 | 62.770 | 40 |
| 2026-10-23_t161A | 2026-10-25, 2026-10-20 | 0.976 | 590.270 | 222.150 | 7.190 | 72.350 | 33 |

Verdicts per zone type (the probable cause of each case):

| Zone | Cases | NISAR right | Sentinel-1 right | Undecidable | Pending |
|---|---|---|---|---|---|
| narrow_channel | 104 | 0 | 0 | 0 | 104 |
| unexplained | 48 | 0 | 0 | 0 | 48 |
| threshold | 37 | 0 | 0 | 0 | 37 |
| shore_mixed_pixel | 33 | 0 | 0 | 0 | 33 |
| smooth_ground | 5 | 0 | 0 | 0 | 5 |

Which radar the published status follows in those cases: neither 12, nisar 200, sentinel1 15.

### Places to check (67)

Open both links of a pass: the Sentinel-1 image (10 m, VV/VH) and the Sentinel-2 image of the nearest clear day. A verdict covers every community and pass of the place.

#### 1. Near São Jorge: NISAR links it, Sentinel-1 does not; NISAR's route is wider

- Where: 0.8 km from São Jorge (-64.66738, -3.35152)
- Zone: `narrow_channel`: reference channel narrower than 60 m
- Communities: Alencar, Alvarães, Boca do Mamiraua, Caburinim de Cima, Fazendinha, Juruari, Laranjal, Manixi, Marajá, Missão, Olaria, Parauari, Pau Rosa, Perseverança, Porto Vale, Rio Grande, Santa Clara, Santa Elena, Santa Maria, Santa Terezinha_, Sao Joaquim do Içe, São Jorge, São Jose, São Pedro, São Rafael, São Raimundo, Tapieira, Vila Valente
- Passes (30 cases): 2025-11-04_t097D, 2026-07-07_t161A
  - 2026-07-07_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.34961&lng=-64.66813&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-07-06T00%3A00%3A00.000Z&toTime=2026-07-06T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.34961&mlon=-64.66813#map=15/-3.34961/-64.66813) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.34961&lng=-64.66813&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-07-09T00%3A00%3A00.000Z&toTime=2026-07-09T23%3A59%3A59.999Z)
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.37308&lng=-64.65676&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.37308&mlon=-64.65676#map=15/-3.37308/-64.65676) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.37308&lng=-64.65676&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D", "2026-07-07_t161A"], "community_ids": ["osm3924267828", "osm3924267833", "osm3924302376", "osm3924302380", "osm3924302384", "osm3924302388", "osm3984711996", "osm3984711997", "osm3984833619", "osm3984833629", "osm3984833630", "osm3984833631", "osm3984833637", "osm3984833638", "osm3984833640", "osm3984833643", "osm3984833646", "osm3984833647", "osm3984833650", "osm3984833653", "osm3984833656", "osm3986860589", "osm3986860610", "osm3986860614", "osm3986860619", "osm3986860634", "osm3986860641", "osm3986860651", "osm415524054"], "verdict": "nisar | sentinel1 | undecidable", "cause": "narrow_channel", "reviewer": "", "date": "", "note": ""}
```

#### 2. Near Itapiranema: NISAR links it, Sentinel-1 does not; NISAR's route is wider

- Where: 0.5 km from Itapiranema (-64.82013, -3.34559)
- Zone: `shore_mixed_pixel`: within one pixel of the shore: a 20 m pixel holds both water and land
- Communities: Arraia, Caru, Divino Espito do Catuiri, Divino Estirito Santo, Fe Em Deus, Mutum, Santa Luzia do Catuiri, São João do Mulato, São Raimundo de Baixo, São Sebastião do Ture, São Sebatião do Catuiri, Tauary, Vila Sião
- Passes (19 cases): 2025-11-04_t097D, 2026-10-11_t161A, 2026-10-23_t161A
  - 2026-10-23_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.33971&lng=-64.81447&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-10-21T00%3A00%3A00.000Z&toTime=2026-10-21T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.33971&mlon=-64.81447#map=15/-3.33971/-64.81447) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.33971&lng=-64.81447&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-10-25T00%3A00%3A00.000Z&toTime=2026-10-25T23%3A59%3A59.999Z)
  - 2026-10-11_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.34115&lng=-64.81987&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-10-11T00%3A00%3A00.000Z&toTime=2026-10-11T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.34115&mlon=-64.81987#map=15/-3.34115/-64.81987) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.34115&lng=-64.81987&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-10-13T00%3A00%3A00.000Z&toTime=2026-10-13T23%3A59%3A59.999Z)
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.35609&lng=-64.82113&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.35609&mlon=-64.82113#map=15/-3.35609/-64.82113) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.35609&lng=-64.82113&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D", "2026-10-11_t161A", "2026-10-23_t161A"], "community_ids": ["osm3984833607", "osm3984833616", "osm3984833618", "osm3984833644", "osm3984833655", "osm3984835457", "osm3984835460", "osm3984835463", "osm3986860568", "osm3986860569", "osm3986860596", "osm3986860644", "osm3986860646"], "verdict": "nisar | sentinel1 | undecidable", "cause": "shore_mixed_pixel", "reviewer": "", "date": "", "note": ""}
```

#### 3. Near São Jose: NISAR links it, Sentinel-1 does not; NISAR's route is wider

- Where: 0.5 km from São Jose (-64.83336, -3.16626)
- Zone: `narrow_channel`: reference channel narrower than 60 m
- Communities: Assunção, Buna, Canaria, Cauaçu de Baixo, Coadi, Fonte da Luz, Fonte de Luz, Jaquiri, Juruama, Marajá, Parauari, Punã, São Jose, Tupa Supe
- Passes (14 cases): 2025-11-04_t097D, 2026-07-07_t161A
  - 2026-07-07_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.16511&lng=-64.83355&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-07-06T00%3A00%3A00.000Z&toTime=2026-07-06T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.16511&mlon=-64.83355#map=15/-3.16511/-64.83355) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.16511&lng=-64.83355&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-07-09T00%3A00%3A00.000Z&toTime=2026-07-09T23%3A59%3A59.999Z)
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.16941&lng=-64.83048&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.16941&mlon=-64.83048#map=15/-3.16941/-64.83048) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.16941&lng=-64.83048&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D", "2026-07-07_t161A"], "community_ids": ["osm2661355762", "osm3984712000", "osm3984712003", "osm3984712006", "osm3984712016", "osm3984712024", "osm3984712038", "osm3984833608", "osm3984833614", "osm3984833621", "osm3984833628", "osm3984833631", "osm3984833638", "osm3984833653"], "verdict": "nisar | sentinel1 | undecidable", "cause": "narrow_channel", "reviewer": "", "date": "", "note": ""}
```

#### 4. Near Itapiranema: NISAR links it, Sentinel-1 does not

- Where: 4.4 km from Itapiranema (-64.78498, -3.34127)
- Zone: `unexplained`: no rule explains it
- Communities: Bacuri, Canaman, Caru, Divino Estirito Santo, Fe Em Deus, Nova Jerusalem, São Antonio do Ipapucu, São Benedito, São Jose do Madureira, São João do Mulato, São Sebastião do Ture, Vista Alegre
- Passes (13 cases): 2025-11-04_t097D
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.33755&lng=-64.78243&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.33755&mlon=-64.78243#map=15/-3.33755/-64.78243) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.33755&lng=-64.78243&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D"], "community_ids": ["osm3984833616", "osm3984833655", "osm3986858845", "osm3986860562", "osm3986860568", "osm3986860569", "osm3986860602", "osm3986860627", "osm3986860636", "osm3986860644", "osm3986860652", "osm3986860653", "osm8583188413"], "verdict": "nisar | sentinel1 | undecidable", "cause": "unexplained", "reviewer": "", "date": "", "note": ""}
```

#### 5. Near Santa Rosa do Repartimento: NISAR's route is wider

- Where: 0.3 km from Santa Rosa do Repartimento (-64.59299, -3.21497)
- Zone: `narrow_channel`: reference channel narrower than 60 m
- Communities: Abacatal, Acarazinho, Boca do Atapi, Cardoso, Girassol, Liocadio, Mangueal, Monte Sinai, Nazaré, Renascer, São João
- Passes (11 cases): 2026-10-11_t161A
  - 2026-10-11_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.21497&lng=-64.59343&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-10-11T00%3A00%3A00.000Z&toTime=2026-10-11T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.21497&mlon=-64.59343#map=15/-3.21497/-64.59343) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.21497&lng=-64.59343&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-10-13T00%3A00%3A00.000Z&toTime=2026-10-13T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2026-10-11_t161A"], "community_ids": ["osm3924302370", "osm3924302372", "osm3924302373", "osm3924302377", "osm3924302379", "osm3924302381", "osm3924302382", "osm3924302383", "osm3924302387", "osm3924302395", "osm416757398"], "verdict": "nisar | sentinel1 | undecidable", "cause": "narrow_channel", "reviewer": "", "date": "", "note": ""}
```

#### 6. Near São João: NISAR links it, Sentinel-1 does not

- Where: 1.2 km from São João (-64.60145, -3.16751)
- Zone: `threshold`: backscatter within the margin of the water threshold: a small change of threshold flips it
- Communities: Belo Horizonte, Cupuacu, Santa Tereza do Rio Cubua, Sao Raimundo do Rio Cubua, Sitio Luiz, São Francisco do Mapitirini, São João, São Sebastião
- Passes (9 cases): 2025-11-04_t097D, 2026-07-07_t161A, 2026-10-11_t161A
  - 2026-10-11_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.16493&lng=-64.60297&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-10-11T00%3A00%3A00.000Z&toTime=2026-10-11T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.16493&mlon=-64.60297#map=15/-3.16493/-64.60297) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.16493&lng=-64.60297&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-10-13T00%3A00%3A00.000Z&toTime=2026-10-13T23%3A59%3A59.999Z)
  - 2026-07-07_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.17652&lng=-64.59615&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-07-06T00%3A00%3A00.000Z&toTime=2026-07-06T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.17652&mlon=-64.59615#map=15/-3.17652/-64.59615) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.17652&lng=-64.59615&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-07-09T00%3A00%3A00.000Z&toTime=2026-07-09T23%3A59%3A59.999Z)
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.17652&lng=-64.59615&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.17652&mlon=-64.59615#map=15/-3.17652/-64.59615) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.17652&lng=-64.59615&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D", "2026-07-07_t161A", "2026-10-11_t161A"], "community_ids": ["osm3924267758", "osm3924267772", "osm3924267813", "osm3924267817", "osm3924267831", "osm3924302390", "osm3924302391", "osm3924302395"], "verdict": "nisar | sentinel1 | undecidable", "cause": "threshold", "reviewer": "", "date": "", "note": ""}
```

#### 7. Near Igarape do Grilo: NISAR links it, Sentinel-1 does not; NISAR's route is wider

- Where: 1.0 km from Igarape do Grilo (-64.7719, -3.30405)
- Zone: `shore_mixed_pixel`: within one pixel of the shore: a 20 m pixel holds both water and land
- Communities: Arraia, Itapiranema, Nogueira, São João do Mulato, São Raimundo de Baixo, São Sebastião do Ture, São Sebatião do Catuiri, Tauary
- Passes (8 cases): 2026-10-23_t161A
  - 2026-10-23_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.30263&lng=-64.77199&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-10-21T00%3A00%3A00.000Z&toTime=2026-10-21T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.30263&mlon=-64.77199#map=15/-3.30263/-64.77199) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.30263&lng=-64.77199&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-10-25T00%3A00%3A00.000Z&toTime=2026-10-25T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2026-10-23_t161A"], "community_ids": ["osm3984833607", "osm3984833624", "osm3984833636", "osm3984833655", "osm3984835457", "osm3984835460", "osm3986860644", "osm3986860646"], "verdict": "nisar | sentinel1 | undecidable", "cause": "shore_mixed_pixel", "reviewer": "", "date": "", "note": ""}
```

#### 8. Near Santa Clara: NISAR links it, Sentinel-1 does not; NISAR's route is wider

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

#### 9. Near Vista Alegre: NISAR links it, Sentinel-1 does not; NISAR's route is wider

- Where: at Vista Alegre (-64.80715, -3.40898)
- Zone: `threshold`: backscatter within the margin of the water threshold: a small change of threshold flips it
- Communities: Canaman, Nova Jerusalem, São Benedito, São Jose do Madureira
- Passes (6 cases): 2026-10-11_t161A, 2026-10-23_t161A
  - 2026-10-23_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.41063&lng=-64.80673&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-10-21T00%3A00%3A00.000Z&toTime=2026-10-21T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.41063&mlon=-64.80673#map=15/-3.41063/-64.80673) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.41063&lng=-64.80673&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-10-25T00%3A00%3A00.000Z&toTime=2026-10-25T23%3A59%3A59.999Z)
  - 2026-10-11_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.41405&lng=-64.79593&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-10-11T00%3A00%3A00.000Z&toTime=2026-10-11T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.41405&mlon=-64.79593#map=15/-3.41405/-64.79593) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.41405&lng=-64.79593&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-10-13T00%3A00%3A00.000Z&toTime=2026-10-13T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2026-10-11_t161A", "2026-10-23_t161A"], "community_ids": ["osm3986860562", "osm3986860602", "osm3986860627", "osm3986860636"], "verdict": "nisar | sentinel1 | undecidable", "cause": "threshold", "reviewer": "", "date": "", "note": ""}
```

#### 10. Near Sao Raimundo do Rio Cubua: NISAR's route is wider

- Where: 2.0 km from Sao Raimundo do Rio Cubua (-64.59397, -3.10103)
- Zone: `narrow_channel`: reference channel narrower than 60 m
- Communities: Belo Horizonte, Cupuacu, Sao Raimundo do Rio Cubua, Sitio Luiz, São Francisco do Mapitirini, São Sebastião
- Passes (6 cases): 2026-10-23_t161A
  - 2026-10-23_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.10103&lng=-64.59397&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-10-21T00%3A00%3A00.000Z&toTime=2026-10-21T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.10103&mlon=-64.59397#map=15/-3.10103/-64.59397) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.10103&lng=-64.59397&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-10-25T00%3A00%3A00.000Z&toTime=2026-10-25T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2026-10-23_t161A"], "community_ids": ["osm3924267758", "osm3924267772", "osm3924267813", "osm3924267817", "osm3924267831", "osm3924302391"], "verdict": "nisar | sentinel1 | undecidable", "cause": "narrow_channel", "reviewer": "", "date": "", "note": ""}
```

#### 11. Near Santa Maria: NISAR links it, Sentinel-1 does not

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

#### 12. Near São Francisco do Mapitirini: NISAR links it, Sentinel-1 does not

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

#### 13. Near Sitio Luiz: NISAR links it, Sentinel-1 does not

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

#### 14. Near São Francisco do Bauana: NISAR links it, Sentinel-1 does not

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

#### 15. Near Boca do Mamiraua: NISAR links it, Sentinel-1 does not

- Where: 1.7 km from Boca do Mamiraua (-64.78054, -3.12731)
- Zone: `threshold`: backscatter within the margin of the water threshold: a small change of threshold flips it
- Communities: Alencar, Boca do Mamiraua, Juruari, São Jose
- Passes (4 cases): 2025-11-04_t097D, 2026-10-11_t161A
  - 2026-10-11_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.12983&lng=-64.77883&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-10-11T00%3A00%3A00.000Z&toTime=2026-10-11T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.12983&mlon=-64.77883#map=15/-3.12983/-64.77883) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.12983&lng=-64.77883&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-10-13T00%3A00%3A00.000Z&toTime=2026-10-13T23%3A59%3A59.999Z)
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.12623&lng=-64.78171&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.12623&mlon=-64.78171#map=15/-3.12623/-64.78171) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.12623&lng=-64.78171&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D", "2026-10-11_t161A"], "community_ids": ["osm3924302380", "osm3984711996", "osm3984711997", "osm3984712031"], "verdict": "nisar | sentinel1 | undecidable", "cause": "threshold", "reviewer": "", "date": "", "note": ""}
```

#### 16. Near Juruari: NISAR links it, Sentinel-1 does not

- Where: 0.2 km from Juruari (-64.73905, -3.12697)
- Zone: `smooth_ground`: seasonal ground (bank, mud, sand) clearly dark in L-band
- Communities: Juruari, Pau Rosa, São Raimundo, Tapieira
- Passes (4 cases): 2025-11-04_t097D, 2026-10-11_t161A
  - 2026-10-11_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.12677&lng=-64.73851&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-10-11T00%3A00%3A00.000Z&toTime=2026-10-11T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.12677&mlon=-64.73851#map=15/-3.12677/-64.73851) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.12677&lng=-64.73851&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-10-13T00%3A00%3A00.000Z&toTime=2026-10-13T23%3A59%3A59.999Z)
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.12758&lng=-64.74066&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.12758&mlon=-64.74066#map=15/-3.12758/-64.74066) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.12758&lng=-64.74066&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D", "2026-10-11_t161A"], "community_ids": ["osm3924267828", "osm3924267833", "osm3924302380", "osm3924302384"], "verdict": "nisar | sentinel1 | undecidable", "cause": "smooth_ground", "reviewer": "", "date": "", "note": ""}
```

#### 17. Near Cauaçu de Baixo: NISAR links it, Sentinel-1 does not; NISAR's route is wider

- Where: 1.0 km from Cauaçu de Baixo (-65.00839, -3.04398)
- Zone: `narrow_channel`: reference channel narrower than 60 m
- Communities: Buna, Cauaçu de Baixo
- Passes (4 cases): 2025-11-04_t097D, 2026-10-11_t161A, 2026-10-23_t161A
  - 2026-10-23_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.04469&lng=-65.00743&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-10-21T00%3A00%3A00.000Z&toTime=2026-10-21T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.04469&mlon=-65.00743#map=15/-3.04469/-65.00743) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.04469&lng=-65.00743&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-10-25T00%3A00%3A00.000Z&toTime=2026-10-25T23%3A59%3A59.999Z)
  - 2026-10-11_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.04505&lng=-65.00689&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-10-11T00%3A00%3A00.000Z&toTime=2026-10-11T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.04505&mlon=-65.00689#map=15/-3.04505/-65.00689) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.04505&lng=-65.00689&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-10-13T00%3A00%3A00.000Z&toTime=2026-10-13T23%3A59%3A59.999Z)
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.04795&lng=-65.01833&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.04795&mlon=-65.01833#map=15/-3.04795/-65.01833) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.04795&lng=-65.01833&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D", "2026-10-11_t161A", "2026-10-23_t161A"], "community_ids": ["osm2661355762", "osm3984712000"], "verdict": "nisar | sentinel1 | undecidable", "cause": "narrow_channel", "reviewer": "", "date": "", "note": ""}
```

#### 18. Near Vista Alegre: NISAR links it, Sentinel-1 does not

- Where: 2.2 km from Vista Alegre (-64.82941, -3.40033)
- Zone: `unexplained`: no rule explains it
- Communities: Fe Em Deus, Nova Esperança, São Jose do Tuiuca, Tauary
- Passes (4 cases): 2025-11-04_t097D, 2026-10-23_t161A
  - 2026-10-23_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.40595&lng=-64.82545&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-10-21T00%3A00%3A00.000Z&toTime=2026-10-21T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.40595&mlon=-64.82545#map=15/-3.40595/-64.82545) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.40595&lng=-64.82545&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-10-25T00%3A00%3A00.000Z&toTime=2026-10-25T23%3A59%3A59.999Z)
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.39659&lng=-64.82671&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.39659&mlon=-64.82671#map=15/-3.39659/-64.82671) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.39659&lng=-64.82671&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D", "2026-10-23_t161A"], "community_ids": ["osm3984833652", "osm3986860569", "osm3986860646", "osm8583554431"], "verdict": "nisar | sentinel1 | undecidable", "cause": "unexplained", "reviewer": "", "date": "", "note": ""}
```

#### 19. Near Boara do Meio: NISAR links it, Sentinel-1 does not

- Where: 0.1 km from Boara do Meio (-64.63925, -3.35448)
- Zone: `narrow_channel`: reference channel narrower than 60 m
- Communities: Boara de Cima, Boara do Meio, Boarazinho
- Passes (3 cases): 2025-11-04_t097D
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.35927&lng=-64.63600&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.35927&mlon=-64.63600#map=15/-3.35927/-64.63600) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.35927&lng=-64.63600&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D"], "community_ids": ["osm3986858853", "osm3986858854", "osm9829129139"], "verdict": "nisar | sentinel1 | undecidable", "cause": "narrow_channel", "reviewer": "", "date": "", "note": ""}
```

#### 20. Near Santa Terezinha_: NISAR links it, Sentinel-1 does not

- Where: 0.1 km from Santa Terezinha_ (-64.74528, -3.26098)
- Zone: `narrow_channel`: reference channel narrower than 60 m
- Communities: Fazendinha, Santa Terezinha_, São Jorge
- Passes (3 cases): 2025-11-04_t097D
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.26590&lng=-64.73703&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.26590&mlon=-64.73703#map=15/-3.26590/-64.73703) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.26590&lng=-64.73703&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D"], "community_ids": ["osm3984833619", "osm3984833646", "osm3984833650"], "verdict": "nisar | sentinel1 | undecidable", "cause": "narrow_channel", "reviewer": "", "date": "", "note": ""}
```

#### 21. Near Fonte da Luz: NISAR links it, Sentinel-1 does not

- Where: 0.4 km from Fonte da Luz (-64.97256, -3.0851)
- Zone: `narrow_channel`: reference channel narrower than 60 m
- Communities: Fonte da Luz, Fonte de Luz, Tupa Supe
- Passes (3 cases): 2025-11-04_t097D
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.08048&lng=-64.97845&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.08048&mlon=-64.97845#map=15/-3.08048/-64.97845) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.08048&lng=-64.97845&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D"], "community_ids": ["osm3984712006", "osm3984712038", "osm3984833621"], "verdict": "nisar | sentinel1 | undecidable", "cause": "narrow_channel", "reviewer": "", "date": "", "note": ""}
```

#### 22. Near Alvarães: NISAR links it, Sentinel-1 does not

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

#### 23. Near Tauary: NISAR links it, Sentinel-1 does not; NISAR's route is wider

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

#### 24. Near São Antonio do Ipapucu: NISAR's route is wider

- Where: 1.5 km from São Antonio do Ipapucu (-64.78579, -3.37103)
- Zone: `shore_mixed_pixel`: within one pixel of the shore: a 20 m pixel holds both water and land
- Communities: São Antonio do Ipapucu, Vista Alegre
- Passes (3 cases): 2026-10-23_t161A
  - 2026-10-23_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.36887&lng=-64.78513&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-10-21T00%3A00%3A00.000Z&toTime=2026-10-21T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.36887&mlon=-64.78513#map=15/-3.36887/-64.78513) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.36887&lng=-64.78513&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-10-25T00%3A00%3A00.000Z&toTime=2026-10-25T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2026-10-23_t161A"], "community_ids": ["osm3986860652", "osm3986860653", "osm8583188413"], "verdict": "nisar | sentinel1 | undecidable", "cause": "shore_mixed_pixel", "reviewer": "", "date": "", "note": ""}
```

#### 25. Near Acarazinho: NISAR links it, Sentinel-1 does not

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

#### 26. Near Cupuacu: NISAR links it, Sentinel-1 does not

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

#### 27. Near Santa Tereza do Rio Cubua: NISAR links it, Sentinel-1 does not

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

#### 28. Near Sao Raimundo do Rio Cubua: NISAR links it, Sentinel-1 does not

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

#### 29. Near Rio Grande: NISAR links it, Sentinel-1 does not

- Where: 3.1 km from Rio Grande (-64.7071, -3.21416)
- Zone: `threshold`: backscatter within the margin of the water threshold: a small change of threshold flips it
- Communities: Caburinim de Baixo, São Francisco
- Passes (2 cases): 2026-07-07_t161A
  - 2026-07-07_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.21713&lng=-64.70287&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-07-06T00%3A00%3A00.000Z&toTime=2026-07-06T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.21713&mlon=-64.70287#map=15/-3.21713/-64.70287) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.21713&lng=-64.70287&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-07-09T00%3A00%3A00.000Z&toTime=2026-07-09T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2026-07-07_t161A"], "community_ids": ["osm3924302375", "osm3924302392"], "verdict": "nisar | sentinel1 | undecidable", "cause": "threshold", "reviewer": "", "date": "", "note": ""}
```

#### 30. Near Sao Joaquim do Içe: NISAR links it, Sentinel-1 does not; NISAR's route is wider

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

#### 31. Near São Raimundo: NISAR links it, Sentinel-1 does not

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

#### 32. Near Boca do Mamiraua: NISAR's route is wider

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

#### 33. Near Itapiranema: NISAR links it, Sentinel-1 does not; NISAR's route is wider

- Where: 5.1 km from Itapiranema (-64.85416, -3.38003)
- Zone: `threshold`: backscatter within the margin of the water threshold: a small change of threshold flips it
- Communities: Santa Luzia do Catuiri, Vila Sião
- Passes (2 cases): 2025-11-04_t097D, 2026-10-11_t161A
  - 2026-10-11_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.37751&lng=-64.85443&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-10-11T00%3A00%3A00.000Z&toTime=2026-10-11T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.37751&mlon=-64.85443#map=15/-3.37751/-64.85443) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.37751&lng=-64.85443&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-10-13T00%3A00%3A00.000Z&toTime=2026-10-13T23%3A59%3A59.999Z)
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.38255&lng=-64.85389&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.38255&mlon=-64.85389#map=15/-3.38255/-64.85389) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.38255&lng=-64.85389&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D", "2026-10-11_t161A"], "community_ids": ["osm3984833644", "osm3984835463"], "verdict": "nisar | sentinel1 | undecidable", "cause": "threshold", "reviewer": "", "date": "", "note": ""}
```

#### 34. Near Nova Esperança: NISAR links it, Sentinel-1 does not

- Where: 1.7 km from Nova Esperança (-64.88359, -3.46688)
- Zone: `threshold`: backscatter within the margin of the water threshold: a small change of threshold flips it
- Communities: Nova Esperança
- Passes (2 cases): 2026-10-11_t161A, 2026-10-23_t161A
  - 2026-10-23_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.46535&lng=-64.88467&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-10-21T00%3A00%3A00.000Z&toTime=2026-10-21T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.46535&mlon=-64.88467#map=15/-3.46535/-64.88467) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.46535&lng=-64.88467&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-10-25T00%3A00%3A00.000Z&toTime=2026-10-25T23%3A59%3A59.999Z)
  - 2026-10-11_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.46841&lng=-64.88251&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-10-11T00%3A00%3A00.000Z&toTime=2026-10-11T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.46841&mlon=-64.88251#map=15/-3.46841/-64.88251) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.46841&lng=-64.88251&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-10-13T00%3A00%3A00.000Z&toTime=2026-10-13T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2026-10-11_t161A", "2026-10-23_t161A"], "community_ids": ["osm8583554431"], "verdict": "nisar | sentinel1 | undecidable", "cause": "threshold", "reviewer": "", "date": "", "note": ""}
```

#### 35. Near Assunção: NISAR links it, Sentinel-1 does not

- Where: at Assunção (-64.90409, -3.11298)
- Zone: `narrow_channel`: reference channel narrower than 60 m
- Communities: Assunção
- Passes (1 cases): 2025-11-04_t097D
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.11298&lng=-64.90409&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.11298&mlon=-64.90409#map=15/-3.11298/-64.90409) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.11298&lng=-64.90409&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D"], "community_ids": ["osm3984833608"], "verdict": "nisar | sentinel1 | undecidable", "cause": "narrow_channel", "reviewer": "", "date": "", "note": ""}
```

#### 36. Near Caburinim de Baixo: NISAR links it, Sentinel-1 does not

- Where: at Caburinim de Baixo (-64.68438, -3.23497)
- Zone: `narrow_channel`: reference channel narrower than 60 m
- Communities: Caburinim de Baixo
- Passes (1 cases): 2025-11-04_t097D
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.23497&lng=-64.68438&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.23497&mlon=-64.68438#map=15/-3.23497/-64.68438) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.23497&lng=-64.68438&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D"], "community_ids": ["osm3924302375"], "verdict": "nisar | sentinel1 | undecidable", "cause": "narrow_channel", "reviewer": "", "date": "", "note": ""}
```

#### 37. Near Caburinim de Cima: NISAR links it, Sentinel-1 does not

- Where: at Caburinim de Cima (-64.77525, -3.15922)
- Zone: `narrow_channel`: reference channel narrower than 60 m
- Communities: Caburinim de Cima
- Passes (1 cases): 2025-11-04_t097D
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.15922&lng=-64.77525&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.15922&mlon=-64.77525#map=15/-3.15922/-64.77525) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.15922&lng=-64.77525&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D"], "community_ids": ["osm3924302376"], "verdict": "nisar | sentinel1 | undecidable", "cause": "narrow_channel", "reviewer": "", "date": "", "note": ""}
```

#### 38. Near São João do Mulato: NISAR links it, Sentinel-1 does not

- Where: 3.9 km from São João do Mulato (-64.96171, -3.55463)
- Zone: `unexplained`: no rule explains it
- Communities: Campo Novo
- Passes (1 cases): 2025-11-04_t097D
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.55463&lng=-64.96171&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.55463&mlon=-64.96171#map=15/-3.55463/-64.96171) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.55463&lng=-64.96171&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D"], "community_ids": ["osm3984833612"], "verdict": "nisar | sentinel1 | undecidable", "cause": "unexplained", "reviewer": "", "date": "", "note": ""}
```

#### 39. Near Canaria: NISAR links it, Sentinel-1 does not

- Where: at Canaria (-64.92806, -3.09596)
- Zone: `narrow_channel`: reference channel narrower than 60 m
- Communities: Canaria
- Passes (1 cases): 2025-11-04_t097D
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.09596&lng=-64.92806&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.09596&mlon=-64.92806#map=15/-3.09596/-64.92806) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.09596&lng=-64.92806&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D"], "community_ids": ["osm3984833614"], "verdict": "nisar | sentinel1 | undecidable", "cause": "narrow_channel", "reviewer": "", "date": "", "note": ""}
```

#### 40. Near Coadi: NISAR links it, Sentinel-1 does not

- Where: at Coadi (-64.99816, -3.07035)
- Zone: `narrow_channel`: reference channel narrower than 60 m
- Communities: Coadi
- Passes (1 cases): 2025-11-04_t097D
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.07035&lng=-64.99816&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.07035&mlon=-64.99816#map=15/-3.07035/-64.99816) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.07035&lng=-64.99816&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D"], "community_ids": ["osm3984712003"], "verdict": "nisar | sentinel1 | undecidable", "cause": "narrow_channel", "reviewer": "", "date": "", "note": ""}
```

#### 41. Near Comunidade São Francisco do Aratamã: NISAR links it, Sentinel-1 does not

- Where: at Comunidade São Francisco do Aratamã (-64.65657, -3.29792)
- Zone: `narrow_channel`: reference channel narrower than 60 m
- Communities: Comunidade São Francisco do Aratamã
- Passes (1 cases): 2025-11-04_t097D
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.29792&lng=-64.65657&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.29792&mlon=-64.65657#map=15/-3.29792/-64.65657) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.29792&lng=-64.65657&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D"], "community_ids": ["osm9755637967"], "verdict": "nisar | sentinel1 | undecidable", "cause": "narrow_channel", "reviewer": "", "date": "", "note": ""}
```

#### 42. Near Gloria: NISAR links it, Sentinel-1 does not

- Where: at Gloria (-64.66019, -3.33153)
- Zone: `narrow_channel`: reference channel narrower than 60 m
- Communities: Gloria
- Passes (1 cases): 2025-11-04_t097D
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.33153&lng=-64.66019&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.33153&mlon=-64.66019#map=15/-3.33153/-64.66019) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.33153&lng=-64.66019&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D"], "community_ids": ["osm3986860573"], "verdict": "nisar | sentinel1 | undecidable", "cause": "narrow_channel", "reviewer": "", "date": "", "note": ""}
```

#### 43. Near Itapiranema: NISAR's route is wider

- Where: 3.3 km from Itapiranema (-64.79899, -3.33017)
- Zone: `unexplained`: no rule explains it
- Communities: Itapiranema
- Passes (1 cases): 2025-11-04_t097D
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.33017&lng=-64.79899&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.33017&mlon=-64.79899#map=15/-3.33017/-64.79899) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.33017&lng=-64.79899&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D"], "community_ids": ["osm3984833624"], "verdict": "nisar | sentinel1 | undecidable", "cause": "unexplained", "reviewer": "", "date": "", "note": ""}
```

#### 44. Near Jaquiri: NISAR links it, Sentinel-1 does not

- Where: at Jaquiri (-64.87807, -3.0948)
- Zone: `narrow_channel`: reference channel narrower than 60 m
- Communities: Jaquiri
- Passes (1 cases): 2025-11-04_t097D
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.09480&lng=-64.87807&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.09480&mlon=-64.87807#map=15/-3.09480/-64.87807) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.09480&lng=-64.87807&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D"], "community_ids": ["osm3984712016"], "verdict": "nisar | sentinel1 | undecidable", "cause": "narrow_channel", "reviewer": "", "date": "", "note": ""}
```

#### 45. Near Juruama: NISAR links it, Sentinel-1 does not

- Where: at Juruama (-64.88039, -3.13586)
- Zone: `narrow_channel`: reference channel narrower than 60 m
- Communities: Juruama
- Passes (1 cases): 2025-11-04_t097D
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.13586&lng=-64.88039&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.13586&mlon=-64.88039#map=15/-3.13586/-64.88039) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.13586&lng=-64.88039&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D"], "community_ids": ["osm3984833628"], "verdict": "nisar | sentinel1 | undecidable", "cause": "narrow_channel", "reviewer": "", "date": "", "note": ""}
```

#### 46. Near Laranjal: NISAR links it, Sentinel-1 does not

- Where: at Laranjal (-64.77764, -3.23884)
- Zone: `narrow_channel`: reference channel narrower than 60 m
- Communities: Laranjal
- Passes (1 cases): 2025-11-04_t097D
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.23884&lng=-64.77764&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.23884&mlon=-64.77764#map=15/-3.23884/-64.77764) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.23884&lng=-64.77764&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D"], "community_ids": ["osm3984833629"], "verdict": "nisar | sentinel1 | undecidable", "cause": "narrow_channel", "reviewer": "", "date": "", "note": ""}
```

#### 47. Near Manixi: NISAR links it, Sentinel-1 does not

- Where: at Manixi (-64.75932, -3.23261)
- Zone: `narrow_channel`: reference channel narrower than 60 m
- Communities: Manixi
- Passes (1 cases): 2025-11-04_t097D
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.23261&lng=-64.75932&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.23261&mlon=-64.75932#map=15/-3.23261/-64.75932) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.23261&lng=-64.75932&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D"], "community_ids": ["osm3984833630"], "verdict": "nisar | sentinel1 | undecidable", "cause": "narrow_channel", "reviewer": "", "date": "", "note": ""}
```

#### 48. Near São Sebastião do Ture: NISAR links it, Sentinel-1 does not

- Where: 3.2 km from São Sebastião do Ture (-64.87441, -3.43313)
- Zone: `unexplained`: no rule explains it
- Communities: Mutum
- Passes (1 cases): 2025-11-04_t097D
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.43313&lng=-64.87441&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.43313&mlon=-64.87441#map=15/-3.43313/-64.87441) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.43313&lng=-64.87441&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D"], "community_ids": ["osm3986860596"], "verdict": "nisar | sentinel1 | undecidable", "cause": "unexplained", "reviewer": "", "date": "", "note": ""}
```

#### 49. Near Pau Rosa: NISAR links it, Sentinel-1 does not

- Where: at Pau Rosa (-64.76165, -3.06296)
- Zone: `narrow_channel`: reference channel narrower than 60 m
- Communities: Pau Rosa
- Passes (1 cases): 2025-11-04_t097D
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.06296&lng=-64.76165&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.06296&mlon=-64.76165#map=15/-3.06296/-64.76165) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.06296&lng=-64.76165&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D"], "community_ids": ["osm3924302384"], "verdict": "nisar | sentinel1 | undecidable", "cause": "narrow_channel", "reviewer": "", "date": "", "note": ""}
```

#### 50. Near Perseverança: NISAR links it, Sentinel-1 does not

- Where: at Perseverança (-64.79171, -3.22402)
- Zone: `narrow_channel`: reference channel narrower than 60 m
- Communities: Perseverança
- Passes (1 cases): 2025-11-04_t097D
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.22402&lng=-64.79171&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.22402&mlon=-64.79171#map=15/-3.22402/-64.79171) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.22402&lng=-64.79171&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D"], "community_ids": ["osm3984833640"], "verdict": "nisar | sentinel1 | undecidable", "cause": "narrow_channel", "reviewer": "", "date": "", "note": ""}
```

#### 51. Near Porto Natal: NISAR links it, Sentinel-1 does not

- Where: at Porto Natal (-64.6635, -3.26469)
- Zone: `narrow_channel`: reference channel narrower than 60 m
- Communities: Porto Natal
- Passes (1 cases): 2025-11-04_t097D
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.26469&lng=-64.66350&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.26469&mlon=-64.66350#map=15/-3.26469/-64.66350) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.26469&lng=-64.66350&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D"], "community_ids": ["osm3924302386"], "verdict": "nisar | sentinel1 | undecidable", "cause": "narrow_channel", "reviewer": "", "date": "", "note": ""}
```

#### 52. Near Buna: NISAR links it, Sentinel-1 does not

- Where: 2.7 km from Buna (-65.02399, -3.02381)
- Zone: `threshold`: backscatter within the margin of the water threshold: a small change of threshold flips it
- Communities: Punã
- Passes (1 cases): 2025-11-04_t097D
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.02381&lng=-65.02399&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.02381&mlon=-65.02399#map=15/-3.02381/-65.02399) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.02381&lng=-65.02399&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D"], "community_ids": ["osm3984712024"], "verdict": "nisar | sentinel1 | undecidable", "cause": "threshold", "reviewer": "", "date": "", "note": ""}
```

#### 53. Near Rio Grande: NISAR links it, Sentinel-1 does not

- Where: at Rio Grande (-64.72871, -3.19704)
- Zone: `narrow_channel`: reference channel narrower than 60 m
- Communities: Rio Grande
- Passes (1 cases): 2025-11-04_t097D
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.19704&lng=-64.72871&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.19704&mlon=-64.72871#map=15/-3.19704/-64.72871) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.19704&lng=-64.72871&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D"], "community_ids": ["osm3924302388"], "verdict": "nisar | sentinel1 | undecidable", "cause": "narrow_channel", "reviewer": "", "date": "", "note": ""}
```

#### 54. Near Santa Elena: NISAR links it, Sentinel-1 does not

- Where: at Santa Elena (-64.73364, -3.24712)
- Zone: `narrow_channel`: reference channel narrower than 60 m
- Communities: Santa Elena
- Passes (1 cases): 2025-11-04_t097D
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.24712&lng=-64.73364&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.24712&mlon=-64.73364#map=15/-3.24712/-64.73364) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.24712&lng=-64.73364&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D"], "community_ids": ["osm3984833643"], "verdict": "nisar | sentinel1 | undecidable", "cause": "narrow_channel", "reviewer": "", "date": "", "note": ""}
```

#### 55. Near São Francisco: NISAR links it, Sentinel-1 does not

- Where: at São Francisco (-64.62125, -3.2814)
- Zone: `narrow_channel`: reference channel narrower than 60 m
- Communities: São Francisco
- Passes (1 cases): 2025-11-04_t097D
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.28140&lng=-64.62125&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.28140&mlon=-64.62125#map=15/-3.28140/-64.62125) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.28140&lng=-64.62125&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D"], "community_ids": ["osm3924302392"], "verdict": "nisar | sentinel1 | undecidable", "cause": "narrow_channel", "reviewer": "", "date": "", "note": ""}
```

#### 56. Near São Rafael: NISAR links it, Sentinel-1 does not

- Where: at São Rafael (-64.72076, -3.27716)
- Zone: `narrow_channel`: reference channel narrower than 60 m
- Communities: São Rafael
- Passes (1 cases): 2025-11-04_t097D
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.27716&lng=-64.72076&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.27716&mlon=-64.72076#map=15/-3.27716/-64.72076) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.27716&lng=-64.72076&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D"], "community_ids": ["osm3984833656"], "verdict": "nisar | sentinel1 | undecidable", "cause": "narrow_channel", "reviewer": "", "date": "", "note": ""}
```

#### 57. Near Tapieira: NISAR links it, Sentinel-1 does not

- Where: at Tapieira (-64.7743, -3.04973)
- Zone: `narrow_channel`: reference channel narrower than 60 m
- Communities: Tapieira
- Passes (1 cases): 2025-11-04_t097D
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.04973&lng=-64.77430&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.04973&mlon=-64.77430#map=15/-3.04973/-64.77430) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.04973&lng=-64.77430&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D"], "community_ids": ["osm3924267833"], "verdict": "nisar | sentinel1 | undecidable", "cause": "narrow_channel", "reviewer": "", "date": "", "note": ""}
```

#### 58. Near Vila Nova: NISAR's route is wider

- Where: 1.0 km from Vila Nova (-64.69009, -3.32531)
- Zone: `shore_mixed_pixel`: within one pixel of the shore: a 20 m pixel holds both water and land
- Communities: Vila Nova
- Passes (1 cases): 2025-11-04_t097D
  - 2025-11-04_t097D: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.32531&lng=-64.69009&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-05T00%3A00%3A00.000Z&toTime=2025-11-05T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.32531&mlon=-64.69009#map=15/-3.32531/-64.69009) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.32531&lng=-64.69009&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2025-11-04T00%3A00%3A00.000Z&toTime=2025-11-04T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2025-11-04_t097D"], "community_ids": ["osm3986860650"], "verdict": "nisar | sentinel1 | undecidable", "cause": "shore_mixed_pixel", "reviewer": "", "date": "", "note": ""}
```

#### 59. Near Sao Joaquim do Içe: NISAR links it, Sentinel-1 does not

- Where: 2.3 km from Sao Joaquim do Içe (-64.68631, -3.25727)
- Zone: `threshold`: backscatter within the margin of the water threshold: a small change of threshold flips it
- Communities: Porto Natal
- Passes (1 cases): 2026-07-07_t161A
  - 2026-07-07_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.25727&lng=-64.68631&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-07-06T00%3A00%3A00.000Z&toTime=2026-07-06T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.25727&mlon=-64.68631#map=15/-3.25727/-64.68631) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.25727&lng=-64.68631&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-07-09T00%3A00%3A00.000Z&toTime=2026-07-09T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2026-07-07_t161A"], "community_ids": ["osm3924302386"], "verdict": "nisar | sentinel1 | undecidable", "cause": "threshold", "reviewer": "", "date": "", "note": ""}
```

#### 60. Near Monte Sinai: NISAR's route is wider

- Where: 1.0 km from Monte Sinai (-64.56265, -3.16673)
- Zone: `narrow_channel`: reference channel narrower than 60 m
- Communities: Urcui
- Passes (1 cases): 2026-10-11_t161A
  - 2026-10-11_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.16673&lng=-64.56265&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-10-11T00%3A00%3A00.000Z&toTime=2026-10-11T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.16673&mlon=-64.56265#map=15/-3.16673/-64.56265) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.16673&lng=-64.56265&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-10-13T00%3A00%3A00.000Z&toTime=2026-10-13T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2026-10-11_t161A"], "community_ids": ["osm3924302396"], "verdict": "nisar | sentinel1 | undecidable", "cause": "narrow_channel", "reviewer": "", "date": "", "note": ""}
```

#### 61. Near São Antonio do Ipapucu: NISAR links it, Sentinel-1 does not

- Where: 6.7 km from São Antonio do Ipapucu (-64.74049, -3.35303)
- Zone: `shore_mixed_pixel`: within one pixel of the shore: a 20 m pixel holds both water and land
- Communities: Bacuri
- Passes (1 cases): 2026-10-23_t161A
  - 2026-10-23_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.35303&lng=-64.74049&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-10-21T00%3A00%3A00.000Z&toTime=2026-10-21T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.35303&mlon=-64.74049#map=15/-3.35303/-64.74049) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.35303&lng=-64.74049&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-10-25T00%3A00%3A00.000Z&toTime=2026-10-25T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2026-10-23_t161A"], "community_ids": ["osm3986858845"], "verdict": "nisar | sentinel1 | undecidable", "cause": "shore_mixed_pixel", "reviewer": "", "date": "", "note": ""}
```

#### 62. Near São Raimundo do Sapia: NISAR links it, Sentinel-1 does not

- Where: 4.8 km from São Raimundo do Sapia (-65.01967, -3.70871)
- Zone: `threshold`: backscatter within the margin of the water threshold: a small change of threshold flips it
- Communities: Campo Novo
- Passes (1 cases): 2026-10-23_t161A
  - 2026-10-23_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.70871&lng=-65.01967&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-10-21T00%3A00%3A00.000Z&toTime=2026-10-21T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.70871&mlon=-65.01967#map=15/-3.70871/-65.01967) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.70871&lng=-65.01967&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-10-25T00%3A00%3A00.000Z&toTime=2026-10-25T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2026-10-23_t161A"], "community_ids": ["osm3984833612"], "verdict": "nisar | sentinel1 | undecidable", "cause": "threshold", "reviewer": "", "date": "", "note": ""}
```

#### 63. Near São João do Mulato: NISAR links it, Sentinel-1 does not

- Where: 0.7 km from São João do Mulato (-64.99141, -3.55805)
- Zone: `smooth_ground`: seasonal ground (bank, mud, sand) clearly dark in L-band
- Communities: Caru
- Passes (1 cases): 2026-10-23_t161A
  - 2026-10-23_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.55805&lng=-64.99141&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-10-21T00%3A00%3A00.000Z&toTime=2026-10-21T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.55805&mlon=-64.99141#map=15/-3.55805/-64.99141) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.55805&lng=-64.99141&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-10-25T00%3A00%3A00.000Z&toTime=2026-10-25T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2026-10-23_t161A"], "community_ids": ["osm3984833616"], "verdict": "nisar | sentinel1 | undecidable", "cause": "smooth_ground", "reviewer": "", "date": "", "note": ""}
```

#### 64. Near Divino Estirito Santo: NISAR links it, Sentinel-1 does not

- Where: 1.1 km from Divino Estirito Santo (-64.83949, -3.42791)
- Zone: `threshold`: backscatter within the margin of the water threshold: a small change of threshold flips it
- Communities: Divino Estirito Santo
- Passes (1 cases): 2026-10-23_t161A
  - 2026-10-23_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.42791&lng=-64.83949&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-10-21T00%3A00%3A00.000Z&toTime=2026-10-21T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.42791&mlon=-64.83949#map=15/-3.42791/-64.83949) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.42791&lng=-64.83949&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-10-25T00%3A00%3A00.000Z&toTime=2026-10-25T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2026-10-23_t161A"], "community_ids": ["osm3986860568"], "verdict": "nisar | sentinel1 | undecidable", "cause": "threshold", "reviewer": "", "date": "", "note": ""}
```

#### 65. Near Mutum: NISAR links it, Sentinel-1 does not

- Where: 3.2 km from Mutum (-64.90987, -3.49487)
- Zone: `shore_mixed_pixel`: within one pixel of the shore: a 20 m pixel holds both water and land
- Communities: Mutum
- Passes (1 cases): 2026-10-23_t161A
  - 2026-10-23_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.49487&lng=-64.90987&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-10-21T00%3A00%3A00.000Z&toTime=2026-10-21T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.49487&mlon=-64.90987#map=15/-3.49487/-64.90987) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.49487&lng=-64.90987&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-10-25T00%3A00%3A00.000Z&toTime=2026-10-25T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2026-10-23_t161A"], "community_ids": ["osm3986860596"], "verdict": "nisar | sentinel1 | undecidable", "cause": "shore_mixed_pixel", "reviewer": "", "date": "", "note": ""}
```

#### 66. Near São Raimundo de Baixo: NISAR links it, Sentinel-1 does not

- Where: 3.3 km from São Raimundo de Baixo (-64.94983, -3.48785)
- Zone: `unexplained`: no rule explains it
- Communities: Vila Sião
- Passes (1 cases): 2026-10-23_t161A
  - 2026-10-23_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.48785&lng=-64.94983&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-10-21T00%3A00%3A00.000Z&toTime=2026-10-21T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-3.48785&mlon=-64.94983#map=15/-3.48785/-64.94983) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-3.48785&lng=-64.94983&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-10-25T00%3A00%3A00.000Z&toTime=2026-10-25T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2026-10-23_t161A"], "community_ids": ["osm3984835463"], "verdict": "nisar | sentinel1 | undecidable", "cause": "unexplained", "reviewer": "", "date": "", "note": ""}
```

#### 67. Near Novo Amparo: Sentinel-1 links it, NISAR does not

- Where: 2.2 km from Novo Amparo (-64.80613, -2.90327)
- Zone: `shore_mixed_pixel`: within one pixel of the shore: a 20 m pixel holds both water and land
- Communities: Novo Amparo
- Passes (3 cases): 2026-07-07_t161A, 2026-08-24_t161A, 2026-10-23_t161A
  - 2026-10-23_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-2.90339&lng=-64.80619&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-10-21T00%3A00%3A00.000Z&toTime=2026-10-21T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-2.90339&mlon=-64.80619#map=15/-2.90339/-64.80619) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-2.90339&lng=-64.80619&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-10-25T00%3A00%3A00.000Z&toTime=2026-10-25T23%3A59%3A59.999Z)
  - 2026-08-24_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-2.90321&lng=-64.80619&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-08-25T00%3A00%3A00.000Z&toTime=2026-08-25T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-2.90321&mlon=-64.80619#map=15/-2.90321/-64.80619) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-2.90321&lng=-64.80619&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-08-26T00%3A00%3A00.000Z&toTime=2026-08-26T23%3A59%3A59.999Z)
  - 2026-07-07_t161A: [Sentinel-2](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-2.90321&lng=-64.80601&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2026-07-06T00%3A00%3A00.000Z&toTime=2026-07-06T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR) · [map](https://www.openstreetmap.org/?mlat=-2.90321&mlon=-64.80601#map=15/-2.90321/-64.80601) · [Sentinel-1](https://browser.dataspace.copernicus.eu/?zoom=15&lat=-2.90321&lng=-64.80601&themeId=DEFAULT-THEME&datasetId=S1_CDAS_IW_VVVH&fromTime=2026-07-09T00%3A00%3A00.000Z&toTime=2026-07-09T23%3A59%3A59.999Z)
- Verdict to add to `processing/benchmark/crosscheck_reviews.json`:

```json
{"passes": ["2026-07-07_t161A", "2026-08-24_t161A", "2026-10-23_t161A"], "community_ids": ["osm3924267794"], "verdict": "nisar | sentinel1 | undecidable", "cause": "shore_mixed_pixel", "reviewer": "", "date": "", "note": ""}
```

## River gauge

ANA telemetry, station 12900001.

| Correlation | Spearman rho | Passes | Expected sign |
|---|---|---|---|
| water area vs level | 0.968 | 15 | + |
| lost routes vs level | -0.759 | 15 | - |

## Field and report checks

| Community | Expected | Kind | Found | Passes judged | Correct | Source |
|---|---|---|---|---|---|---|
| Caiambé | linked | sanity | True | 14 | 14 | Team plausibility check (docs/river-monitor.md): settlement on the Solimões main channel, used as the boat landing in the 2023 and 2024 droughts. Not an observation of 2026. |
| Alvarães | linked | sanity | True | 14 | 14 | Team plausibility check (docs/river-monitor.md): municipal seat reached through its port; no 2026 report of the town being cut off was found. Not an observation of 2026. |

## Community classes

| monitored | unresolved | inland | no_data |
|---|---|---|---|
| 130 | 39 | 35 | 0 |
