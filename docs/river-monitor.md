# River lifeline monitor

In severe Amazon droughts, rivers and side channels dry up and riverside communities lose
their only way to reach food, fuel, medicine, doctors and school. In September 2024 about
1,554 communities were isolated in the Middle Solimões alone, and the 2026 drought has left
47 of the 62 municipalities of Amazonas in emergency. Today, isolated communities are counted
by hand after the fact; the Instituto Mamirauá's first recommendation to the state government
for the 2026 drought is to map the communities at risk of isolation.

This monitor uses every NISAR radar pass (through clouds and smoke, under the forest canopy)
to tell, community by community, whether a water route to the hub town still exists and how
narrow it has become.

## Architecture

```
NASA ASF / OpenStreetMap / ANA ──> monitor worker (processing/, Python) ──> monitor_data volume
                                                                               │ read-only
                          browser <── Caddy /api/* <── backend (server/, Java) ┘
                          browser <── Caddy /      <── frontend (frontend/, nginx)
```

- **Worker** (`processing/`, the `monitor` service of `podman-compose.yml`): all the radar processing, in Python
  because it relies on its scientific stack (HDF5 reads with `h5py`, `numpy`/`scipy` filters and distance
  transforms, `pyproj`). It is a batch job, not a web service: it never answers requests, it writes files.
- **Backend** (`server/`): the only API the web page talks to. It serves the record from the volume under
  `/api/monitor` and refuses a catalog whose `schema_version` it does not know.
- **Frontend** (`frontend/`): reads everything from `api/monitor/...`.

### API

| Request | Answer |
|---|---|
| `GET /api/monitor/areas/{area}` | `catalog.json` of the area. `Cache-Control: no-cache` with `Last-Modified`: the page polls it every ten minutes and gets `304 Not Modified` until the worker writes a new one. `404` while the area has no record, `503` when its `schema_version` is not the backend's |
| `GET /api/monitor/areas/{area}/passes/{pass}/{layer}` | `radar.webp`, `water.png` or `change.png` of a pass (cached for an hour). Any other file (`water.npz`) is `404` |

Area and pass ids are plain names (`[A-Za-z0-9_-]`); anything else is `404`.

### Catalog contract

`catalog.json` carries `schema_version` (`SCHEMA_VERSION` in `processing/src/lifeline/config.py`, and the same constant
in the backend's `MonitorRecordService`; a unit test checks they match) and its own `status_codes` table
(`{"0": "no_data", "1": "connected", "2": "at_risk", "3": "isolated"}`): the page names the codes from that table
instead of repeating them. Change `schema_version` on both sides whenever a reader would notice the change.

## Run it

```bash
python -m pip install -e processing        # the lifeline package, its pinned dependencies and the river-monitor command
river-monitor communities                  # once: places from OpenStreetMap
river-monitor occurrence                   # once: JRC water occurrence layer
river-monitor update                       # all passes not processed yet, into processing/output/
```

Then run the backend with `MONITOR_DATA_DIR` pointing at `processing/output` and open the frontend through it
(the page reads `api/monitor/...`). `python -m lifeline` is the same command line as `river-monitor`.
`MONITOR_DATA_DIR` and `MONITOR_AREAS_DIR` change where the record is written and where the area files are read.
`MONITOR_CACHE_DIR` (optional, unset in the stack) keeps a local copy of the area window of every granule read, with
all its bands (HH and HV): reprocessing a pass, for example in the benchmark or after a method change, then reads
nothing remote. It takes about 250 MB per granule for the Tefé area.

In the stack, the `monitor` service runs `river-monitor watch --hours 6` and writes to the `monitor_data` volume.
A new volume starts empty: the first round processes every pass ASF lists (about one minute per pass on the Pi).

`update` needs a NASA Earthdata token (free account at https://urs.earthdata.nasa.gov,
*Generate Token*) in the `EARTHDATA_TOKEN` environment variable. It never downloads whole
products: only the area of interest is read with HTTP range requests (about 100 MB and one
minute per pass for the Tefé area, instead of ~1.9 GB).

`river-monitor watch --hours 6` searches ASF every six hours and processes new passes; the web page
picks them up every ten minutes without a reload. In the stack the token is `EARTHDATA_TOKEN` in the
stack's `.env` (see `tools/ci/README.md`).

`river-monitor reevaluate` recomputes every pass from the stored water masks (no download), for
example after changing the rules in the area file or the community list. In the stack:
`podman-compose run --rm monitor reevaluate`.

## Area file

`processing/areas/<area>.json` defines the area, either as a `circle` (centre and radius in km;
Tefé uses 55 km) or as a `bbox`, the grid (~20 m), the hub town, a
point on the main river (to report the hub ↔ main river link), the water threshold and the
rules below. `processing/areas/<area>_communities.geojson` holds the places (OpenStreetMap,
ODbL). Add an area by writing a new pair of files and passing `--area <id>`; the web page
takes `index.html?area=<id>`.

## Method

For every pass (all frames of one track on one day):

1. **Read**: HH backscatter of the area from the NISAR L2 GCOV product (ASF DAAC). Values
   below −40 dB (`valid_floor_db`) are swath-edge fill, not measurements, and become no data
   ([ADR-001](decisions/ADR-001-river-monitor-fill-is-no-data.md)). Then speckle filtered with a
   refined Lee filter (7 × 7 window, edge-aligned half windows, 9 looks: shores are not blurred;
   [ADR-002](decisions/ADR-002-river-monitor-refined-lee-filter.md); the older box filter,
   `speckle_filter: "box"`, averages over ~60 m and narrows every channel), and resampled to a fixed
   lon/lat grid shared by all passes. The last 1 km before the edge of the data (`edge_margin_m`) is also no
   data: the signal rolls off to the noise floor there and would read as a channel along the edge
   ([ADR-006](decisions/ADR-006-river-monitor-swath-edge-margin.md)).
2. **Water**: filtered HH below −16 dB, plus pixels below −14 dB that touch that water
   (hysteresis): wind roughens stretches of rivers and lakes, which then return a little
   more echo and would otherwise cut the river in two. Both values are tuned for the refined Lee filter
   ([ADR-005](decisions/ADR-005-river-monitor-thresholds-for-refined-lee.md)); a threshold measured on every pass,
   `water_db_adaptive`, exists but is off ([ADR-003](decisions/ADR-003-river-monitor-per-pass-threshold.md),
   rejected). Specks under 1 ha are dropped and
   holes under 2 ha inside water are filled.
   **Water under vegetation** (dual-polarisation passes): HH > −4 dB and HH − HV ≥ 7 dB within
   1 km of open water, the double bounce of floating plants or flooded forest. It is drawn in green
   and is never a route ([ADR-004](decisions/ADR-004-river-monitor-water-under-vegetation.md)).
3. **Route**: for each channel width W (40, 60, 100, 200, 400 m), keep only the water whose
   centre is far enough from the shore for a channel at least W wide, and check whether a
   community (within 1 km) and the hub town fall in the same piece of water. The widest W
   that still links them is the narrowest point of the route. Widths are estimated
   conservatively (one pixel less) so warnings come early rather than late. At the
   "any water" level, pixels touching at a corner count as connected, because one-pixel
   creeks often run diagonally.
   Routes start where people reach the water, not at the middle of the settlement: a place
   called "Porto de X" next to X is X's port, and towns use the nearest ferry terminal, pier
   or harbour within 3 km (villages and hamlets within 500 m) from OpenStreetMap. Without
   this, a town whose centre is a kilometre inland (Alvarães) looked isolated while its port
   stayed connected.
   **Low water and Sentinel-1** ([ADR-007](decisions/ADR-007-river-monitor-low-water-beds.md)): the wet, smooth bed
   of a drained lake or side channel reads in NISAR's L band as dark as open water (about −17 dB in HH), and showed
   wide routes where only a creek was left. Sentinel-1 (C band, 5.6 cm) sees the same mud as rough, about 10 dB
   brighter than water. Every pass therefore also reads the Sentinel-1 scenes within 4 days (VV, radiometrically
   terrain-corrected, from Microsoft Planetary Computer, no account), skipping a scene taken when the river was
   more than 30 cm off the level of the pass, and keeps the darkest of them on each pixel: wind roughens open water
   in C band for a day or two, a drained bed stays bright on every date. When the river gauge on the day of the pass is at most 1200 cm
   (`low_water.gauge_max_cm`), on seasonal ground (water in 30 to 90 % of the months of 1984–2021, JRC Global
   Surface Water, `processing/areas/<area>_occurrence.png`):
   - NISAR water that Sentinel-1 sees as land (VV ≥ −16 dB, in patches at least 60 m across) carries no route;
   - a broad seasonal patch (holding a 60 m disc) that no usable Sentinel-1 scene covers is *unverified*: a route
     through it is at most *at risk*, never *connected*, and the community is listed in the pass's
     `unverified_route`.

   A seasonal lake that still holds water keeps its route: the historical occurrence alone cannot tell it from a
   drained bed. Every pass records its river level (`river_level_cm`), whether the rule applied (`low_water`) and how
   the two radars agree (`sentinel1`: scene dates, agreement, water each one alone sees, mud left out).
4. **Status**: *connected* (route ≥ 60 m), *at risk* (route narrower), *isolated* (no water
   route, or no water within 1 km), *no data* (not covered by the pass, or a route could run
   through a gap in the pass).
   Isolation is only confirmed when the previous pass with data agrees; the first pass that
   shows it counts as *at risk (to confirm)*, because one image can be spoiled by wind or rain.
5. **Whole record**: places that never have water within 1 km are *inland* (not river
   dependent) and places never linked through a channel of at least 40 m on any pass are
   *not resolved* (one-pixel creeks come and go between passes). Both are left out of the
   counts, so *isolated* means a community lost a route it had.
6. **Change**: water lost and gained since the previous pass of the same track.

With a circular area, pixels outside the circle are not part of the area: they are transparent in
the images, never water, and not counted as gaps in a pass. Coverage is measured inside the
circle.

Passes that cover less than 80 % of the area are kept as images but not evaluated, and
passes under 5 % are hidden.

The thresholds were tuned on two passes over Tefé: 7 July 2026 (high water) and 23 October 2026
(low water). With the final settings, places without a route drop from 44 to 18 at high water
(the rest are mostly streams too narrow to resolve) while 30 remain at low water.

## Accuracy benchmark

`river-monitor benchmark --label <name>` scores the method of the current checkout against synthetic scenes,
Sentinel-2 water, the river gauge and field checks, and keeps every result in `processing/benchmark/history/`.
Run it before and after any change to the method; see [river-monitor-benchmark.md](river-monitor-benchmark.md).

## Validation so far (Tefé, November 2026)

- **River level**: against the official ANA gauge Tefé-Missões (station 12900001, Solimões),
  across the 15 evaluated passes, monitored communities without a water route follow the river
  level (Spearman −0.86 over the 55 km circle; −0.99 over the earlier 78 km square) and so does
  detected water (+0.85; +0.96 over the square). Over the circle the high-water passes of track
  161 cover only 88–89 % of the area, which makes their water totals less comparable.
- **Places named in reports**: Caiambé, the boat landing used in the 2023–2024 droughts, stays
  connected; Alvarães stays connected through its port.
- **Not validated yet: how many communities are isolated.** Tefé's civil defence counted 122
  of 151 communities isolated in 2023 and 88 in 2024, but at that gauge the 2026 river stays
  5–7 m higher than in those years (minimum 780 cm on 26 October 2026, against about 23 cm in
  2024), and no per-community list for 2026 has been published. A list from the civil
  defence or the Instituto Mamirauá, or the same method run on ALOS-2 L-band data for 2023 and
  2024, is needed. Several places named in health reports (Vila Bastos, São Francisco do
  Itauba, Porto Praia de Baixo) are missing from OpenStreetMap.

## Limits

- Radar does not measure depth: a route can exist and still be too shallow for boats. That
  is why narrow routes are flagged, and why river gauges (SGB/ANA) remain the reference for
  depth.
- At 20 m, channels narrower than about 40–60 m are not reliable.
- Different tracks look at the ground from different angles; water/no-water is robust to it,
  backscatter values are not compared across tracks.
- NISAR data are still *provisional* (and some early passes *beta*), and public data start in
  late 2025: there is no NISAR record of the 2023 and 2024 droughts.
- Community positions come from OpenStreetMap and can be off; the list should be validated
  with people who know the area (Instituto Mamirauá, Defesa Civil).

## Output

`catalog.json` also carries the official river level next to the hub (ANA telemetry station set
in the area file as `gauge`), refreshed on every `update`: the page draws it behind the pass log
so the radar result can be read against the river.

`<MONITOR_DATA_DIR>/<area>/catalog.json` plus, per pass (`passes/<pass>/`), `radar.webp`, `water.png`
(channels narrower than the safe width in amber, water under vegetation in green), `change.png`, `water.npz` (packed water
mask used for the change layer and `reevaluate`, never served) and `sentinel1.npz` (the Sentinel-1 classes the pass
used, for `reevaluate`, never served). The record is data, not code: it
lives in the volume (or `processing/output/` locally, ignored by git), never in the repository.

## Code and tests

`processing/` is a Python project (`pyproject.toml`, `src` layout). The `lifeline` package is split by
responsibility, and `tests/` mirrors it:

| Package / module | What |
|---|---|
| `config.py` | paths (`MONITOR_DATA_DIR`, `MONITOR_AREAS_DIR`), remote services, `SCHEMA_VERSION`, status codes |
| `geometry/` | `geo.py` distances and place-name folding; `area.py` area files, the lon/lat grid, the circular area mask |
| `sources/` | external data: `asf.py` NISAR GCOV search; `remote.py` Earthdata token and ranged reads; `places.py` communities and landings from OpenStreetMap; `gauge.py` river level from ANA; `occurrence.py` JRC water occurrence layer; `sentinel1.py` Sentinel-1 water and land around a pass |
| `analysis/` | `radar.py` speckle filter and the read of one pass onto the area grid; `water.py` water mask (hysteresis), channel widths and the route of every community to the hub |
| `output/` | `layers.py` `radar.webp`, `water.png`, `change.png` and the stored water mask; `catalog.py` evaluation of a pass, whole-record classification, `catalog.json` |
| `pipeline.py` | the commands (`communities`, `update`, `reevaluate`, `watch`) |
| `cli.py`, `__main__.py` | the command line: `river-monitor` or `python -m lifeline` |

```bash
python -m pip install -e processing
python -m unittest discover -s processing/tests -t processing
```

The tests need no network access and no NISAR product: HTTP clients are replaced by stand-ins, the
GCOV reader runs on a small synthetic HDF5 product and the commands write to temporary folders.
They run in the CI before any image is built. The backend's API has its own tests in
`server/src/test` (`mvn verify`) and the web page's in `frontend/tests` (`npm test` in `frontend/`).
