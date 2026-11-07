# api

FastAPI backend of the irrigation footprint map (plan phase 7). It will replace the Spring Boot + MySQL backend in
`server/` with FastAPI + PostGIS, plus TiTiler for the COG rasters.

Until then `server/` keeps serving the current app: CI (`.github/workflows/build.yml`, `tools/ci/smoke-test.sh`) builds,
tests and smoke tests it, so it is removed in the same change that moves CI to this backend.
