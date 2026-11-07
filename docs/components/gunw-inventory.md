# Component: GUNW inventory and download

`pipeline/src/irrigation_footprint/inventory.py`, `download.py`, `aoi.py`

## What it does

- `inventory`: searches ASF for every NISAR L2 GUNW intersecting the search bbox, parses each product name into
  structured fields and writes a CSV and a per-track summary (date range, pairs, pairs longer than 12 days, gaps,
  pairs available in several product versions). It does not choose between duplicates.
- `download`: downloads products listed in the inventory with the Earthdata credentials of `.env`, skipping files
  already complete (resumable). Uses the token and falls back to username + password if ASF rejects it.

## Inputs

- `aoi.SEARCH_BBOX` = (-120.05, 35.75, -118.85, 36.45), EPSG:4326: a generous rectangle around the Tule and Tulare
  Lake subbasins, only for searching. Clipping uses the official DWR Bulletin 118 boundaries (support-layer step).
- Earthdata credentials (`docs/components/pipeline-config.md`). The Earthdata account must have authorized the ASF
  application once (the error message gives the `approve_app` URL).

## Outputs

- `data/inventory/gunw.csv`: one row per product: parsed name fields, `baseline_days` (secondary minus reference
  date), `h5_bytes`, `url`, ASF path/frame/direction and footprint WKT.
- `data/inventory/gunw_summary.txt`: per (direction, track, frame) summary.
- `data/gunw/<product>.h5`: downloaded products (about 2.4 GB each).

## How to run

```bash
python -m irrigation_footprint.inventory
python -m irrigation_footprint.download <product name> [...]
```

## Product name fields

`NISAR_L2_<PR>_GUNW_<refCycle>_<track>_<A|D>_<frame>_<secCycle>_<mode>_<pol>_<refStart>_<refStop>_<secStart>_<secStop>_<CRID>_<f13>_<f14>_<f15>_<counter>`

`mode` 4000 and `pol` SH are the only values over the area. `CRID` is the processing release (`P05023`, `X05010`
seen). `f13`–`f15` are kept raw: their meaning (probably orbit accuracy N/F, coverage, processing site) is inferred,
not documented by ASF, and must be checked against the HDF5 identification metadata.

## Limitations

- Product versions are not deduplicated: the choice of CRID and `f13` is an accuracy decision (ADR).
- ASF footprints are swath outlines; the coverage of the real subbasins is checked after clipping.
