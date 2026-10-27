# CI tooling

Files used by the GitHub Actions pipeline in `.github/workflows/`.

## Pipeline

```
push to main ─> Build Images (build.yml): validate ─> build (multi-arch images pushed to GHCR)
                                                         └─> Deploy (deploy.yml): deploy on the Pi ─> post-deployment smoke test
```

`validate` is the pre-deployment validation stage. `build` needs it and Deploy only runs when the whole Build Images workflow succeeds,
so if any check fails no image is pushed and the Raspberry Pi keeps running the current version.

| Step | Fails when |
|---|---|
| Frontend - check JavaScript syntax | An ES module under `frontend/` has a syntax error (`node --check`, the frontend has no build step) |
| Model lab - compile | `fractal_model_lab` does not compile from sources (`-Werror`, so warnings too) |
| Backend - compile, run tests and package | `mvn verify` fails: compilation errors or failing tests (every test under `server/src/test` runs) |
| Startup check - prepare environment | `podman-compose.yml` plus `compose.ci.yml` is not a valid compose configuration |
| Startup check - build images | A `Containerfile` does not build |
| Startup check - start stack | A container cannot start or MySQL never becomes healthy |
| Startup check - smoke test | `smoke-test.sh` fails: Spring initialization, Flyway migrations, database connection, Caddy routing or frontend assets |

The startup check runs the production `podman-compose.yml` (services, env vars, healthcheck, `Caddyfile`, published port) with `docker compose`,
layered with `compose.ci.yml`, against a fresh database with throwaway credentials.

## Post-deployment smoke test

Once Deploy has pulled the images and recreated the stack on the Raspberry Pi, it runs `smoke-test.sh` from the deployed commit on the Pi
(`ssh ... bash -s`), so the checks hit production itself: the new backend starts against the production database and its data, Caddy routes `/api/*`
and the frontend is served, then the same through the public URL. Deploy fails if any check fails. **It does not roll back**: the new version stays deployed.

| Step | Fails when |
|---|---|
| Deploy | An image cannot be pulled or `podman-compose up` fails |
| Smoke test - deployed stack | `smoke-test.sh http://127.0.0.1:8089` (Caddy) fails on the Pi: the backend does not answer within 120 s (Spring initialization, Flyway migrations on the production data, database connection), Caddy does not route `/api/*`, or the page or one of its assets is not served |
| Smoke test - public URL | The same checks fail at `https://raspberrypi.tail0a4b52.ts.net/terra-pulse`, through Tailscale Funnel, as browsers reach the app (the frontend calls `../api/sites`, under the `/terra-pulse` prefix). Only runs once the stack passed, so the cause is in front of Caddy: the Funnel mapping (`tailscale serve status` on the Pi) or a URL that ignores the prefix, e.g. an absolute asset path |

## Files

| File | Purpose |
|---|---|
| `smoke-test.sh` | Checks a running stack through Caddy: `GET /api/sites` returns a non-empty catalog read from MySQL, and the page and every local asset it references are served. Usage: `smoke-test.sh [BASE_URL]` (default `http://127.0.0.1:8089`), waits up to `SMOKE_TIMEOUT` seconds (default 180) for the backend. Used by the startup check and the post-deployment smoke test |
| `compose.ci.yml` | Compose override that builds `backend` and `frontend` from the checkout instead of using the published `:latest` images |

## When validate fails

- The run marks the failing step. The smoke test prints a `[FAIL]` line per failed check, with a hint of where to look, and adds it as an annotation on the run summary.
- If the startup check fails, **Startup check - container status and logs** prints `docker compose ps -a` (crashed or restarting containers),
  annotates the innermost `Caused by:` of the backend's first start (usually the root cause of a Spring startup failure,
  e.g. `Access denied for user ...` or the SQL error of a broken migration) and prints each service's logs in a collapsible group.

## When Deploy fails

- The smoke test output is the same as in validate: a `[FAIL]` line per failed check, with a hint, also annotated on the run summary.
- If the deployment or the deployed stack check failed, **Smoke test - container status and logs** prints `podman-compose ps` from the Pi,
  annotates the innermost `Caused by:` of the new backend's first start and prints the backend and mysql logs in collapsible groups.
  Caddy and frontend logs are not printed: they record visitors' IP addresses and the Actions logs of this public repository are public.
  Read them on the Pi with `podman-compose logs caddy frontend` in `/opt/NISAR-SAR-Change-Detection`.
- Production keeps running the failed version until a fix is deployed. To re-check it at any time, run `tools/ci/smoke-test.sh` on the Pi (see below).

## Running it locally

`tools/ci/smoke-test.sh [BASE_URL]` only sends GET requests, so it can check any running stack, production included: on the Pi, without arguments
it checks the deployed stack as Deploy does, and `tools/ci/smoke-test.sh https://raspberrypi.tail0a4b52.ts.net/terra-pulse` checks the public URL.

To reproduce the whole startup check use a separate worktree, since it writes `.env` and `server/.env`, and not on the Raspberry Pi,
where `127.0.0.1:8089` is the production Caddy:

```bash
git worktree add ../nisar-ci HEAD && cd ../nisar-ci
(cd server && mvn -B -ntp verify)
printf 'MYSQL_ROOT_PASSWORD=%s\nMYSQL_USER=root\n' "$(openssl rand -hex 16)" > .env && : > server/.env
export COMPOSE_FILE=podman-compose.yml:tools/ci/compose.ci.yml COMPOSE_PROJECT_NAME=nisarsar-ci
docker compose build && docker compose up -d --no-build
tools/ci/smoke-test.sh
docker compose down -v
```
