# CI tooling

Files used by the GitHub Actions pipeline in `.github/workflows/`.

## Pipeline

```

Weekly merge (weekly-merge.yml, Wed 21:00 UTC): PR develop ─> main (squash) ─┐
push to main ────────────────────────────────────────────────────────────────┴─> Build Images (build.yml): validate ─> build (multi-arch images pushed to GHCR)
                                                                                                                         └─> Deploy (deploy.yml): mark the running version as known-good ─> deploy on the Pi
                                                                                                                                                  ─> post-deployment smoke test ─> rollback if anything failed
push to main ─> Sync main into develop (sync-main.yml): merges main back into develop, so the next release PR doesn't conflict
push to develop ─> Develop (develop.yml): the same Build Images (images tagged develop) and Deploy, to the develop stack on the Pi (QA)
pull request into develop ─> PR preview (preview.yml): the same Build Images (images tagged pr-<N>), then preview.sh runs them next to the
                             develop stack, at <develop URL>/pr-<N>/, linked in a comment. Closing the pull request removes it
```

Every push to `develop` goes through the same pipeline, with the same workflows, to its own stack on the Raspberry Pi: developers QA it there
before the weekly merge releases it to production. See [Develop stack](#develop-stack). Before that, every pull request into `develop` gets its
own preview, see [PR previews](#pr-previews).

Every Wednesday at 21:00 UTC `weekly-merge.yml` releases `develop` into `main` (it does nothing if `develop` has nothing new):
it opens a pull request, approves it as `github-actions[bot]` and squash merges it (`main` requires 1 approval and a linear history).
The merge is pushed with the `RELEASE_TOKEN` secret, so the push event fires Build Images and Deploy as for any other push to `main`.
If it fails (e.g. conflicts) the PR stays open and the next run reuses it. It can also be run by hand from the Actions tab.

Every push to `main` also runs `sync-main.yml`, which merges `main` back into `develop` so the next release PR starts from it:
with the `ours` strategy when `main` is a squash merge of `develop` (its tree is that of a `develop` commit), with a normal merge
otherwise (e.g. a hotfix pushed to `main`). It runs whoever pushed, so `develop` can also be released by hand: squash merge a PR
`develop` -> `main` from the GitHub UI. If the merge conflicts the job fails and `main` must be merged into `develop` by hand, with a
pull request into `develop` merged with a merge commit (a squash would not record `main` as merged and the release PR would conflict).

Setup: a fine-grained PAT of the repository owner for this repository with *Contents* and *Pull requests* read and write, stored
as the `RELEASE_TOKEN` repository secret, and *Settings → Actions → General → Allow GitHub Actions to create and approve pull requests*
enabled (for the approval).

`validate` is the pre-deployment validation stage. `build` needs it and Deploy only runs when the whole Build Images workflow succeeds
(Develop's deploy job only once its images job succeeds), so if any check fails no image is pushed and the Raspberry Pi keeps running the current version.

| Step | Fails when |
|---|---|
| Frontend - check JavaScript syntax | An ES module under `frontend/` has a syntax error (`node --check`, the frontend has no build step) |
| Frontend - run unit tests | A test under `frontend/tests` fails (`npm test`: `node:test`, with `jsdom` for the page tests). They also check that every page declares its icon and that no local URL starts with `/`, which would escape the path prefix of production, develop and PR previews |
| Processing - run unit tests | A test under `processing/tests` fails (`unittest`, no network access): water mask, routes, catalog, OpenStreetMap places, river gauge, remote reads and the commands of the river lifeline monitor. The `lifeline` package is installed from `processing/pyproject.toml` (pinned dependencies) |
| Rollback - test rollback.sh | `test-rollback.sh` fails: `rollback.sh` no longer marks or restores the known-good images as it should (tested against fake `podman` and `podman-compose`, no container runs) |
| Preview - test preview.sh | `test-preview.sh` fails: `preview.sh deploy` no longer starts a preview as it should, e.g. without the develop stack's river record (tested against a fake `podman`, no container runs) |
| Model lab - compile | `fractal_model_lab` does not compile from sources (`-Werror`, so warnings too) |
| Backend - compile, run tests and package | `mvn verify` fails: compilation errors or failing tests (every test under `server/src/test` runs) |
| Startup check - prepare environment | `podman-compose.yml` plus `compose.ci.yml` is not a valid compose configuration |
| Startup check - build images | A `Containerfile` does not build |
| Startup check - start stack | A container cannot start or MySQL never becomes healthy |
| Startup check - smoke test | `smoke-test.sh` fails: Spring initialization, Flyway migrations, database connection, Caddy routing or frontend assets |

The startup check runs the production `podman-compose.yml` (services, env vars, healthcheck, `Caddyfile`, published port) with `docker compose`,
layered with `compose.ci.yml`, against a fresh database with throwaway credentials. The river lifeline worker (`monitor`) is built from the
commit too, but there it only prints its help and exits: the check never contacts NASA.

### River lifeline worker

The `monitor` service runs the processing image (`nisar-sar-change-detection-processing`, built by Build Images for `latest` and `develop`,
not for PR previews) and writes the record to the stack's `monitor_data` volume, which the backend mounts read-only and serves under
`/api/monitor` (see `docs/river-monitor.md`). It reads NISAR products with `EARTHDATA_TOKEN` from the stack's `.env`; without it each round
fails and is logged (`podman-compose logs monitor`) and the page says the record has not been built. Each stack has its own volume, so production
and develop process the passes separately; PR previews read develop's (see [PR previews](#pr-previews)). `rollback.sh` only switches the
backend and the frontend: the worker keeps the deployed image.

## Post-deployment smoke test

Once Deploy has pulled the images and recreated the stack on the Raspberry Pi, it runs `smoke-test.sh` from the deployed commit on the Pi
(`ssh ... bash -s`), so the checks hit production itself: the new backend starts against the production database and its data, Caddy routes `/api/*`
and the frontend is served, then the same through the public URL. Deploy fails if any check fails, and rolls back to the version it replaced, see [Rollback](#rollback).

| Step | Fails when |
|---|---|
| Check the stack settings | A setting of the stack to deploy is not valid, or a stack other than production uses production's checkout, image tag or port ([Develop stack](#develop-stack)) |
| Check the stack on the Pi | The stack's checkout has no `podman-compose.yml`, `.env` or `server/.env` (the develop stack is not set up yet), or a stack other than production would be deployed with less than 2 GB free on the Pi. Nothing has changed then |
| Deploy | An image cannot be pulled or `podman-compose up` fails |
| Smoke test - deployed stack | `smoke-test.sh http://127.0.0.1:8089` (Caddy) fails on the Pi: the backend does not answer within 120 s (Spring initialization, Flyway migrations on the production data, database connection), Caddy does not route `/api/*`, or the page or one of its assets is not served |
| Smoke test - public URL | The same checks fail at `https://raspberrypi.tail0a4b52.ts.net/terra-pulse`, through Tailscale Funnel, as browsers reach the app (the frontend calls `../api/sites`, under the `/terra-pulse` prefix). Only runs once the stack passed, so the cause is in front of Caddy: the Funnel mapping (`tailscale serve status` on the Pi) or a URL that ignores the prefix, e.g. an absolute asset path |

## Rollback

Deploy keeps the version it replaces on the Pi, so that a failed deployment goes back to it without pulling or building anything: a rollback only
recreates the backend and frontend containers. `rollback.sh` does it, run on the Pi like the smoke test (below for production; the develop stack
does the same with its own tags, `develop` and `develop-known-good`, see [Develop stack](#develop-stack)):

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
`podman-compose.yml` and `.env`; another stack also needs its `NISAR_IMAGE_TAG`, see [Develop stack](#develop-stack)); the script itself can
come from any checkout that has it. If `restore` fails after removing containers, `latest`
already points to the `known-good` images: `podman-compose up -d` in `/opt/NISAR-SAR-Change-Detection` recreates them.
Without the script, the same by hand (it recreates the whole stack, as Deploy does; the database keeps its data):

```bash
cd /opt/NISAR-SAR-Change-Detection
for image in back front; do
  podman tag ghcr.io/s4nxez/nisar-sar-change-detection-$image:known-good ghcr.io/s4nxez/nisar-sar-change-detection-$image:latest
done
podman-compose up -d --force-recreate
```

## Develop stack

A second deployment of the app on the Pi, from `develop`, for QA: what is merged into `develop` runs there first, and only reaches production
with the weekly merge. Every push to `develop` runs **Develop** (`develop.yml`), which calls the production workflows themselves:

1. **Build Images** (`build.yml`): the same `validate` stage, then the images are pushed tagged `develop` instead of `latest`.
2. **Deploy** (`deploy.yml`): the same deployment, smoke tests and rollback, on the develop stack. If anything fails, it rolls back to `develop-known-good`.

Called from `develop`, both workflows run as they are in the pushed commit: a change to the pipeline itself is tried on the develop stack before
it reaches `main`. Run on their own (a push to `main`, Build Images on `main`) they build and deploy production, as before. Develop runs one at a
time (concurrency group `develop`), so an older run never pushes or deploys `develop` images after a newer one. The sync of
`main` into `develop` (`sync-main.yml`) is pushed with `GITHUB_TOKEN`, which starts no workflow: it doesn't redeploy the develop stack (after a squash merge it changes nothing in it).

The two stacks share nothing but the host:

| | Production | Develop stack |
|---|---|---|
| Branch, workflows | `main`: Build Images, then Deploy | `develop`: Develop, calling both |
| Images (GHCR) | `:latest` | `:develop` |
| Rollback tag (Pi only) | `:known-good` | `:develop-known-good` |
| Checkout on the Pi | `/opt/NISAR-SAR-Change-Detection` | `/opt/NISAR-SAR-Change-Detection-develop` |
| Containers, database, volumes | compose project `nisar-sar-change-detection` | compose project `nisar-sar-change-detection-develop` (from the directory name): its own MySQL and data |
| Caddy | `127.0.0.1:8089` | `127.0.0.1:8090` |
| Public URL | `https://raspberrypi.tail0a4b52.ts.net/terra-pulse` | the `DEVELOP_PUBLIC_URL` variable, if set (see below) |
| Deploy concurrency group | `deploy-production` | `deploy-develop`: the two may deploy at the same time |

`podman-compose.yml` reads the tag and the port from `NISAR_IMAGE_TAG` and `NISAR_HTTP_PORT`, by default `latest` and `8089`: production runs
the defaults and the develop checkout sets them in its `.env`. Deploy also passes them to `podman-compose` and `rollback.sh`, whatever the `.env`
says. Safeguards keep a mistake on the develop side away from production:

- Deploy refuses to deploy a stack other than production to production's checkout, with `latest` or on port 8089.
- `rollback.sh` never changes `latest` or `known-good` for another checkout than production's: without `NISAR_IMAGE_TAG=develop` it refuses to run on the develop checkout.
- Build Images only pushes `latest` from `main`.
- Deploy doesn't deploy the develop stack with less than 2 GB free on the Pi (`MIN_FREE_MB`): the disk is production's too, and every deployment
  leaves the images it replaced behind (about 55 MB for a new backend, more when a base image changes). Free space with `podman image prune`:
  it removes the images that no tag and no container use, on the whole Pi (`latest`, `known-good`, `develop` and `develop-known-good` stay).

The develop stack runs a second MySQL, backend, frontend and Caddy: about 900 MB of RAM, as much as production's.

### Setting up the develop stack

Once, on the Pi, after this pipeline is merged into `develop`. Until then every Develop run fails at **Check the stack on the Pi**, before anything
changes on the Pi:

```bash
git clone --branch develop https://github.com/S4nxez/NISAR-SAR-Change-Detection.git /opt/NISAR-SAR-Change-Detection-develop
cd /opt/NISAR-SAR-Change-Detection-develop
# Its own database password. NISAR_* make podman-compose, run by hand here, act on the develop stack too. Add
# EARTHDATA_TOKEN=<NASA Earthdata token> for the river lifeline worker (see "River lifeline worker" above)
printf 'MYSQL_ROOT_PASSWORD=%s\nMYSQL_USER=root\nNISAR_IMAGE_TAG=develop\nNISAR_HTTP_PORT=8090\n' "$(openssl rand -hex 16)" > .env
: > server/.env
chmod 600 .env server/.env
```

Write this `.env` from scratch rather than copying production's, and never set `COMPOSE_PROJECT_NAME` in it: the compose project comes from the
directory name, which keeps the containers and the database of the two stacks apart. Then re-run the failed Develop run (or push to `develop`).
The first deployment creates the develop database (Flyway migrations and their demo data) and has no `develop-known-good` to roll back to yet.
Like production's, the checkout is only updated by hand (`git pull`): Deploy only pulls images and recreates the containers.

To QA it:

- On the Pi: `http://127.0.0.1:8090`. From another machine: `ssh -L 8090:127.0.0.1:8090 sanxez@<pi>`, then `http://localhost:8090`.
- Publicly, like production: `tailscale funnel --bg --set-path /terra-pulse-dev http://127.0.0.1:8090` on the Pi, then set the repository variable
  `DEVELOP_PUBLIC_URL` (*Settings → Secrets and variables → Actions → Variables*) to `https://raspberrypi.tail0a4b52.ts.net/terra-pulse-dev`, so
  Deploy also smoke tests that URL. Without the variable, that check is skipped with a notice.

By hand, run `podman-compose` and `rollback.sh` in the develop checkout (`smoke-test.sh` needs its port):

```bash
cd /opt/NISAR-SAR-Change-Detection-develop
DEPLOY_DIR=$PWD NISAR_IMAGE_TAG=develop tools/ci/rollback.sh status    # read-only
DEPLOY_DIR=$PWD NISAR_IMAGE_TAG=develop tools/ci/rollback.sh restore   # back to develop-known-good
tools/ci/smoke-test.sh http://127.0.0.1:8090
podman-compose logs backend
```

## PR previews

Every pull request into `develop` from a branch of this repository gets a preview, to try its changes before they are merged: **PR preview**
(`preview.yml`) runs on every push to it.

1. **Build Images** (`build.yml`): the same `validate` stage on the pull request merged into `develop` (as GitHub tests pull requests), then
   the images are pushed tagged `pr-<N>`. If validate fails nothing is deployed.
2. **Deploy the preview**: `preview.sh deploy <N>`, run on the Pi like the other scripts, starts three containers on the develop stack's network:
   `nisar-pr-<N>-mysql`, `nisar-pr-<N>-backend` and `nisar-pr-<N>-frontend`. The develop stack's Caddy serves them at `/pr-<N>/`, so the
   preview is at `<develop URL>/pr-<N>/`, e.g. `https://raspberrypi.tail0a4b52.ts.net/terra-pulse-dev/pr-12/`.
3. **Smoke test**: the same `smoke-test.sh`, at `http://127.0.0.1:8090/pr-<N>` on the Pi and at the public URL if `DEVELOP_PUBLIC_URL` is set.
4. **Comment the preview link**: one comment on the pull request, updated on every run, links the preview (or says the deployment failed).

Closing the pull request (merged or not) runs `preview.sh remove <N>`: it removes the three containers, the preview's data and its
`pr-<N>` images on the Pi, and the comment says so. Reopening it deploys it again. A newer push cancels the run of an older one.

How a preview relates to the other stacks:

- **Develop stack**: a preview reuses its network, its Caddy (with `NISAR_PR_PREVIEWS=true`) and its URL, and nothing else: it is not
  changed when a preview is deployed or removed, and redeploying develop leaves the previews running (Caddy finds the preview containers by
  name on every request, with no reload).
- **Database**: each preview has its own MySQL, empty on every deployment (no volume): Flyway runs the pull request's migrations and demo
  data from scratch, so a pull request may change its own migrations. It can't share the develop stack's MySQL, the migrations use the
  `NisarSar` database by name (`USE NisarSar`) and would write into develop's data.
- **River record** (`api/monitor`): the preview's backend mounts the develop stack's `monitor_data` volume read-only
  (`<project>_monitor_data`, written by develop's monitor worker), so a preview shows develop's record. Previews run no monitor worker.
  If develop has no such volume yet, the preview starts without a record and its page says the area is not published.
- **Production**: untouched. `preview.sh` refuses production's checkout, the previews never join production's network, and production's
  Caddy has `NISAR_PR_PREVIEWS` unset, so `/terra-pulse/pr-<N>/` is the app's path as before.
- **Resources**: at most 3 previews at once (`MAX_PREVIEWS`), each a MySQL, a backend and an nginx, about 600 MB of RAM. A fourth pull request's
  preview fails with the list of the running ones, until one is closed. Like develop, nothing is pulled with less than 2 GB free on the Pi.
- **Forks and Dependabot**: no preview. Their pull requests get no secrets, and a fork's code must not run on the Pi.
- The `pr-<N>` images stay in GHCR (the workflow's token can't delete package versions): delete them from the package's page if needed.

### Setting up the PR previews

Once, on the Pi, after this pipeline is merged into `develop`. Until then **Deploy the preview** fails, before anything changes on the Pi:

```bash
cd /opt/NISAR-SAR-Change-Detection-develop
git pull                                     # Caddyfile and podman-compose.yml with the preview routes
echo 'NISAR_PR_PREVIEWS=true' >> .env
podman-compose up -d caddy                   # recreates only the develop stack's Caddy
```

For public links, publish the develop stack as in [Setting up the develop stack](#setting-up-the-develop-stack): `tailscale funnel --bg
--set-path /terra-pulse-dev http://127.0.0.1:8090`, and the `DEVELOP_PUBLIC_URL` variable. The previews come with it, under `/pr-<N>/`.
Without it, the comment gives the URL on the Pi (`ssh -L 8090:127.0.0.1:8090 sanxez@<pi>`, then `http://localhost:8090/pr-<N>/`).

By hand, on the Pi:

```bash
cd /opt/NISAR-SAR-Change-Detection-develop
tools/ci/preview.sh list                     # every preview (read-only)
tools/ci/preview.sh status 12                # its containers and images (read-only)
tools/ci/preview.sh remove 12                # e.g. a preview left behind
tools/ci/smoke-test.sh http://127.0.0.1:8090/pr-12
podman logs nisar-pr-12-backend
```

With previews running, `podman-compose down` in the develop checkout can't remove the network they use: remove them first.

## Files

| File | Purpose |
|---|---|
| `smoke-test.sh` | Checks a running stack through Caddy: `GET /api/sites` returns a non-empty catalog read from MySQL, and the page and every local asset it references are served. Usage: `smoke-test.sh [BASE_URL]` (default `http://127.0.0.1:8089`), waits up to `SMOKE_TIMEOUT` seconds (default 180) for the backend. Used by the startup check and the post-deployment smoke test |
| `rollback.sh` | Rollback of the stack on the Pi to its `known-good` images: `status` (read-only), `mark` (tags the images the backend and frontend containers run as `known-good`), `restore` (switches those containers back to them). `DEPLOY_DIR` and `NISAR_IMAGE_TAG` select the stack, production by default. Used by Deploy and by hand, see [Rollback](#rollback) and [Develop stack](#develop-stack) |
| `test-rollback.sh` | Tests of `rollback.sh` against fake `podman` and `podman-compose` commands, for production's and the develop stack's checkouts: no container runs, only bash is needed. Run by validate |
| `test-preview.sh` | Tests of `preview.sh deploy` against a fake `podman`: the river record it mounts and its failures. No container runs, only bash is needed. Run by validate |
| `preview.sh` | PR previews on the develop stack: `deploy <N>` (its own MySQL, backend and frontend, from scratch, with develop's river record), `remove <N>`, `status <N>`, `list`. Used by PR preview and by hand, see [PR previews](#pr-previews) |
| `pr-comment.sh` | Creates or updates the one comment of `github-actions[bot]` that starts with a marker on a pull request: the preview link |
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
  Read them on the Pi with `podman-compose logs caddy frontend` in the stack's checkout (`/opt/NISAR-SAR-Change-Detection` for production).
- Then Deploy rolls back (see [Rollback](#rollback)): the `Rollback` annotations say whether production runs the `known-good` version again or
  still needs a hand. To re-check production at any time, run `tools/ci/smoke-test.sh` on the Pi (see below).

## Running it locally

`tools/ci/smoke-test.sh [BASE_URL]` only sends GET requests, so it can check any running stack, production included: on the Pi, without arguments
it checks the deployed stack as Deploy does, and `tools/ci/smoke-test.sh https://raspberrypi.tail0a4b52.ts.net/terra-pulse` checks the public URL.
`tools/ci/test-rollback.sh` and `tools/ci/test-preview.sh` run anywhere with bash (they fake podman): run them after changing `rollback.sh`
or `preview.sh`.

To reproduce the whole startup check use a separate worktree, since it writes `.env` and `server/.env`, and not on the Raspberry Pi,
where `127.0.0.1:8089` is the production Caddy (and `127.0.0.1:8090` the develop stack's):

```bash
git worktree add ../nisar-ci HEAD && cd ../nisar-ci
(cd server && mvn -B -ntp verify)
printf 'MYSQL_ROOT_PASSWORD=%s\nMYSQL_USER=root\n' "$(openssl rand -hex 16)" > .env && : > server/.env
export COMPOSE_FILE=podman-compose.yml:tools/ci/compose.ci.yml COMPOSE_PROJECT_NAME=nisarsar-ci
docker compose build && docker compose up -d --no-build
tools/ci/smoke-test.sh
docker compose down -v
```
