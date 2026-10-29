# CI tooling

Files used by the GitHub Actions pipeline in `.github/workflows/`.

## Pipeline

```

Weekly merge (weekly-merge.yml, Wed 21:00 UTC): PR develop ─> main (squash) ─┐
push to main ────────────────────────────────────────────────────────────────┴─> Build Images (build.yml): validate ─> build (multi-arch images pushed to GHCR)
                                                                                                                         └─> Deploy (deploy.yml): mark the running version as known-good ─> deploy on the Pi
                                                                                                                                                  ─> post-deployment smoke test ─> rollback if anything failed
```

Every Wednesday at 21:00 UTC `weekly-merge.yml` releases `develop` into `main` (it does nothing if `develop` has nothing new):
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
| Rollback - test rollback.sh | `test-rollback.sh` fails: `rollback.sh` no longer marks or restores the known-good images as it should (tested against fake `podman` and `podman-compose`, no container runs) |
| Model lab - unit tests | `make unit` fails: the random shutdown of models of `fractal_model_lab` (`random`, `random_pct`, `seed`) breaks one of its rules, miscounts the models or no longer gives the same schema for the same seed (`fractal_model_lab/tests/prune_tests.c` prints a `[FAIL]` line per failed check) |
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
and the frontend is served, then the same through the public URL. Deploy fails if any check fails, and rolls back to the version it replaced, see [Rollback](#rollback).

| Step | Fails when |
|---|---|
| Deploy | An image cannot be pulled or `podman-compose up` fails |
| Smoke test - deployed stack | `smoke-test.sh http://127.0.0.1:8089` (Caddy) fails on the Pi: the backend does not answer within 120 s (Spring initialization, Flyway migrations on the production data, database connection), Caddy does not route `/api/*`, or the page or one of its assets is not served |
| Smoke test - public URL | The same checks fail at `https://raspberrypi.tail0a4b52.ts.net/terra-pulse`, through Tailscale Funnel, as browsers reach the app (the frontend calls `../api/sites`, under the `/terra-pulse` prefix). Only runs once the stack passed, so the cause is in front of Caddy: the Funnel mapping (`tailscale serve status` on the Pi) or a URL that ignores the prefix, e.g. an absolute asset path |

## Rollback

Deploy keeps the version it replaces on the Pi, so that a failed deployment goes back to it without pulling or building anything: a rollback only
recreates the backend and frontend containers. `rollback.sh` does it, run on the Pi like the smoke test:

1. **Before deploying**, Deploy smoke tests the running version (one attempt). If it passes, `rollback.sh mark` tags the images its backend and frontend
   containers run as `known-good`: `ghcr.io/s4nxez/nisar-sar-change-detection-{back,front}:known-good`, local tags on the Pi, never pushed.
   If it fails, the `known-good` images marked before stay, so they always are the last version that passed the smoke test before being replaced.
2. **If the deployment or a smoke test fails**, or the run is cancelled, `rollback.sh restore` runs once the logs are printed: it tags the `known-good`
   images as `latest`, the tag `podman-compose.yml` runs, removes the backend and frontend containers that don't run them and recreates them with
   `podman-compose up -d`, which also creates any other missing container of the stack (e.g. after a deployment stopped half-way). The smoke test then
   checks the restored version. The run still fails, as the deployment did, and a `Rollback` annotation says what production runs.

| Step | Fails when |
|---|---|
| Rollback - mark the running version as known-good | Never fails the run. A warning says when the running version was not marked (it fails the smoke test, or tagging failed): a failed deployment then rolls back to the `known-good` images marked before, if any |
| Rollback - restore the known-good version | There are no `known-good` images or `podman-compose.yml` can't be read (nothing is changed then), or a recreated container does not run its `known-good` image |
| Rollback - smoke test | The restored version fails the smoke test too: the problem is not in the application images (the database, Caddy, the Pi), fix it on the Pi |

Deployments run one at a time (concurrency group `deploy-production`), so a rollback never undoes another run's deployment.

What a rollback changes, and what not:

- Only the `backend` and `frontend` containers of this stack, found by their compose labels. MySQL keeps running with its `mysql_data` volume,
  Caddy keeps running (both are only created if missing), and no other container, volume, network or pod of the Pi is touched. Nothing is pulled or pruned.
- The database is not rolled back: what the failed version wrote, and the Flyway migrations it applied, stay. The `known-good` backend still starts,
  Flyway ignores migrations newer than its own (`*:future` by default), as long as migrations are backward compatible: add tables and columns, and drop
  or rename them in a later deployment, once no version that may be rolled back to uses them.
- `known-good` is one version back: the one the last deployment replaced. Going further back needs a revert on `main`, built and deployed by the pipeline.
- The restored version stays until the next deployment: push the fix, or a revert, to `main`. Re-running the failed Deploy run deploys the same images again.
- `podman image prune` keeps the `known-good` images, they are tagged. `podman image prune -a` and `podman system prune -a` delete them while no container uses them.

### Rolling back by hand

For a deployment that passed the smoke tests but is faulty, or when Deploy could not roll back (e.g. the runner lost the connection to the Pi).
Not while a Deploy run is in progress: the concurrency group only keeps Deploy runs apart.

```bash
# On the Pi. From another machine: ssh <pi> 'bash -s -- restore' < tools/ci/rollback.sh
cd /opt/NISAR-SAR-Change-Detection
tools/ci/rollback.sh status    # images the backend and frontend containers run, latest and known-good (read-only)
tools/ci/rollback.sh restore   # back to the known-good images
tools/ci/smoke-test.sh         # check the restored version
```

`rollback.sh` acts on the stack that runs from `DEPLOY_DIR` (default `/opt/NISAR-SAR-Change-Detection`, the production checkout, with its
`podman-compose.yml` and `.env`); the script itself can come from any checkout that has it. If `restore` fails after removing containers, `latest`
already points to the `known-good` images: `podman-compose up -d` in `/opt/NISAR-SAR-Change-Detection` recreates them.
Without the script, the same by hand (it recreates the whole stack, as Deploy does; the database keeps its data):

```bash
cd /opt/NISAR-SAR-Change-Detection
for image in back front; do
  podman tag ghcr.io/s4nxez/nisar-sar-change-detection-$image:known-good ghcr.io/s4nxez/nisar-sar-change-detection-$image:latest
done
podman-compose up -d --force-recreate
```

## Files

| File | Purpose |
|---|---|
| `smoke-test.sh` | Checks a running stack through Caddy: `GET /api/sites` returns a non-empty catalog read from MySQL, and the page and every local asset it references are served. Usage: `smoke-test.sh [BASE_URL]` (default `http://127.0.0.1:8089`), waits up to `SMOKE_TIMEOUT` seconds (default 180) for the backend. Used by the startup check and the post-deployment smoke test |
| `rollback.sh` | Rollback of the stack on the Pi to its `known-good` images: `status` (read-only), `mark` (tags the images the backend and frontend containers run as `known-good`), `restore` (switches those containers back to them). Used by Deploy and by hand, see [Rollback](#rollback) |
| `test-rollback.sh` | Tests of `rollback.sh` against fake `podman` and `podman-compose` commands: no container runs, only bash is needed. Run by validate |
| `compose.ci.yml` | Compose override that builds `backend` and `frontend` from the checkout instead of using the published `:latest` images |

## When validate fails

- The run marks the failing step. The smoke test prints a `[FAIL]` line per failed check, with a hint of where to look, and adds it as an annotation on the run summary.
- If the startup check fails, **Startup check - container status and logs** prints `docker compose ps -a` (crashed or restarting containers),
  annotates the innermost `Caused by:` of the backend's first start (usually the root cause of a Spring startup failure,
  e.g. `Access denied for user ...` or the SQL error of a broken migration) and prints each service's logs in a collapsible group.

## When Deploy fails

- The smoke test output is the same as in validate: a `[FAIL]` line per failed check, with a hint, also annotated on the run summary.
- If the deployment or the deployed stack check failed, **Smoke test - container status and logs** prints `podman-compose ps` from the Pi,
  annotates the innermost `Caused by:` of the new backend's first start and prints the backend and mysql logs in collapsible groups,
  before the rollback removes those containers.
  Caddy and frontend logs are not printed: they record visitors' IP addresses and the Actions logs of this public repository are public.
  Read them on the Pi with `podman-compose logs caddy frontend` in `/opt/NISAR-SAR-Change-Detection`.
- Then Deploy rolls back (see [Rollback](#rollback)): the `Rollback` annotations say whether production runs the `known-good` version again or
  still needs a hand. To re-check production at any time, run `tools/ci/smoke-test.sh` on the Pi (see below).

## Running it locally

`tools/ci/smoke-test.sh [BASE_URL]` only sends GET requests, so it can check any running stack, production included: on the Pi, without arguments
it checks the deployed stack as Deploy does, and `tools/ci/smoke-test.sh https://raspberrypi.tail0a4b52.ts.net/terra-pulse` checks the public URL.
`tools/ci/test-rollback.sh` runs anywhere with bash (it fakes podman): run it after changing `rollback.sh`.

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
