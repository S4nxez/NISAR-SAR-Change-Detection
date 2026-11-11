# ADR-004: Water under vegetation is mapped as its own class and is not a route (M1)

- Status: routing rule **accepted**; detection thresholds **proposed** (2026-11-11)
- Component: river lifeline monitor, `processing/src/lifeline/analysis/water.py` (`vegetated_water`), area key
  `vegetated_water`, `water.png` colour 3 (green), map key in `frontend/src/components/panels.js`

## Context

Sentinel-2 NDWI showed water where the monitor showed none. A main cause is water under floating meadows
(canarana, *Paspalum*, water hyacinth) or flooded forest: at L-band the double bounce water → stem → radar makes
such water brighter than dry forest, never darker than −15 dB, so it was land. Some of these stretches allow canoes
or long-tail boats; others (dense meadows, matupás) close channels overnight, and in the dry season they are mostly
shallow margins.

## Decision

1. **Routing (project lead):** water under vegetation is shown on the map with its own colour and an entry in the
   map key ("Water under vegetation · not a route") and is **never counted as a navigable route**. A community whose
   only route crosses it is isolated. This follows the project's rule of erring on the safe side.
2. **Detection (proposed values):** on dual-polarisation passes, HH > −4 dB and HH − HV ≥ 7 dB, outside open water,
   within 1 km of it, specks under 1 ha dropped. Values chosen inside the L-band ranges of Hess et al. (1995, 2003)
   for the central Amazon: flooded forest HH about −3 to +2 dB with HH − HV of 8–12 dB; dry forest HH about −7 dB
   with HH − HV about 5–6 dB. Not yet checked against field observations at Tefé.

## Consequences

- Community status does not change with this class (it was land before and still blocks routes); the benchmark
  confirms no route metric moves, and reports the area flagged and how much of it Sentinel-2 sees as open water.
- Single-polarisation passes (SHSH) have no HV: no vegetated layer there (`vegetated_km2` null).
- Expected false positives: towns and metal roofs (double bounce too), within 1 km of the water; they only change
  the colour on the map.
- Floating meadows that are thin and short can stay below −4 dB and remain unflagged land.
