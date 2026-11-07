# pipeline

Python package `irrigation_footprint`: the processing that runs on the local PC (download, NISAR GUNW corrections,
time series, support layers, 500 m hexagon classification). Its outputs are precomputed files that the API serves.

## Environment

```bash
# From the repository root, with micromamba (or mamba / conda, same arguments)
micromamba create -f pipeline/environment.yml
micromamba activate irrigation-footprint
pip install --no-deps nisar-pytools==0.5.0
pip install -e pipeline --no-deps
```

`nisar-pytools` is installed without its dependencies because it requires `snaphu`, which has no Windows build; all
its other dependencies are in `environment.yml`. Phase unwrapping with `nisar-pytools` is therefore unavailable on
Windows (not needed for GUNW, see ADR-001).

## Tests

```bash
cd pipeline
pytest
```

Every calculation is tested on synthetic data with a known result, sign and unit tests included (see `CLAUDE.md`).

## Data and credentials

Downloads go to `data/` at the repository root (git-ignored). NASA Earthdata credentials are read from the root `.env`
(see `.env.example`).
