# CLAUDE.md

Rules for every Claude Code session in this repository. Project: map of the **groundwater irrigation footprint** in the
Tule and Tulare Lake subbasins (Central Valley, California) from NISAR L2 GUNW, for the NASA Space Apps Challenge 2026
("Dancing with the SARs"). The goal is to flag where groundwater pumping for irrigation is *probable*, per 500 m hexagon,
with a confidence level — not to find illegal wells.

## Repository layout

| Path | Content |
| --- | --- |
| `pipeline/` | Python package `irrigation_footprint`: download, InSAR corrections, time series, support layers, classification |
| `api/` | FastAPI backend (phase 7; replaces `server/`) |
| `frontend/` | Vanilla JS + Leaflet web app |
| `server/`, `fractal_model_lab/` | Legacy Spring Boot backend and C model lab; still built by CI (`.github/workflows/build.yml`) |
| `docs/` | Component, calculation, interpretation and decision (ADR) docs |
| `data/` | Downloaded and derived data. **Git-ignored** except the legacy `data/csv/` and `data/sql_generator.py` |
| `tools/ci/` | CI/CD scripts (smoke test, rollback, PR previews) |

## Git

- Integration branch for this work: `feature/jorge/california-illegal-wells`. Each step goes in its own branch
  `feature/jorge/<area>-<description>` created from it and merged back into it. Areas: `insar`, `data`, `classify`,
  `compare`, `api`, `web`, `infra`, `docs`.
- Never commit to, push to or open pull requests against `main`, `develop` or any branch outside `feature/jorge/`
  without explicit approval. `feature/jorge/donana-illegal-wells` is not touched either.
- Atomic commits: one logical change per commit; the project builds and the tests pass at every commit.
  Conventional Commits messages, in English (`feat(insar): apply ionospheric correction`).
- Never commit data, credentials or `.env`. Data lives in `data/`; the repo keeps only the scripts that download it.

### CI coupling

Workflows only run on pushes to `main`/`develop`, pull requests into `develop` and the weekly `develop` → `main` merge,
so `feature/jorge/*` pushes trigger nothing. But `build.yml` validates `frontend/*.js` syntax, compiles
`fractal_model_lab/`, runs `mvn verify` in `server/`, starts `podman-compose.yml` and runs `tools/ci/smoke-test.sh`
(which calls `GET /api/sites`). Removing or replacing any of those must update the workflows, `tools/ci/*` and the
compose file in the same change.

## Documentation (mandatory, updated in the same PR as the code)

- `docs/components/<component>.md`: what it does, inputs, outputs, how to run it, limitations.
- `docs/calculations/<calculation>.md`: formula, units, sign convention, assumptions, source of every constant.
- `docs/interpretation.md`: how to read the map (classes, what they do not mean, confidence, typical false
  positives/negatives).
- `docs/decisions/ADR-NNN-<title>.md`: one record for every choice that affects accuracy.

## Step-by-step development

- One plan step per session or PR. Do not jump ahead of phases.
- At the end of each step, summarise what was done, what is pending and the risks seen.
- Every calculation has tests on synthetic data with a known result, including sign and unit tests.
- Run the tests with `pytest` from `pipeline/` inside the `irrigation-footprint` environment (`pipeline/environment.yml`).

## Accuracy review and mandatory consultation

When closing each part, actively look for problems that affect the accuracy of the anomalies and **ask before
deciding**. Never silently pick a threshold, mask or method. At least review:

- Sign convention and units of the phase and of every correction.
- Reference system (UTM, EPSG) and resampling between 20, 30, 80 and 100 m grids.
- Coherence thresholds, connected components and masks.
- Choice of reference point and reference date.
- Temporal alignment between sources with different dates.
- Line-of-sight to vertical projection.
- Per-cell aggregation (mean, median, coherence weighting) and minimum number of valid pixels.
- Any provisional or doubtful-quality data (NISAR data is provisional until the validated reprocessing, late 2026).

Each consultation lists the options, their expected effect on accuracy and a recommendation. The answer is recorded in
an ADR.
