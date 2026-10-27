# CI tooling

Files used by the GitHub Actions pipeline in `.github/workflows/`.

## Pipeline

```
Weekly merge (weekly-merge.yml, Wed 20:00 UTC): PR develop ─> main (squash) ─┐
push to main ────────────────────────────────────────────────────────────────┴─> Build Images (build.yml): validate ─> build (multi-arch images pushed to GHCR)
                                                                                                                         └─> Deploy (deploy.yml)
```

Every Wednesday at 20:00 UTC `weekly-merge.yml` releases `develop` into `main` (it does nothing if `develop` has nothing new):
it opens a pull request, approves it as `github-actions[bot]` and squash merges it (`main` requires 1 approval and a linear history),
then merges `main` back into `develop` with the `ours` strategy so the next PR starts from the squash commit. The merge is pushed
with the `RELEASE_TOKEN` secret, so the push event fires Build Images and Deploy as for any other push to `main`. If it fails
(e.g. conflicts) the PR stays open and the next run reuses it. It can also be run by hand from the Actions tab.

Setup: a fine-grained PAT of the repository owner for this repository with *Contents* and *Pull requests* read and write, stored
as the `RELEASE_TOKEN` repository secret, and *Settings → Actions → General → Allow GitHub Actions to create and approve pull requests*
enabled (for the approval).

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

## Files

| File | Purpose |
|---|---|
| `smoke-test.sh` | Checks a running stack through Caddy: `GET /api/sites` returns a non-empty catalog read from MySQL, and the page and every local asset it references are served. Usage: `smoke-test.sh [BASE_URL]` (default `http://127.0.0.1:8089`), waits up to `SMOKE_TIMEOUT` seconds (default 180) for the backend |
| `compose.ci.yml` | Compose override that builds `backend` and `frontend` from the checkout instead of using the published `:latest` images |

## When validate fails

- The run marks the failing step. The smoke test prints a `[FAIL]` line per failed check, with a hint of where to look, and adds it as an annotation on the run summary.
- If the startup check fails, **Startup check - container status and logs** prints `docker compose ps -a` (crashed or restarting containers),
  annotates the innermost `Caused by:` of the backend's first start (usually the root cause of a Spring startup failure,
  e.g. `Access denied for user ...` or the SQL error of a broken migration) and prints each service's logs in a collapsible group.

## Running it locally

`tools/ci/smoke-test.sh [BASE_URL]` only sends GET requests, so it can check any running stack.

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
