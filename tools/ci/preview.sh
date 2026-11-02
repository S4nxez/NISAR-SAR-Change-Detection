#!/usr/bin/env bash
# PR previews on the develop stack of the Raspberry Pi: the backend and frontend of a pull request, next to the
# develop stack and served by its Caddy under /pr-<N>/ (the Caddyfile, with NISAR_PR_PREVIEWS=true).
#
# Usage: tools/ci/preview.sh deploy|remove|status PR_NUMBER
#        tools/ci/preview.sh list
#   deploy   pull the pr-<N> images and (re)start the preview of pull request N from scratch: containers
#            nisar-pr-<N>-mysql (its own, empty: Flyway fills it with the demo data), nisar-pr-<N>-backend and
#            nisar-pr-<N>-frontend on the develop stack's network. The develop stack itself is not changed. Run by
#            PR preview (preview.yml) on every push to the pull request.
#   remove   remove the preview: its containers, their data and its local images. Run when the pull request is
#            closed. Does nothing for what is already gone.
#   status   the preview's containers and images (read-only)
#   list     every preview on the Pi (read-only)
#
#   DEPLOY_DIR    the develop stack's checkout (default: /opt/NISAR-SAR-Change-Detection-develop), whose running caddy
#                 container serves the previews, found by the labels podman-compose sets
#   MAX_PREVIEWS  previews that may run at once, this one included (default: 3): each one is a MySQL and a backend
#   MIN_FREE_MB   deploy refuses with less free space for podman's images (default: 2048, as Deploy for develop)
#   PREVIEW_PULL  false: deploy runs the local pr-<N> images instead of pulling them (testing by hand)
#
# Each preview has its own MySQL: the migrations use the NisarSar database by name (USE NisarSar), so previews can't
# share the develop stack's MySQL without writing into develop's data. Previews never touch production: they only
# join the develop stack's network, and every name they use carries the pull request number (containers, tag pr-<N>).
#
# Exits 1 if the command fails, 2 on usage errors. Needs podman.
#
# PR preview runs it on the Raspberry Pi from stdin (ssh ... bash -s -- COMMAND N): no command may read stdin, it
# would eat the rest of the script.
set -euo pipefail

REGISTRY=ghcr.io/s4nxez
declare -A REPOSITORY=(
  [backend]=$REGISTRY/nisar-sar-change-detection-back
  [frontend]=$REGISTRY/nisar-sar-change-detection-front
)
LABEL=nisar.preview.pr

usage_error() { echo "preview: $*" >&2; exit 2; }

# Every podman call reads /dev/null, not the script (see above), unless given its own stdin (mysql below)
podman() { command podman "$@" </dev/null; }

annotate() {
  if [[ "${GITHUB_ACTIONS:-}" == true ]]; then
    local message="${2//%/%25}"
    printf '::%s title=PR preview::%s\n' "$1" "${message//$'\n'/%0A}"
  fi
}

fail() {
  printf '[FAIL] %s\n' "$1"
  annotate error "$1"
  exit 1
}

# develop_container SERVICE: ID of the running container of SERVICE in the develop stack
develop_container() {
  local out
  out="$(podman ps --no-trunc \
    --filter "label=com.docker.compose.project.working_dir=$DEPLOY_DIR" \
    --filter "label=com.docker.compose.service=$1" \
    --filter status=running --format '{{.ID}}')" || fail "podman ps failed (see the error above)"
  [[ -n "$out" && "$out" != *$'\n'* ]] \
    || fail "The develop stack ($DEPLOY_DIR) has no running $1 container: the previews run on it, deploy develop first (tools/ci/README.md)"
  printf '%s' "$out"
}

# preview_containers [N]: "<name> <state> <image ID>" per preview container (of pull request N)
preview_containers() {
  podman ps -a --no-trunc --filter "label=$LABEL${1:+=$1}" --format '{{.Names}} {{.State}} {{.ImageID}}' \
    || fail "podman ps failed (see the error above)"
}

# describe IMAGE: "image <short ID>, built <date>[, commit <short SHA>]", as rollback.sh
describe() {
  local out id created revision
  out="$(podman image inspect --format \
    '{{.Id}}|{{.Created.Format "2006-01-02 15:04 MST"}}|{{index .Labels "org.opencontainers.image.revision"}}' "$1")"
  IFS='|' read -r id created revision <<<"$out"
  printf 'image %s, built %s%s' "${id:0:12}" "$created" "${revision:+, commit ${revision:0:7}}"
}

image_id() {
  if podman image exists "$1"; then podman image inspect --format '{{.Id}}' "$1"; fi
}

cmd_status() {
  local service ref id rows
  echo "Preview of pull request #$PR (/pr-$PR/ on the develop stack)"
  rows="$(preview_containers "$PR")"
  if [[ -z "$rows" ]]; then echo "  no container"; fi
  while read -r name state image; do
    [[ -n "$name" ]] && printf '  %s: %s, %s\n' "$name" "$state" "$(describe "$image")"
  done <<<"$rows"
  for service in backend frontend; do
    ref="${REPOSITORY[$service]}:$TAG"
    id="$(image_id "$ref")"
    if [[ -n "$id" ]]; then printf '  %s: %s\n' "$ref" "$(describe "$id")"; fi
  done
}

cmd_list() {
  local rows
  rows="$(podman ps -a --filter "label=$LABEL" --format "{{index .Labels \"$LABEL\"}} {{.Names}} {{.State}} {{.RunningFor}}" \
    | sort -n)" || fail "podman ps failed (see the error above)"
  if [[ -z "$rows" ]]; then echo "No PR preview on the Pi"; else echo "$rows"; fi
}

cmd_deploy() {
  local service ref network others free_mb
  local -A old=()
  # The develop stack's Caddy, whose network the preview joins
  local caddy
  caddy="$(develop_container caddy)"
  [[ "$(podman exec "$caddy" printenv NISAR_PR_PREVIEWS || true)" == true ]] \
    || fail "The develop stack's Caddy does not route PR previews: set NISAR_PR_PREVIEWS=true in $DEPLOY_DIR/.env, update its Caddyfile and podman-compose.yml (git pull) and run podman-compose up -d caddy there (tools/ci/README.md)"
  network="$(podman inspect --format '{{range $name, $_ := .NetworkSettings.Networks}}{{$name}}{{"\n"}}{{end}}' "$caddy" | head -n 1)"
  [[ -n "$network" ]] || fail "Could not find the network of the develop stack's Caddy"

  # Room for it: the other previews, and the disk production uses too
  others="$(podman ps -a --filter "label=$LABEL" --format "{{index .Labels \"$LABEL\"}}" | grep -vxF "$PR" | sort -u | paste -sd ' ' || true)"
  if [[ -n "$others" ]] && (( $(wc -w <<<"$others") >= MAX_PREVIEWS )); then
    fail "$MAX_PREVIEWS PR previews already run (pull requests $others), the limit (MAX_PREVIEWS): close a pull request, or remove its preview on the Pi with tools/ci/preview.sh remove <N>"
  fi
  free_mb="$(df --output=avail -m "$(podman info --format '{{.Store.GraphRoot}}')" | tail -n 1)"
  free_mb="${free_mb//[[:space:]]/}"
  [[ "$free_mb" =~ ^[0-9]+$ ]] || fail "Could not read the free disk space on the Pi (got '$free_mb')"
  (( free_mb >= MIN_FREE_MB )) \
    || fail "Only $free_mb MB free on the Pi, the preview is not deployed below $MIN_FREE_MB MB to keep room for production: free space on the Pi, e.g. podman image prune"

  # Pulled before anything is removed: a failed pull keeps the running preview
  for service in backend frontend; do
    ref="${REPOSITORY[$service]}:$TAG"
    old[$service]="$(image_id "$ref")"
    if [[ "$PREVIEW_PULL" != false ]]; then
      podman pull -q "$ref" >/dev/null || fail "Could not pull $ref (see the error above)"
    fi
    [[ -n "$(image_id "$ref")" ]] || fail "No $ref image on the Pi"
    echo "$service: $ref, $(describe "$ref")"
  done

  remove_containers

  # The password goes through a file, not the command line. Global: the EXIT trap also removes it when a failure exits
  ENV_FILE="$(mktemp)"
  trap 'rm -f "$ENV_FILE"' EXIT
  printf 'MYSQL_ROOT_PASSWORD=%s\n' "$(od -An -N16 -tx1 /dev/urandom | tr -d ' \n')" > "$ENV_FILE"

  # From scratch on every deployment, no volume (the image's anonymous one goes with the container): the pull request
  # may have changed migrations Flyway already applied. Small buffers, it only holds the demo data
  local mysql="nisar-pr-$PR-mysql" waited=0
  podman run -d --name "$mysql" --network "$network" --restart always --label "$LABEL=$PR" --env-file "$ENV_FILE" \
    -e MYSQL_DATABASE=NisarSar \
    --health-cmd 'mysqladmin ping -h 127.0.0.1 -uroot -p"$MYSQL_ROOT_PASSWORD" --silent' --health-interval 5s \
    "$MYSQL_IMAGE" --performance-schema=OFF --innodb-buffer-pool-size=32M >/dev/null \
    || fail "Could not start the MySQL of the preview (see the error above)"
  # The backend gives up after 5 failed starts: it only starts once MySQL answers
  until [[ "$(podman inspect --format '{{.State.Health.Status}}' "$mysql")" == healthy ]]; do
    if (( waited >= MYSQL_TIMEOUT )); then
      podman logs --tail 20 "$mysql" 2>&1 | sed 's/^/  mysql: /'
      fail "The MySQL of the preview was not healthy within ${MYSQL_TIMEOUT}s (its last log lines above)"
    fi
    podman healthcheck run "$mysql" >/dev/null 2>&1 || true
    sleep 5
    waited=$((waited + 5))
  done
  echo "database: $mysql, empty, healthy after ${waited}s"

  # As the develop stack's backend (podman-compose.yml), with its server/.env
  printf 'DB_URL=jdbc:mysql://%s:3306/NisarSar\nDB_USER=root\nDB_PASSWORD=%s\nSPRING_PROFILES_ACTIVE=spring\n' \
    "$mysql" "$(sed -n 's/^MYSQL_ROOT_PASSWORD=//p' "$ENV_FILE")" >> "$ENV_FILE"
  local env_files=(--env-file "$ENV_FILE")
  if [[ -f "$DEPLOY_DIR/server/.env" ]]; then env_files=(--env-file "$DEPLOY_DIR/server/.env" "${env_files[@]}"); fi

  podman run -d --name "nisar-pr-$PR-backend" --network "$network" --restart on-failure:5 \
    --label "$LABEL=$PR" "${env_files[@]}" "${REPOSITORY[backend]}:$TAG" >/dev/null \
    || fail "Could not start the backend of the preview (see the error above)"
  podman run -d --name "nisar-pr-$PR-frontend" --network "$network" --restart always \
    --label "$LABEL=$PR" "${REPOSITORY[frontend]}:$TAG" >/dev/null \
    || fail "Could not start the frontend of the preview (see the error above)"
  echo "containers: $mysql, nisar-pr-$PR-backend, nisar-pr-$PR-frontend on $network"

  # The images the previous deployment ran, untagged by the pull: deleted unless something else uses them
  for service in backend frontend; do
    if [[ -n "${old[$service]}" && "${old[$service]}" != "$(image_id "${REPOSITORY[$service]}:$TAG")" ]] \
      && [[ "$(podman image inspect --format '{{len .RepoTags}}' "${old[$service]}" 2>/dev/null)" == 0 ]]; then
      podman rmi "${old[$service]}" >/dev/null 2>&1 && echo "$service: deleted the previous image ${old[$service]:0:12}" || true
    fi
  done
  echo "Deployed: the preview of pull request #$PR answers under /pr-$PR/ of the develop stack, smoke test it with tools/ci/smoke-test.sh"
}

remove_containers() {
  local rows name
  rows="$(preview_containers "$PR")"
  while read -r name _; do
    if [[ -n "$name" ]]; then
      # --volumes: the MySQL data of the preview
      podman rm --force --volumes "$name" >/dev/null || fail "Could not remove the container $name (see the error above)"
      echo "removed container $name"
    fi
  done <<<"$rows"
}

cmd_remove() {
  local service ref
  remove_containers
  # Only the pr-<N> names: podman rmi of a name deletes the image only if no other name or container uses it
  for service in backend frontend; do
    ref="${REPOSITORY[$service]}:$TAG"
    if podman image exists "$ref"; then
      podman rmi "$ref" >/dev/null || fail "Could not remove the image $ref (see the error above)"
      echo "removed image $ref"
    fi
  done
  echo "Removed the preview of pull request #$PR"
}

DEPLOY_DIR="${DEPLOY_DIR:-/opt/NISAR-SAR-Change-Detection-develop}"
MAX_PREVIEWS="${MAX_PREVIEWS:-3}"
MIN_FREE_MB="${MIN_FREE_MB:-2048}"
PREVIEW_PULL="${PREVIEW_PULL:-true}"
# The develop stack's (podman-compose.yml)
MYSQL_IMAGE=docker.io/library/mysql:8
MYSQL_TIMEOUT=120
[[ "$MAX_PREVIEWS" =~ ^[1-9][0-9]*$ ]] || usage_error "MAX_PREVIEWS must be a positive number, got '$MAX_PREVIEWS'"
[[ "$MIN_FREE_MB" =~ ^[0-9]+$ ]] || usage_error "MIN_FREE_MB must be a number, got '$MIN_FREE_MB'"
[[ -f "$DEPLOY_DIR/podman-compose.yml" ]] || usage_error "DEPLOY_DIR=$DEPLOY_DIR has no podman-compose.yml (the develop stack's checkout)"
# As podman-compose labels the containers: absolute path, symlinks resolved
DEPLOY_DIR="$(cd "$DEPLOY_DIR" && pwd -P)"
[[ "$DEPLOY_DIR" != "$(cd /opt/NISAR-SAR-Change-Detection 2>/dev/null && pwd -P || true)" ]] \
  || usage_error "DEPLOY_DIR=$DEPLOY_DIR is production's checkout: previews only run on the develop stack"

case "${1:-}" in
  list)
    (( $# == 1 )) || usage_error "usage: preview.sh list"
    cmd_list ;;
  deploy|remove|status)
    (( $# == 2 )) || usage_error "usage: preview.sh $1 PR_NUMBER"
    [[ "$2" =~ ^[1-9][0-9]{0,5}$ ]] || usage_error "PR_NUMBER must be a pull request number, got '$2'"
    PR="$2" TAG="pr-$2"
    "cmd_$1" ;;
  *) usage_error "usage: preview.sh deploy|remove|status PR_NUMBER, or preview.sh list" ;;
esac
