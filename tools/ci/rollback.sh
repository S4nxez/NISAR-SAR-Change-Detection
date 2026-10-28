#!/usr/bin/env bash
# Rollback of the deployment on the Raspberry Pi to its known-good application images.
#
# Usage: tools/ci/rollback.sh status|mark|restore
#   status   show the images the backend and frontend containers run and the known-good
#            ones (read-only)
#   mark     tag the images the backend and frontend containers run as known-good, in
#            place of the former ones. Deploy (deploy.yml) runs it before replacing a
#            version that passes the smoke test: known-good is the last version that
#            passed before being replaced.
#   restore  switch the backend and frontend containers back to the known-good images,
#            without pulling or building anything: tags them as latest, the tag
#            podman-compose.yml runs, and recreates the containers that don't run them
#            (podman-compose up -d, which also creates any other missing container of
#            the stack). MySQL and its data, Caddy and the other containers on the Pi
#            keep running. Deploy runs it when a deployment fails.
#
#   DEPLOY_DIR   checkout the stack runs from, with its podman-compose.yml and .env
#                (default: /opt/NISAR-SAR-Change-Detection, the one Deploy uses)
#
# known-good tags only exist on the Pi, they are never pushed. Containers are found by the
# labels podman-compose sets (project working dir and service), never by name.
#
# Exits 1 if the command fails, 2 on usage errors. Needs podman and podman-compose.
#
# Deploy runs it on the Raspberry Pi from stdin (ssh ... bash -s -- COMMAND): no command
# may read stdin, it would eat the rest of the script.
set -euo pipefail

SERVICES=(backend frontend)
declare -A REPOSITORY=(
  [backend]=ghcr.io/s4nxez/nisar-sar-change-detection-back
  [frontend]=ghcr.io/s4nxez/nisar-sar-change-detection-front
)
RUN_TAG=latest
GOOD_TAG=known-good

usage_error() { echo "rollback: $*" >&2; exit 2; }

# Every podman call reads /dev/null, not the script (see above)
podman() { command podman "$@" </dev/null; }

# annotate LEVEL MESSAGE: annotation on the run summary when run by Deploy (GITHUB_ACTIONS=true)
annotate() {
  if [[ "${GITHUB_ACTIONS:-}" == true ]]; then
    local message="${2//%/%25}"
    printf '::%s title=Rollback::%s\n' "$1" "${message//$'\n'/%0A}"
  fi
}

fail() {
  printf '[FAIL] %s\n' "$1"
  annotate error "$1"
  exit 1
}

# join SEPARATOR WORD...: the words separated by SEPARATOR
join() {
  local separator="$1" result="$2" word
  shift 2
  for word in "$@"; do result+="$separator$word"; done
  printf '%s' "$result"
}

# image_id REF: ID of the local image REF, nothing if there is none
image_id() {
  if podman image exists "$1"; then
    podman image inspect --format '{{.Id}}' "$1"
  fi
}

# describe IMAGE: "image <short ID>, built <date>[, commit <short SHA>]"
# (the commit is the org.opencontainers.image.revision label set by build.yml)
describe() {
  local out id created revision
  out="$(podman image inspect --format \
    '{{.Id}}|{{.Created.Format "2006-01-02 15:04 MST"}}|{{index .Labels "org.opencontainers.image.revision"}}' "$1")"
  IFS='|' read -r id created revision <<<"$out"
  printf 'image %s, built %s%s' "${id:0:12}" "$created" "${revision:+, commit ${revision:0:7}}"
}

# load_containers SERVICE: ROWS gets one "<container ID> <image ID> <state>" per container of SERVICE
load_containers() {
  local out
  out="$(podman ps -a --no-trunc \
    --filter "label=com.docker.compose.project.working_dir=$DEPLOY_DIR" \
    --filter "label=com.docker.compose.service=$1" \
    --format '{{.ID}} {{.ImageID}} {{.State}}')" || fail "podman ps failed (see the error above)"
  ROWS=()
  if [[ -n "$out" ]]; then mapfile -t ROWS <<<"$out"; fi
}

cmd_status() {
  local service row id image state good latest on_good missing=() differ=()
  echo "Deployment in $DEPLOY_DIR"
  for service in "${SERVICES[@]}"; do
    echo "$service"
    load_containers "$service"
    good="$(image_id "${REPOSITORY[$service]}:$GOOD_TAG")"
    latest="$(image_id "${REPOSITORY[$service]}:$RUN_TAG")"
    on_good=0
    if (( ${#ROWS[@]} == 0 )); then echo "  container   none"; fi
    for row in "${ROWS[@]}"; do
      read -r id image state <<<"$row"
      printf '  container   %s, %s\n' "$state" "$(describe "$image")"
      if (( ${#ROWS[@]} == 1 )) && [[ "$image" == "$good" && "$state" == running ]]; then on_good=1; fi
    done
    if (( ! on_good )); then differ+=("$service"); fi
    if [[ -n "$latest" ]]; then printf '  %-11s %s\n' "$RUN_TAG" "$(describe "$latest")"; else printf '  %-11s none\n' "$RUN_TAG"; fi
    if [[ -n "$good" ]]; then
      printf '  %-11s %s\n' "$GOOD_TAG" "$(describe "$good")"
    else
      printf '  %-11s none\n' "$GOOD_TAG"
      missing+=("$service")
    fi
  done
  echo
  if (( ${#missing[@]} )); then
    echo "No known-good image for ${missing[*]}: restore is not possible. Deploy marks them before replacing a version that passes the smoke test."
  elif (( ${#differ[@]} )); then
    echo "restore would switch ${differ[*]} to the known-good images."
  else
    echo "The backend and frontend containers run the known-good images."
  fi
}

cmd_mark() {
  local service id image state ref
  local -A running=()
  # Check both first: never leave known-good images from two different versions
  for service in "${SERVICES[@]}"; do
    load_containers "$service"
    (( ${#ROWS[@]} == 1 )) || fail "$service has ${#ROWS[@]} containers in $DEPLOY_DIR (expected 1): nothing was marked"
    read -r id image state <<<"${ROWS[0]}"
    [[ "$state" == running ]] || fail "$service is not running ($state): nothing was marked"
    running[$service]="$image"
  done
  for service in "${SERVICES[@]}"; do
    ref="${REPOSITORY[$service]}:$GOOD_TAG"
    if [[ "$(image_id "$ref")" == "${running[$service]}" ]]; then
      echo "$service: already known-good, $(describe "${running[$service]}")"
    else
      podman tag "${running[$service]}" "$ref" || fail "Could not tag the $service image as $ref (see the error above)"
      echo "$service: marked known-good, $(describe "${running[$service]}")"
    fi
  done
}

cmd_restore() {
  local service ref row id image state out rc=0 summary broken=()
  local -A good=()
  local recreate=() remove=()

  # Nothing changes until the known-good images and the compose file are known to be there
  for service in "${SERVICES[@]}"; do
    good[$service]="$(image_id "${REPOSITORY[$service]}:$GOOD_TAG")"
    [[ -n "${good[$service]}" ]] || fail "No known-good image for $service (${REPOSITORY[$service]}:$GOOD_TAG), nothing was changed. Deploy marks them before replacing a version that passes the smoke test; until then, roll back by reverting on main."
  done
  # Only prints service names, never the configuration (it holds the database password)
  out="$(cd "$DEPLOY_DIR" && podman-compose config --services </dev/null)" \
    || fail "podman-compose cannot read the compose file in $DEPLOY_DIR (see the error above), nothing was changed"
  for service in "${SERVICES[@]}"; do
    grep -qxF "$service" <<<"$out" || fail "podman-compose.yml in $DEPLOY_DIR has no $service service, nothing was changed"
  done

  echo "Rolling back $DEPLOY_DIR to the known-good images"
  for service in "${SERVICES[@]}"; do
    echo "  $service: $(describe "${good[$service]}")"
  done

  # podman-compose runs :latest and never pulls an image that exists locally: pointing :latest at
  # the known-good images makes it (and any later podman-compose up) run them
  for service in "${SERVICES[@]}"; do
    ref="${REPOSITORY[$service]}:$RUN_TAG"
    if [[ "$(image_id "$ref")" != "${good[$service]}" ]]; then
      podman tag "${good[$service]}" "$ref" || fail "Could not tag the known-good $service image as $ref (see the error above)"
      echo "$service: $ref now is the known-good image"
    fi
  done

  for service in "${SERVICES[@]}"; do
    load_containers "$service"
    if (( ${#ROWS[@]} == 1 )); then
      read -r id image state <<<"${ROWS[0]}"
      if [[ "$image" == "${good[$service]}" && "$state" == running ]]; then
        echo "$service: already runs the known-good image"
        continue
      fi
    fi
    recreate+=("$service")
    for row in "${ROWS[@]}"; do
      read -r id image state <<<"$row"
      echo "$service: removing container ${id:0:12} ($state, image ${image:0:12})"
      remove+=("$id")
    done
  done

  if (( ${#recreate[@]} == 0 )); then
    echo "Nothing to roll back: the backend and frontend containers run the known-good images."
    annotate warning "Nothing to roll back: the backend and frontend containers already run the known-good images (the deployment did not change them)"
    return 0
  fi

  # From here on a failure can leave containers missing: :latest already is the known-good
  # images, so podman-compose up -d recreates them as they should be
  local by_hand="podman-compose up -d in $DEPLOY_DIR recreates them with the known-good images (latest already points to them)"
  if (( ${#remove[@]} )); then
    podman rm --force "${remove[@]}" >/dev/null || fail "Could not remove the ${recreate[*]} containers (see the error above): $by_hand"
  fi
  # Creates the removed containers, and any other missing one (e.g. a deployment stopped half-way
  # removed them all), with the configuration Deploy uses. The existing ones (mysql, caddy) keep
  # running: podman-compose 1.3.0 gets "name already in use" for them and starts them, a no-op.
  # up -d exits 0 even if a container fails to start, so the containers are checked below.
  echo "Recreating ${recreate[*]} with podman-compose up -d"
  out="$(cd "$DEPLOY_DIR" && podman-compose up -d </dev/null 2>&1)" || rc=$?

  for service in "${recreate[@]}"; do
    load_containers "$service"
    if (( ${#ROWS[@]} != 1 )); then
      broken+=("$service has ${#ROWS[@]} containers (expected 1)")
      continue
    fi
    read -r id image state <<<"${ROWS[0]}"
    if [[ "$image" != "${good[$service]}" ]]; then
      broken+=("$service runs image ${image:0:12}, not the known-good ${good[$service]:0:12}")
    elif [[ "$state" != running ]]; then
      broken+=("$service is $state")
    else
      echo "[ OK ] $service runs the known-good image (container ${id:0:12})"
    fi
  done
  if (( ${#broken[@]} )); then
    echo "podman-compose up -d (exit code $rc):"
    while IFS= read -r row; do printf '  %s\n' "$row"; done <<<"${out:-(no output)}"
    fail "Rollback incomplete, $(join '; ' "${broken[@]}"): check the containers with podman-compose ps, $by_hand"
  fi

  summary=()
  for service in "${SERVICES[@]}"; do
    summary+=("$service $(describe "${good[$service]}")")
  done
  echo "Rolled back: the backend and frontend containers run the known-good images. Check the app with tools/ci/smoke-test.sh"
  annotate warning "Rolled back to the known-good images: $(join '; ' "${summary[@]}")"
}

(( $# == 1 )) || usage_error "usage: rollback.sh status|mark|restore"
DEPLOY_DIR="${DEPLOY_DIR:-/opt/NISAR-SAR-Change-Detection}"
[[ -f "$DEPLOY_DIR/podman-compose.yml" ]] || usage_error "DEPLOY_DIR=$DEPLOY_DIR has no podman-compose.yml"
# As podman-compose labels the containers: absolute path, symlinks resolved
DEPLOY_DIR="$(cd "$DEPLOY_DIR" && pwd -P)"

case "$1" in
  status) cmd_status ;;
  mark) cmd_mark ;;
  restore) cmd_restore ;;
  *) usage_error "unknown command '$1', usage: rollback.sh status|mark|restore" ;;
esac
