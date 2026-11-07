# pipeline

Python package `irrigation_footprint`: the processing that runs on the local PC (download, NISAR GUNW corrections,
time series, support layers, 500 m hexagon classification). Its outputs are precomputed files that the API serves.

## Environment

```bash
# From the repository root, with micromamba (or mamba / conda, same arguments)
micromamba create -f pipeline/environment.yml
micromamba activate irrigation-footprint
pip install -e pipeline --no-deps
```

## Tests

```bash
cd pipeline
pytest
```

Every calculation is tested on synthetic data with a known result, sign and unit tests included (see `CLAUDE.md`).

## Data and credentials

Downloads go to `data/` at the repository root (git-ignored). NASA Earthdata credentials are read from the root `.env`
(see `.env.example`).
