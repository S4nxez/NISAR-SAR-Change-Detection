# Accuracy review of the isolated communities monitor (Tefé)

> **Status (2026-11-13): historical record of the review of 2026-11-10.** It describes the method as it was then.
> The current method is in [river-monitor.md](river-monitor.md), and every change made since is recorded in an
> ADR and measured with the [benchmark](river-monitor-benchmark.md). What became of each option:
>
> | Option | Outcome |
> |---|---|
> | M1 water under vegetation | Own class, never a route: [ADR-004](decisions/ADR-004-river-monitor-water-under-vegetation.md) (routing accepted, detection thresholds proposed) |
> | M2 per-pass threshold | Rejected: [ADR-003](decisions/ADR-003-river-monitor-per-pass-threshold.md); the code stays, off |
> | M4 edge-preserving filter | Refined Lee filter: [ADR-002](decisions/ADR-002-river-monitor-refined-lee-filter.md); thresholds retuned to −16 / −14 dB: [ADR-005](decisions/ADR-005-river-monitor-thresholds-for-refined-lee.md). The multitemporal filter was not built |
> | M6 permanent water reference | Partly: JRC occurrence marks the seasonal ground of the low-water rule ([ADR-007](decisions/ADR-007-river-monitor-low-water-beds.md)), not as a prior against wind |
> | M8 fusion | Sentinel-1 judges drained beds at low water ([ADR-007](decisions/ADR-007-river-monitor-low-water-beds.md)); Sentinel-2 and OPERA DSWx are benchmark references; SWOT is not used |
> | M3, M5, M7, C1–C6 | Open |
> | §3.1 water mask validation | Built as the benchmark (MNDWI with an Otsu threshold, ≤ 2 days, then a consensus of references) |
> | §3.2 ground validation | Open: no dated per-community field data yet |
> | §5 open decisions | 1: own class, but never a route rather than "at risk" (ADR-004); 2: fixed threshold (ADR-003); 5: adopted by exam 1 of the benchmark; 3, 4 and 6: open |
>
> Found later and not covered here: swath-edge fill below −40 dB ([ADR-001](decisions/ADR-001-river-monitor-fill-is-no-data.md))
> and the last kilometre of the swath ([ADR-006](decisions/ADR-006-river-monitor-swath-edge-margin.md)) are no data.

Review of the code of the `feature/river-lifeline-monitor` branch (`processing/src/lifeline/`, area
`processing/areas/tefe.json`) prompted by a visual discrepancy: areas our map shows **without water** appear
**clearly with water** in the Sentinel-2 NDWI.

The document has three parts:

1. Why it can happen: causes in the water mask, in the connectivity and in the comparison itself.
2. How to improve accuracy: options with their expected effect and a recommendation.
3. How to validate with real data collected on the ground.

At the end there is a short procedure to diagnose each discrepant area, and the decisions that remain open.

---

## 0. How the monitor decides today (summary)

| Step | What it does | Parameter | Where |
|---|---|---|---|
| Read | Only **HH** from GCOV (frequency A), in dB | — | `analysis/radar.py:read_pass` |
| Speckle | Box mean over ~60 m (3×3 pixels at 20 m) in linear power | `speckle_m: 60` | `radar.py:speckle_filter` |
| Resampling | Nearest neighbour onto a fixed lon/lat grid of 0.00018° (~20 m) | `step_deg` | `radar.py:resample_into` |
| Water | `HH < −15 dB`, plus the pixels `< −12 dB` touching that water (hysteresis) | `water_db`, `water_db_weak` | `analysis/water.py:water_mask` |
| Clean-up | Specks < 1 ha (25 px) are removed and holes < 2 ha (50 px) are filled | `MIN_WATER_PX`, `MIN_HOLE_PX` | `water.py` |
| Route | Connected components by width (0, 40, 60, 100, 200, 400 m) between the community's access point (1 km radius) and Tefé (2 km radius) | `widths_m`, `access_radius_m` | `water.py:bottlenecks` |
| Status | connected ≥ 60 m; at risk < 60 m; isolated with no route or no water within 1 km | `safe_width_m` | `water.py:route_status` |
| Confirmation | Isolation is confirmed only if the previous pass with data agrees | — | `output/catalog.py:classify_communities` |
| Classes | `inland` (never water within 1 km), `unresolved` (never connected by ≥ 40 m), `monitored` | — | `catalog.py:community_class` |

The thresholds were tuned on **only two passes** (7 July and 23 October 2026) and are applied the same to every
pass, track and incidence angle.

---

## 1. Why the map says "no water" where NDWI sees water

The causes are ordered from most to least likely for the case described. Each one has a **signature** that makes it
recognisable in `radar.webp` and in Sentinel-2 itself.

### 1.1 Causes in the water mask (radar)

**A. Water with vegetation: floating macrophytes, emergent grass, flooded forest (várzea/igapó).**
This is the most likely cause in várzea lakes and channels such as Lake Tefé.
- In L band, a sheet of water with stems above it creates a *double bounce* (water → stem → sensor) that returns
  **more** echo than dry forest (often between −8 and 0 dB in HH). With a threshold of `HH < −15 dB`, these pixels
  can never be water.
- Macrophyte meadows (canarana, *Paspalum*, *Echinochloa*) cover large areas of the várzea lakes at low and medium
  water. NDWI may mark water at their edges and in clearings, or where the vegetation is sparse.
- **Signature:** in `radar.webp` the area looks **brighter** than its surroundings, not mid grey. In Sentinel-2 natural
  colour it looks green or mixed.
- **Consequence for routes:** it depends on the case. A channel covered by macrophytes may still be navigable by
  canoe or long-tail boat (rabeta), or it may be closed. Today it is always treated as land.

**B. Wind or rain over large open surfaces.**
- Wind ripples the water and raises the HH echo, even more in the *near range* (low incidence). The hysteresis
  (−12 dB connected to −15 dB) only rescues rippled water that touches calm water. If the whole lake is rippled, or
  if a gust crosses the whole channel, it is lost.
- Heavy rain cells also roughen the water in L band, though less than in C band.
- **Signature:** uniform mid grey in `radar.webp`, sometimes with bands or a sharp boundary (a gust front). It
  usually affects a single pass: the previous and the next pass of the same track are fine.

**C. Channels narrower than the effective resolution.**
- Sentinel-2 resolves 10 m; we work at 20 m and also filter with a 60 m box. A 20–40 m channel gets mixed with the
  very bright forest shores, and its mean over the box rises above −15 dB.
- If some fragment under 1 ha survives, `MIN_WATER_PX` deletes it. A narrow channel thus becomes "no water", even if
  it is only cut in places.
- For widths ≥ 40 m the connectivity uses 4 neighbours (only the "any water" level uses 8). A 2–3 pixel channel
  running diagonally can break apart at the 40 m level.
- **Signature:** NDWI shows a continuous thread of water and our `water.png` shows loose pieces or nothing.

**D. Fixed threshold against incidence angle and track.**
- NISAR covers about 33–47° of incidence. The echo of water depends strongly on the angle: at low incidence (*near
  range*) water is brighter and can exceed −15 dB even without much wind.
- Track 161 (ascending) and the descending track see the same area from different angles. The same threshold is not
  equally good for both.
- **Signature:** the discrepancy concentrates on one side of the swath or on a single track.

**E. Sandbanks, wet mud and beaches (the opposite error).**
Smooth wet mud can give a low echo and come out as water (false water). It must be taken into account when the error
is measured in both directions, because it usually happens in the same low-water areas.

**F. Provisional data.**
GCOV is *provisional* (and some early passes *beta*). The radiometric calibration may change with the validated
reprocessing of late 2026. If it shifts by 1–2 dB, the −15 dB threshold no longer means the same.

### 1.2 Causes in the connectivity (why a community comes out isolated although there is water)

Here the water map can be right and the community can still come out isolated.

| Problem | Effect | Where |
|---|---|---|
| **The area is a 55 km circle and nothing outside it is water.** A real route that leaves the circle along the Solimões and comes back in is cut | False isolated, mostly near the edge | `pipeline.py:process_pass` (`db[~area_mask] = nan`), `water.py:connectivity` |
| **A single hub (Tefé).** A community supplied from Alvarães, Uarini or Coari, or directly from the Solimões, is measured against Tefé | False isolated with respect to its real centre | `tefe.json:hub` |
| **OSM position of the settlement.** The point may be at the centre of the village, or misplaced; the *snap* to landings only covers 500 m for villages | Distance to water > 1 km → isolated for "no water nearby" | `sources/places.py:assign_access` |
| **Communities missing from OSM** (Vila Bastos, São Francisco do Itauba, Porto Praia de Baixo, already found) | Not evaluated: invisible false negatives | `places.py:fetch_places` |
| **`unresolved` class.** If a community was never connected by ≥ 40 m on any pass, it leaves the counts. With thresholds that are too strict (causes A–D) real communities end up here | The total of isolated communities falls short | `catalog.py:community_class` |
| **Confirmation with the previous pass**, even if it is from another track with another angle and up to 12 days earlier | One pass of delay to confirm; with mixed tracks it may confirm or cancel because of geometry differences | `catalog.py:classify_communities` |
| **Width does not measure depth.** A 100 m channel with 40 cm of draught comes out "connected" | False connected (the most serious error for the user) | Limitation of the method |
| **Width estimated one pixel short** (conservative on purpose) | Early warnings, more "at risk" | `water.py:width_mask` |

### 1.3 Causes in the comparison with Sentinel-2

Before concluding that the radar is wrong, these three must be ruled out:

- **Different dates.** In full recession the Solimões at Tefé can fall 10 to 30 cm a day. With almost permanent
  clouds, the closest clear Sentinel-2 image may be weeks away from the NISAR pass. Comparing needs the same week,
  better ±1–2 days.
- **NDWI is not a water mask.** McFeeters' NDWI (green−NIR) gives positive values on very wet soil, cloud shadows and
  some dark surfaces. The colour ramps of EO Browser and Copernicus Browser paint in blue values that pass no
  validated threshold. Besides, the black water of Lake Tefé reflects very little and stays close to 0, while the
  turbid white water of the Solimões behaves differently. It is better to use **MNDWI** (green−SWIR1) with a threshold
  chosen per image (Otsu) and the cloud and shadow mask (SCL or s2cloudless).
- **Geometric registration.** Our grid is lon/lat with nearest neighbour; Sentinel-2 is in UTM 20S at 10 m. A 1–2
  pixel offset is irrelevant on the lake, but it decides whether a 30 m channel matches or not.

---

## 2. How to improve accuracy

Each option gives the expected effect and the cost. The recommendation is at the end of the section.

### 2.1 Water mask

| # | Option | Addresses | Expected effect | Cost |
|---|---|---|---|---|
| M1 | **Add HV and a "water with vegetation" class**: high HH with a high HH/HV ratio (*double bounce*). Open water = low HH and HV | A | Large in várzea lakes; removes the main false "no water" | Low: GCOV DHDH already carries HVHV. Read another band and add a rule |
| M2 | **Adaptive threshold per pass** (Otsu or Kittler-Illingworth on bimodal tiles, *split-based*), bounded to a range, e.g. [−20, −12] dB | B, D, F | Medium to large; no longer depends on two calibration passes or on the provisional calibration changing | Low |
| M3 | **Normalise by incidence angle** (GCOV carries the incidence metadata cubes) or use thresholds per track | D | Medium in the *near range* | Low to medium |
| M4 | **Edge-preserving speckle filter** (refined Lee or Gamma-MAP) or a **multitemporal** one (Quegan, with the passes of the same track) instead of the 60 m box | C | Medium: recovers 30–60 m channels | Medium |
| M5 | **Do not delete fragments aligned with a known channel**: use the OSM waterway network (`waterway=*`) and the GRWL/SWORD centrelines as a guide to join pieces | C | Medium in narrow channels; risk of inventing connections if the channel is really dry | Medium |
| M6 | **Permanent water reference map** (JRC Global Surface Water) as prior information: water that always was water and disappears on a single pass becomes "doubtful", not land | B | Medium; reduces cuts by wind | Low |
| M7 | **Trained classifier** (Random Forest or GBM on HH, HV, HH/HV, texture, incidence and HAND) with labels from cloud-free Sentinel-2 MNDWI of matching dates | A–E | The largest in the medium term | High: needs the validation set of section 3.1 |
| M8 | **Fusion with other sources when available**: cloud-free Sentinel-2/HLS, Sentinel-1 (C band), **SWOT** (water mask and river and lake heights; it gives *relative depth*, which width does not) | All, and depth | Large for validation and for draught | Medium to high |

### 2.2 Connectivity

| # | Option | Effect |
|---|---|---|
| C1 | **Buffer zone outside the circle for route computation** (e.g. +20 km) even if only the circle is shown | Removes false isolated communities near the edge |
| C2 | **Several hubs or the main channel as destination**: connected if it reaches Tefé, another municipality or the main channel of the Solimões | Reflects how communities are really supplied |
| C3 | **8-connectivity at the width levels too**, or check the width on the channel skeleton | Avoids cuts in diagonal channels |
| C4 | **Confirm with the previous pass of the same track**, or require 2 of 3 passes | Fewer false isolations from geometry differences |
| C5 | **Complete and correct the list of communities** with IBGE (Base de Localidades, Censo 2022), the registers of the RDS Mamirauá and Amanã, FUNAI/DSEI, and the real landings collected in the field | Reduces the invisible false negatives |
| C6 | **Draught**: cross the width with the gauge level (ANA) and, if available, with SWOT heights or bathymetry, to define "at risk" by estimated depth and not only by width | Addresses the most serious error (false connected) |

### 2.3 Recommendation

1. **Diagnose first** the discrepant areas with the procedure of section 4. That way we will know which cause
   dominates before touching thresholds.
2. Then, by cost and benefit: **M1 + M2 + C1** (cheap and probably most of the error), then **M4 + C3 + C4**, and
   **M7/M8** once we have the validation set.
3. Do not change thresholds by tuning them "by eye" against a single Sentinel-2 image. Any change is measured with
   the metrics of section 3 over several dates and recorded in an ADR.

---

## 3. How to validate

There are two levels that should not be mixed:

- **Do we detect water well?** Validation of the mask.
- **Are the communities we call isolated really isolated?** Validation of the connectivity, which is the one that
  matters to the end user and can only be done with information from the ground.

### 3.1 Water mask against an optical reference

1. Find every NISAR–Sentinel-2 pair **≤ 2 days** apart with the area free of clouds (SCL or s2cloudless, with a safety
   margin around clouds and shadows). If there are few, add Landsat 8/9 (HLS) and, if still available, PlanetScope
   (3 m).
2. Reference: **MNDWI** with an Otsu threshold per image, checked by hand on a sample. The NDWI of EO Browser is not
   valid as a reference.
3. **Stratified** sampling (not pixel by pixel over the whole image, because open lake dominates): wide open water,
   channels < 60 m, channels 60–200 m, macrophytes or várzea, beaches and mud, forest, and *near* against *far range*.
4. Metrics per stratum and per pass: confusion matrix, water **IoU** and **F1**, omission and commission errors
   separately.
5. Optical data do not see under flooded forest. In the "water with vegetation" class the reference has to come from
   the field or from high-resolution photo interpretation, not from NDWI.

### 3.2 Isolated communities against reality on the ground

**Existing sources (without going to the field)**
- **Defesa Civil of Tefé and of the state of Amazonas**: lists of isolated communities that accompany the emergency
  decrees (122 of 151 in 2023 and 88 in 2024). Ask for the list **per community and dated**, not only the total.
- **Instituto Mamirauá** (based in Tefé): monitoring of the communities of the RDS Mamirauá and Amanã, and direct
  contact with community leaders.
- **SEMSA Tefé, DSEI and SEDUC**: health or vaccination boat trips and river school transport suspended or diverted.
  They are dated records of "could not get there".
- **Marinha do Brasil** (Agência Fluvial de Tefé / Capitania): notices to mariners and draught restrictions.
- **Operators of scheduled boats** (recreios) and cooperatives: which stops they stopped making and since when.

**Ground campaign (the real validation)**
1. **Sample stratified by the prediction**: e.g. 10–15 communities of each class (connected, at risk, isolated,
   `unresolved`), spread by distance to Tefé and by channel type. Do not visit only the isolated ones, because without
   the other classes the false alarm rate cannot be measured.
2. **Short, repeatable survey** of community leaders (in person, by HF radio or by WhatsApp, which many communities
   have) **in the same week as each NISAR pass**:
   - Today, can a boat leave the community for Tefé (or for its usual centre)? What type (canoe, rabeta, voadeira,
     scheduled boat)?
   - If not, since when? Do people have to walk or drag the boat? How many km?
   - Where is the real boarding point today? Ask for a GPS location: it corrects the OSM position and the access
     point.
3. **GPS tracks** of the boats that already make the trip (health, school, Mamirauá) with a logging app on the phone:
   they give the real route and the exact point where passage ends.
4. **Draught**: if a partner has an echo sounder (even a fishing one), measure the depth at the narrowings the map
   marks "at risk". It is the only way to validate the difference between width and navigability.
5. **Metrics**:
   - Confusion matrix per pass (predicted against observed).
   - **Sensitivity for "isolated"**. It is the priority metric: missing an isolated community is worse than a false
     alarm.
   - Precision and Cohen's kappa.
   - **Lead time**: how many days before the community reports the isolation we mark it "at risk".
6. **Time alignment**: an answer only counts for a pass if it is within ±3 days of it. The river changes too fast to
   use a wider margin.

**Historical validation (without waiting for the next drought)**
Run the same method with **ALOS-2 PALSAR-2** (and **ALOS-4 PALSAR-3** for 2024), both in L band like NISAR, over the
droughts of 2023 and 2024, and compare it with the Defesa Civil lists of those years. It is the strongest validation
we can get soon, because in 2026 the river is 5–7 m higher than in 2024 and there are few isolated communities to
compare with.

---

## 4. Quick diagnosis of each discrepant area

For each area where NDWI sees water and we do not:

1. Write down the dates of the NISAR pass and of the Sentinel-2 image. **If they are more than 3 days apart at low
   water, the comparison is not valid** (§1.3).
2. Look at the filtered HH value in `radar.webp` or in `water.npz`:
   - **HH > −10 dB (bright)** → water with vegetation or flooded forest (A). Check HV.
   - **HH between −15 and −10 dB, uniform** → wind or rain (B), or low incidence (D). Does it happen on other passes
     of the same track?
   - **Fragmented narrow channel** → resolution and filter (C).
3. Check whether the area lies near the edge of the circle or whether the community depends on another centre
   (§1.2).
4. Record the cause in a shared table (area, dates, HH, HV, cause). With 20–30 cases we will know what to fix first.

---

## 5. Open decisions (to be recorded in ADRs)

Under the project rules no threshold, mask or method is changed without asking first. Pending:

1. How to treat **water with vegetation**: as navigable water, as its own class ("possible passage") or as land?
   *Recommendation: its own class; it does not break the route, but marks it "at risk".*
2. **Fixed or adaptive threshold** per pass? *Recommendation: bounded adaptive (M2).*
3. Extend the **computation area** outside the circle and accept **several destinations** (C1, C2)?
   *Recommendation: yes, both.*
4. Does **confirmation** require the same track (C4)? *Recommendation: yes.*
5. Which **reference** do we use to validate the mask (MNDWI with Otsu and ≤ 2 days)? *Recommendation: yes, and never
   viewer NDWI.*
6. Whom do we ask first for **ground data** (Defesa Civil of Tefé or Instituto Mamirauá)? *Recommendation: Mamirauá.
   It is in Tefé, it is in contact with the communities and it has asked for exactly this map.*
