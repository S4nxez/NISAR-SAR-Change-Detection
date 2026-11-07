# ADR-001: Repository layout and Python environment

- Status: **Accepted** (plan step 0.6; confirmed 2026-11-07: micromamba, English, `data/` ignore rule; every merge
  between branches goes through a pull request)
- Date: 2026-11-07

## Context

The irrigation footprint pipeline (Python) joins a repository that already has a Spring Boot backend (`server/`), a C
model lab (`fractal_model_lab/`), a vanilla JS frontend and CI/CD that builds and deploys them to a Raspberry Pi.
`data/` already tracks `data/csv/` and `data/sql_generator.py` (Spring demo data). The local PC has Python 3.12 but no
conda distribution.

## Decision

1. Layout: `pipeline/` (package `irrigation_footprint`, src layout, pytest), `api/` (FastAPI, phase 7), `frontend/`
   (kept), `docs/` (`components/`, `calculations/`, `decisions/`, `interpretation.md`), `data/` (git-ignored).
2. `data/` is ignored except the legacy `data/csv/` and `data/sql_generator.py`, which stay until `server/` is retired.
   Pipeline data does not move elsewhere, so paths follow the plan.
3. `server/` and `fractal_model_lab/` are kept for now: CI builds and smoke tests them, and removing them requires
   changing `build.yml`, `deploy.yml`, `preview.yml`, `tools/ci/*` and `podman-compose.yml` together (phases 7 and 9).
4. Environment: `pipeline/environment.yml` from conda-forge only, Python 3.11, installed with micromamba (the team's
   choice; mamba/conda read the same file). GDAL, rasterio and MintPy are unreliable from pip on Windows.
   `nisar-pytools` is pinned (0.5.0) and installed from PyPI with `--no-deps`: its dependencies come from conda-forge
   except `snaphu`, which has no Windows build (conda-forge or PyPI). `nisar-pytools` only imports `snaphu` inside its
   unwrapping function, which the GUNW path does not need (GUNW is already unwrapped). The optional GSLC long-pairs
   branch of the plan would need unwrapping, so it would run on Linux or WSL2.
5. Repository language: English (code, docs, commits), as the rest of the repository.

## Effect on accuracy

None directly. Pinning `nisar-pytools` and MintPy versions keeps the readers of the GUNW layers stable across the team.

## Alternatives considered

- `pipeline/data/` instead of `data/`: leaves the legacy folder untouched but departs from the plan.
- pip + venv: no conda needed, but GDAL/MintPy installs on Windows are fragile.
- pixi: lockfile across platforms, but new to the team.
