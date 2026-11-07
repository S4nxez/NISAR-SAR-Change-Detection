# NISAR L2 GUNW product

Structure read from a real product (`python -m irrigation_footprint.h5inspect`):
`NISAR_L2_PR_GUNW_024_114_D_070_025_4000_SH_20260704T024822_20260704T024857_20260716T024821_20260716T024856_P05023_N_F_J_001.h5`
(2.4 GB). Product specification: JPL D-102272, `productSpecificationVersion` 1.5.0, `productVersion` 1.0.11, DOI
10.5067/NIL2GUNW-P1 (provisional).

## Main layers (`/science/LSAR/GUNW/grids/frequencyA/`)

| Path | Shape | Type | Units | Grid |
| --- | --- | --- | --- | --- |
| `unwrappedInterferogram/HH/unwrappedPhase` | 4392 × 4446 | float32, NaN fill | radians | 80 m |
| `unwrappedInterferogram/HH/coherenceMagnitude` | 4392 × 4446 | float32 | 1 | 80 m |
| `unwrappedInterferogram/HH/connectedComponents` | 4392 × 4446 | uint16, fill 65535 | 1 | 80 m |
| `unwrappedInterferogram/HH/ionospherePhaseScreen` | 4392 × 4446 | float32 | radians | 80 m |
| `unwrappedInterferogram/HH/ionospherePhaseScreenUncertainty` | 4392 × 4446 | float32 | radians | 80 m |
| `unwrappedInterferogram/mask` | 4392 × 4446 | uint32 (bit-encoded) | — | 80 m |
| `wrappedInterferogram/HH/wrappedInterferogram` | 17568 × 17784 | complex64 | 1 | 20 m |
| `wrappedInterferogram/HH/coherenceMagnitude` | 17568 × 17784 | float32 | 1 | 20 m |
| `pixelOffsets/HH/{alongTrackOffset,slantRangeOffset}` | 4392 × 4446 | float32 | meters | 80 m |
| `pixelOffsets/HH/correlationSurfacePeak` | 4392 × 4446 | float32 | 1 | 80 m |

- Each group has `xCoordinates` / `yCoordinates` (pixel centres, meters), spacing +80 / −80 m (20 m for the wrapped
  interferogram) and `projection` = **EPSG:32611** (WGS 84 / UTM 11N) for this frame. The EPSG of each track/frame
  must be read from the file, never assumed.
- Only frequency A and polarization HH. `centerFrequency` = 1 239 000 000 Hz → **λ = c / f = 0.24196 m**
  (c = 299 792 458 m/s).
- Multilooking: 13 range × 16 azimuth looks (unwrapped), 5 × 6 (wrapped).
- `topographicFlatteningApplied` and `ellipsoidalFlatteningApplied` = True; common-band filters not applied.

## Correction layers

| Correction | Where | Shape | Units |
| --- | --- | --- | --- |
| Ionosphere | `grids/.../ionospherePhaseScreen` (+ uncertainty) | 80 m grid, same as the phase | radians |
| Hydrostatic troposphere | `metadata/radarGrid/hydrostaticTroposphericPhaseScreen` | 20 heights × 714 × 723 cube | radians |
| Wet troposphere | `metadata/radarGrid/wetTroposphericPhaseScreen` | 20 heights × 714 × 723 cube | radians |
| Solid Earth tides | `metadata/radarGrid/slantRangeSolidEarthTidesPhase` | 20 heights × 714 × 723 cube | radians |

The radarGrid cubes are sampled at heights −500 to 9000 m above the WGS84 ellipsoid every 500 m: applying them
needs the terrain height of each 80 m pixel (DEM, e.g. from the static layers product linked in
`identification/staticLayersDataAccess`) and a 3-D interpolation.

**Open question (accuracy):** `processingInformation/parameters/geocoding/{range,azimuth}IonosphericCorrectionApplied`
and `{hydrostatic,wet}TroposphericCorrectionApplied` are `True`. In ISCE3 these flags most likely refer to the
geolocation (timing) corrections used while geocoding, not to the phase; the plan (Fringe 2026) states that the phase
corrections are provided but not applied. This must be confirmed in the product specification D-102272 or
empirically before phase 2, because applying a correction twice or not at all biases the displacement.

## Geometry (`metadata/radarGrid/`, same cube layout)

`losUnitVectorX`, `losUnitVectorY`: east and north components of the line-of-sight unit vector **from the target to
the sensor** (ENU); the up component is `sqrt(1 − X² − Y²)`. Also `incidenceAngle`, `elevationAngle`,
`parallelBaseline`, `perpendicularBaseline`, slant ranges and zero-Doppler times.

## Sign convention

Not stated in the layer attributes. The plan's conversion `d_LOS = −λ/(4π)·φ` assumes the ISCE convention (positive
phase = range increase = motion away from the sensor). With the LOS vector pointing target → sensor, subsidence then
gives negative `d_LOS`. To be verified in phase 2 against GNSS and the known Corcoran subsidence before it is coded.

## Connected components and mask

- `connectedComponents`: in this product only 0 and 1 (+ fill 65535). 0 = pixels not assigned to a reliably
  unwrapped component; ≥ 1 = component labels. Phase is only comparable within one component.
- `mask` (uint32): bits 0–7 encode three decimal digits: water flag of the reference RSLC (1 = water), subswath number
  of the reference RSLC, subswath number of the secondary RSLC (0 = invalid sample). Bits 8–15: anomaly flags.

## Identification (`/science/LSAR/identification/`)

`trackNumber` 114, `frameNumber` 70, `orbitPassDirection` Descending, `lookDirection` Left, `compositeReleaseId`
P05023, `processingType` Nominal, `isFullFrame` True, `processingDateTime` 2026-08-13. Orbits: `orbitType` = MOE
(medium precision) for both dates. `metadata/orbit/temporalBaseline` = 11 days (integer truncation of 11.99999 days:
the secondary starts one second earlier in the day); the inventory computes 12 from the dates.

## Limitations

- Provisional data (`PR`, `NISAR_L2_GUNW_PROVISIONAL_V1`): to be reprocessed (validated release expected late 2026).
- One product inspected; layout of the ascending track 34 (and its EPSG) to be checked when it is downloaded.
