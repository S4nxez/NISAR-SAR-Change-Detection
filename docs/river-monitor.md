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

## Run it

```bash
python -m pip install -r processing/requirements.txt
python processing/river_monitor.py communities     # once: places from OpenStreetMap
python processing/river_monitor.py update          # all passes not processed yet
python -m http.server 8080 --directory frontend    # then open http://localhost:8080/monitor.html
```

`update` needs a NASA Earthdata token (free account at https://urs.earthdata.nasa.gov,
*Generate Token*) in the `EARTHDATA_TOKEN` environment variable. It never downloads whole
products: only the area of interest is read with HTTP range requests (about 100 MB and one
minute per pass for the Tefé area, instead of ~1.9 GB).

To keep it running, `python processing/river_monitor.py watch --hours 6` searches ASF every six
hours and processes new passes; the web page picks them up every ten minutes without a reload.
On Windows the same command can be registered in Task Scheduler; on Linux, use cron or a
systemd service.

`python processing/river_monitor.py reevaluate` recomputes every pass from the stored water
masks (no download), for example after changing the rules in the area file or the community
list.

## Area file

`processing/areas/<area>.json` defines the bounding box, the grid (~20 m), the hub town, a
point on the main river (to report the hub ↔ main river link), the water threshold and the
rules below. `processing/areas/<area>_communities.geojson` holds the places (OpenStreetMap,
ODbL). Add an area by writing a new pair of files and passing `--area <id>`; the web page
takes `monitor.html?area=<id>`.

## Method

For every pass (all frames of one track on one day):

1. **Read**: HH backscatter of the area from the NISAR L2 GCOV product (ASF DAAC), speckle
   filtered over ~60 m (a wider window erases channels two or three pixels wide) and
   resampled to a fixed lon/lat grid shared by all passes.
2. **Water**: filtered HH below −15 dB, plus pixels below −12 dB that touch that water
   (hysteresis): wind roughens stretches of rivers and lakes, which then return a little
   more echo and would otherwise cut the river in two. Specks under 1 ha are dropped and
   holes under 2 ha inside water are filled.
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

Passes that cover less than 80 % of the area are kept as images but not evaluated, and
passes under 5 % are hidden.

The thresholds were tuned on two passes over Tefé: 7 July 2026 (high water) and 23 October 2026
(low water). With the final settings, places without a route drop from 44 to 18 at high water
(the rest are mostly streams too narrow to resolve) while 30 remain at low water.

## Validation so far (Tefé, November 2026)

- **River level**: against the official ANA gauge Tefé-Missões (station 12900001, Solimões),
  across the 15 evaluated passes, detected water follows the river level (Spearman +0.96) and
  so does the number of monitored communities without a water route (−0.99).
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

`frontend/public/data/monitor/<area>/catalog.json` plus, per pass, `radar.webp`, `water.png`
(channels narrower than the safe width in amber), `change.png` and `water.npz` (packed water
mask used for the change layer and `reevaluate`).
