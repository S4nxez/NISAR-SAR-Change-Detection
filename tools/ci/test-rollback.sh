#!/usr/bin/env bash
# Tests of tools/ci/rollback.sh against fake podman and podman-compose commands: no container runs.
#
# Usage: tools/ci/test-rollback.sh
#
# The fakes keep a small image store and container list in a temporary directory and only accept
# the calls rollback.sh makes, with the output of podman 5 and podman-compose 1.3.0 (the versions
# on the Raspberry Pi): any other call fails the test, so a change in how the script calls podman
# shows up here. The fake podman-compose reads the images of the services from the repository's
# podman-compose.yml, as the real one would, resolving ${VAR:-default} as podman-compose 1.3.0 does
# (the environment, then the .env of the checkout, then the default).
# Two checkouts run a stack: DEPLOY plays production's (latest, known-good) and DEVELOP the develop
# stack's (NISAR_IMAGE_TAG=develop, develop-known-good).
# rollback.sh runs from stdin as in Deploy (bash -s) and the fakes read their stdin: a command
# reading it before bash has read the whole script would eat the rest of it.
#
# Exits 1 if any check fails. Run by the validate job (build.yml).
#
# The tests given to check are single-quoted: it evaluates them once the command has run.
# shellcheck disable=SC2016
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT="$ROOT/tools/ci/rollback.sh"
BACK=ghcr.io/s4nxez/nisar-sar-change-detection-back
FRONT=ghcr.io/s4nxez/nisar-sar-change-detection-front

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
DEPLOY="$TMP/deploy"
DEVELOP="$TMP/develop"
mkdir -p "$TMP/bin" "$DEPLOY" "$DEVELOP"
cp "$ROOT/podman-compose.yml" "$DEPLOY/"
cp "$ROOT/podman-compose.yml" "$DEVELOP/"
DEPLOY="$(cd "$DEPLOY" && pwd -P)"
DEVELOP="$(cd "$DEVELOP" && pwd -P)"

# --- Fakes. State files: images (id|created|revision), tags (ref id),
# containers (id|service|image id|state|project working dir), calls (changes made)
cat > "$TMP/bin/podman" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
cat >/dev/null
S="$FAKE_STATE"
unsupported() { echo "fake podman: unsupported call: podman $ARGS" >&2; exit 99; }
ARGS="$*"
# resolve REF: ID of the image REF (an image ID or a tag)
resolve() {
  awk -F'|' -v r="$1" '$1 == r { print $1; found = 1; exit } END { exit !found }' "$S/images" \
    || awk -v r="$1" '$1 == r { print $2; found = 1; exit } END { exit !found }' "$S/tags"
}
describe='{{.Id}}|{{.Created.Format "2006-01-02 15:04 MST"}}|{{index .Labels "org.opencontainers.image.revision"}}'
case "${1:-} ${2:-}" in
  "image exists")
    (( $# == 3 )) || unsupported
    resolve "$3" >/dev/null ;;
  "image inspect")
    (( $# == 5 )) && [[ "$3" == --format ]] || unsupported
    id="$(resolve "$5")" || { echo "Error: $5: image not known" >&2; exit 125; }
    case "$4" in
      '{{.Id}}') echo "$id" ;;
      "$describe") awk -F'|' -v i="$id" '$1 == i' "$S/images" ;;
      *) unsupported ;;
    esac ;;
  tag\ *)
    (( $# == 3 )) || unsupported
    id="$(resolve "$2")" || { echo "Error: $2: image not known" >&2; exit 125; }
    awk -v r="$3" '$1 != r' "$S/tags" > "$S/tags.new" && mv "$S/tags.new" "$S/tags"
    echo "$3 $id" >> "$S/tags"
    echo "podman $ARGS" >> "$S/calls" ;;
  "ps -a")
    (( $# == 9 )) && [[ "$3" == --no-trunc && "$4" == --filter && "$6" == --filter && "$8" == --format \
      && "$5" == label=com.docker.compose.project.working_dir=* && "$7" == label=com.docker.compose.service=* \
      && "$9" == '{{.ID}} {{.ImageID}} {{.State}}' ]] || unsupported
    awk -F'|' -v d="${5#*working_dir=}" -v s="${7#*service=}" '$5 == d && $2 == s { print $1, $3, $4 }' "$S/containers" ;;
  "rm --force")
    (( $# > 2 )) || unsupported
    for id in "${@:3}"; do
      awk -F'|' -v c="$id" '$1 == c { found = 1 } END { exit !found }' "$S/containers" \
        || { echo "Error: no container with name or ID \"$id\" found: no such container" >&2; exit 1; }
      awk -F'|' -v c="$id" '$1 != c' "$S/containers" > "$S/containers.new" && mv "$S/containers.new" "$S/containers"
      echo "$id"
    done
    echo "podman $ARGS" >> "$S/calls" ;;
  *) unsupported ;;
esac
EOF

cat > "$TMP/bin/podman-compose" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
cat >/dev/null
S="$FAKE_STATE"
[[ -f podman-compose.yml ]] || { echo "no compose.yaml, docker-compose.yml or container-compose.yml file found, pass files with -f" >&2; exit 255; }
dir="$(pwd -P)"
echo "podman-compose $* (in $dir)" >> "$S/calls"
services() { awk '/^services:/ { s = 1; next } /^[^ #]/ { s = 0 } s && /^  [a-z]+:/ { sub(/:.*/, ""); print $1 }' podman-compose.yml; }
# image SERVICE: the image of SERVICE in podman-compose.yml, ${VAR:-default} resolved as podman-compose
# does (the environment, then .env, then the default) and short names as podman does
image() {
  local ref name value
  ref="$(awk -v s="  $1:" '/^  [^ ]/ { in_s = ($0 == s) } in_s && /^    image:/ { print $2; exit }' podman-compose.yml)"
  while [[ "$ref" =~ \$\{([A-Za-z_][A-Za-z0-9_]*):-([^}]*)\} ]]; do
    name="${BASH_REMATCH[1]}"
    value="${!name:-}"
    if [[ -z "$value" && -f .env ]]; then value="$(sed -n "s/^$name=//p" .env | tail -n 1)"; fi
    ref="${ref/"${BASH_REMATCH[0]}"/${value:-${BASH_REMATCH[2]}}}"
  done
  if [[ "$ref" != */* ]]; then ref="docker.io/library/$ref"; fi
  echo "$ref"
}
case "$*" in
  "config --services")
    if [[ -n "${FAKE_COMPOSE_CONFIG_ERROR:-}" ]]; then echo "yaml.parser.ParserError: $FAKE_COMPOSE_CONFIG_ERROR" >&2; exit 1; fi
    services ;;
  "up -d")
    for service in $(services); do
      if awk -F'|' -v d="$dir" -v s="$service" '$5 == d && $2 == s { found = 1 } END { exit !found }' "$S/containers"; then
        # podman run fails on the existing container, then podman start starts it, with its own image
        echo "Error: creating container storage: the container name \"${service}_1\" is already in use"
        awk -F'|' -v OFS='|' -v d="$dir" -v s="$service" '$5 == d && $2 == s { $4 = "running" } 1' "$S/containers" > "$S/c.new" && mv "$S/c.new" "$S/containers"
        continue
      fi
      if [[ "${FAKE_RUN_FAILS:-}" == "$service" ]]; then echo "Error: simulated podman run failure for $service"; continue; fi
      ref="$(image "$service")"
      # podman run pulls an image missing locally: here that's the registry's :latest, a failed rollback
      id="$(awk -v r="$ref" '$1 == r { print $2 }' "$S/tags")"
      state=running
      if [[ "${FAKE_CRASHES:-}" == "$service" ]]; then state=exited; fi
      echo "new-$service|$service|${id:-pulled-$ref}|$state|$dir" >> "$S/containers"
      echo "new-$service"
    done ;;
  *) echo "fake podman-compose: unsupported call: podman-compose $*" >&2; exit 99 ;;
esac
EOF
chmod +x "$TMP/bin/podman" "$TMP/bin/podman-compose"

# --- State helpers
S="$TMP/state"

# deployment VERSION: fresh state. The backend and frontend containers run the images of VERSION
# (old: the version before the deployment, new: the deployed one), :latest points to them and the
# old ones are known-good if KNOWN_GOOD=1. mysql, caddy and another project's containers run too.
deployment() {
  local version="$1"
  rm -rf "$S" && mkdir -p "$S"
  printf '%s\n' "back-old|2026-10-26 18:30 UTC|1111111aaaa" "front-old|2026-10-26 18:30 UTC|1111111aaaa" \
    "back-new|2026-10-27 19:01 UTC|2222222bbbb" "front-new|2026-10-27 19:01 UTC|" \
    "mysql-8|2026-06-01 10:00 UTC|" "caddy-2|2026-06-03 17:53 UTC|" "other-app|2026-05-01 09:00 UTC|" > "$S/images"
  printf '%s\n' "$BACK:latest back-$version" "$FRONT:latest front-$version" \
    "docker.io/library/mysql:8 mysql-8" "docker.io/library/caddy:latest caddy-2" > "$S/tags"
  if [[ "${KNOWN_GOOD:-1}" == 1 ]]; then printf '%s\n' "$BACK:known-good back-old" "$FRONT:known-good front-old" >> "$S/tags"; fi
  printf '%s\n' "c-mysql|mysql|mysql-8|running|$DEPLOY" "c-caddy|caddy|caddy-2|running|$DEPLOY" \
    "c-back|backend|back-$version|running|$DEPLOY" "c-front|frontend|front-$version|running|$DEPLOY" \
    "o-back|backend|other-app|running|/srv/other" "o-front|frontend|other-app|exited|/srv/other" > "$S/containers"
  : > "$S/calls"
  cp "$S/containers" "$S/containers.before"
  cp "$S/tags" "$S/tags.before"
}

# add_develop VERSION: adds the develop stack to the state, in DEVELOP. Its backend and frontend containers run the
# develop images of VERSION, :develop points to them and the old ones are develop-known-good if KNOWN_GOOD=1. Its own
# mysql and caddy containers run too.
add_develop() {
  local version="$1"
  printf '%s\n' "devback-old|2026-10-28 10:00 UTC|3333333cccc" "devfront-old|2026-10-28 10:00 UTC|3333333cccc" \
    "devback-new|2026-10-29 07:00 UTC|4444444dddd" "devfront-new|2026-10-29 07:00 UTC|4444444dddd" >> "$S/images"
  printf '%s\n' "$BACK:develop devback-$version" "$FRONT:develop devfront-$version" >> "$S/tags"
  if [[ "${KNOWN_GOOD:-1}" == 1 ]]; then
    printf '%s\n' "$BACK:develop-known-good devback-old" "$FRONT:develop-known-good devfront-old" >> "$S/tags"
  fi
  printf '%s\n' "d-mysql|mysql|mysql-8|running|$DEVELOP" "d-caddy|caddy|caddy-2|running|$DEVELOP" \
    "d-back|backend|devback-$version|running|$DEVELOP" "d-front|frontend|devfront-$version|running|$DEVELOP" >> "$S/containers"
  cp "$S/containers" "$S/containers.before"
  cp "$S/tags" "$S/tags.before"
}

set_container() { # set_container ID IMAGE STATE: changes a container, "" IMAGE removes it
  awk -F'|' -v OFS='|' -v c="$1" -v i="$2" -v s="$3" '$1 == c { if (i == "") next; $3 = i; $4 = s } 1' "$S/containers" > "$S/c.new"
  mv "$S/c.new" "$S/containers" && cp "$S/containers" "$S/containers.before"
}
set_tag() { # set_tag REF IMAGE: points REF to IMAGE, "" IMAGE removes it
  awk -v r="$1" '$1 != r' "$S/tags" > "$S/t.new"
  if [[ -n "$2" ]]; then echo "$1 $2" >> "$S/t.new"; fi
  mv "$S/t.new" "$S/tags" && cp "$S/tags" "$S/tags.before"
}

# run COMMAND [VAR=value...]: rollback.sh COMMAND ("" for none) from stdin, as Deploy runs it, on
# DEPLOY as production's checkout unless the variables say otherwise. Sets OUT and RC
run() {
  local command=()
  if [[ -n "$1" ]]; then command=("$1"); fi
  shift
  RC=0
  OUT="$(env -u GITHUB_ACTIONS -u NISAR_IMAGE_TAG -u NISAR_HTTP_PORT PATH="$TMP/bin:$PATH" FAKE_STATE="$S" \
    PRODUCTION_DIR="$DEPLOY" DEPLOY_DIR="$DEPLOY" "$@" bash -s -- "${command[@]}" < "$SCRIPT" 2>&1)" || RC=$?
}

# --- Checks
checks=0
failures=0
# Prefixed with "| ": GitHub Actions takes lines starting with ::error, after any leading spaces, as annotations
indent() { local line; while IFS= read -r line; do printf '         | %s\n' "$line"; done; }
# check DESCRIPTION TEST...: TEST is a command (with arguments) that must succeed
check() {
  checks=$((checks + 1))
  if "${@:2}"; then
    printf '[ OK ] %s\n' "$1"
  else
    failures=$((failures + 1))
    printf '[FAIL] %s\n       rollback.sh exit code: %s, output:\n' "$1" "$RC"
    indent <<<"$OUT"
    echo "       changes made:"
    indent < "$S/calls"
  fi
}
rc_is() { [[ "$RC" == "$1" ]]; }
says() { grep -qF -- "$1" <<<"$OUT"; }
tag_is() { [[ "$(awk -v r="$1" '$1 == r { print $2 }' "$S/tags")" == "$2" ]]; }
no_tag() { ! awk -v r="$1" '$1 == r { found = 1 } END { exit !found }' "$S/tags"; }
called() { grep -qxF -- "$1" "$S/calls"; }
nothing_changed() { [[ ! -s "$S/calls" ]] && cmp -s "$S/tags" "$S/tags.before" && cmp -s "$S/containers" "$S/containers.before"; }
# runs SERVICE IMAGE [DIR]: SERVICE has exactly one container in the checkout DIR (default: DEPLOY), running IMAGE
runs() { [[ "$(awk -F'|' -v d="${3:-$DEPLOY}" -v s="$1" '$5 == d && $2 == s { print $3, $4 }' "$S/containers")" == "$2 running" ]]; }
# tags_untouched REF...: the tags point where they did before the command (or still don't exist)
tags_untouched() {
  local ref
  for ref in "$@"; do
    [[ "$(awk -v r="$ref" '$1 == r' "$S/tags")" == "$(awk -v r="$ref" '$1 == r' "$S/tags.before")" ]] || return 1
  done
}
# untouched ID...: the containers are as they were before the command
untouched() {
  local id
  for id in "$@"; do
    [[ "$(grep "^$id|" "$S/containers")" == "$(grep "^$id|" "$S/containers.before")" ]] || return 1
  done
}

echo "Testing tools/ci/rollback.sh with fake podman and podman-compose"

echo "--- status"
KNOWN_GOOD=0 deployment old
run status
check "status without known-good images says restore is not possible" \
  eval 'rc_is 0 && says "known-good  none" && says "restore is not possible" && nothing_changed'
deployment new
run status
check "status after a deployment shows the images and what restore would switch" \
  eval 'rc_is 0 && says "container   running, image back-new, built 2026-10-27 19:01 UTC, commit 2222222" &&
    says "known-good  image front-old, built 2026-10-26 18:30 UTC, commit 1111111" &&
    says "restore would switch backend frontend to the known-good images" && nothing_changed'
ln -s "$DEPLOY" "$TMP/deploy-link"
run status DEPLOY_DIR="$TMP/deploy-link"
check "status finds the containers through a symlinked DEPLOY_DIR (labels hold the real path)" \
  eval 'rc_is 0 && says "Deployment in $DEPLOY" && says "container   running, image back-new"'

echo "--- mark"
KNOWN_GOOD=0 deployment old
run mark
check "mark tags the running images as known-good" \
  eval 'rc_is 0 && tag_is "$BACK:known-good" back-old && tag_is "$FRONT:known-good" front-old && says "backend: marked known-good, image back-old"'
run mark
check "mark again leaves them as they are" \
  eval 'rc_is 0 && says "backend: already known-good" && says "frontend: already known-good" && [[ "$(wc -l < "$S/calls")" == 2 ]]'
deployment new
run mark
check "mark replaces the former known-good images" \
  eval 'rc_is 0 && tag_is "$BACK:known-good" back-new && tag_is "$FRONT:known-good" front-new && tag_is "$BACK:latest" back-new'
KNOWN_GOOD=0 deployment old
set_tag "$BACK:latest" back-new
run mark
check "mark tags the images the containers run, not the ones :latest points to" \
  eval 'rc_is 0 && tag_is "$BACK:known-good" back-old && tag_is "$FRONT:known-good" front-old'
KNOWN_GOOD=0 deployment old
set_container c-back back-old exited
run mark
check "mark refuses a backend that is not running, and marks nothing" \
  eval 'rc_is 1 && says "[FAIL] backend is not running (exited): nothing was marked" && nothing_changed'
KNOWN_GOOD=0 deployment old
set_container c-front "" ""
run mark
check "mark refuses a missing frontend container, and marks nothing" \
  eval 'rc_is 1 && says "[FAIL] frontend has 0 containers" && nothing_changed && no_tag "$BACK:known-good"'

echo "--- restore"
deployment new
run restore
check "restore after a failed deployment: latest points to the known-good images" \
  eval 'rc_is 0 && tag_is "$BACK:latest" back-old && tag_is "$FRONT:latest" front-old'
check "restore after a failed deployment: only backend and frontend are removed and recreated, in DEPLOY_DIR" \
  eval 'called "podman rm --force c-back c-front" && called "podman-compose up -d (in $DEPLOY)"'
check "restore after a failed deployment: backend and frontend run the known-good images" \
  eval 'runs backend back-old && runs frontend front-old && says "Rolled back: the backend and frontend containers run the known-good images"'
check "restore after a failed deployment: mysql, caddy and the other project's containers are untouched" \
  untouched c-mysql c-caddy o-back o-front
check "restore keeps the known-good tags and never pulls" \
  eval 'tag_is "$BACK:known-good" back-old && tag_is "$FRONT:known-good" front-old && ! grep -q pulled "$S/containers"'
deployment new
run restore GITHUB_ACTIONS=true
check "restore in Deploy annotates the rollback on the run summary" \
  eval 'rc_is 0 && says "::warning title=Rollback::Rolled back to the known-good images: backend image back-old, built 2026-10-26 18:30 UTC, commit 1111111; frontend image front-old"'

deployment old
set_container c-back back-new running
run restore
check "restore recreates only the containers that don't run the known-good images" \
  eval 'rc_is 0 && called "podman rm --force c-back" && called "podman-compose up -d (in $DEPLOY)" &&
    runs backend back-old && untouched c-front c-mysql c-caddy'
deployment old
set_container c-back back-old exited
run restore
check "restore recreates a stopped backend container" \
  eval 'rc_is 0 && called "podman rm --force c-back" && runs backend back-old && untouched c-front'
deployment new
set_container c-back "" ""
run restore
check "restore recreates a missing backend container" \
  eval 'rc_is 0 && called "podman rm --force c-front" && called "podman-compose up -d (in $DEPLOY)" &&
    runs backend back-old && runs frontend front-old'
deployment new
for id in c-mysql c-caddy c-back c-front; do set_container "$id" "" ""; done
run restore
check "restore after a deployment stopped half-way (no container left) brings the whole stack back" \
  eval 'rc_is 0 && ! grep -q "^podman rm" "$S/calls" && runs backend back-old && runs frontend front-old &&
    runs mysql mysql-8 && runs caddy caddy-2 && untouched o-back o-front'

deployment old
set_tag "$BACK:latest" back-new
set_tag "$FRONT:latest" front-new
run restore GITHUB_ACTIONS=true
check "restore when the deployment pulled but did not recreate: retags latest and recreates nothing" \
  eval 'rc_is 0 && tag_is "$BACK:latest" back-old && tag_is "$FRONT:latest" front-old &&
    ! grep -q "^podman rm\|^podman-compose up" "$S/calls" && untouched c-back c-front &&
    says "::warning title=Rollback::Nothing to roll back"'

KNOWN_GOOD=0 deployment new
run restore GITHUB_ACTIONS=true
check "restore without known-good images fails and changes nothing" \
  eval 'rc_is 1 && says "[FAIL] No known-good image for backend" && says "::error title=Rollback::No known-good image for backend" && nothing_changed'
deployment new
set_tag "$FRONT:known-good" ""
run restore
check "restore without a known-good frontend image fails and changes nothing" \
  eval 'rc_is 1 && says "[FAIL] No known-good image for frontend" && nothing_changed'
deployment new
cp "$DEPLOY/podman-compose.yml" "$TMP/compose.orig"
sed -i "s|image: $BACK:.*|image: $BACK:pinned|" "$DEPLOY/podman-compose.yml"
run restore
mv "$TMP/compose.orig" "$DEPLOY/podman-compose.yml"
check "restore fails when the recreated backend does not run the known-good image (podman-compose.yml not on the stack's tag)" \
  eval 'rc_is 1 && says "[FAIL] Rollback incomplete, backend runs image pulled-ghcr., not the known-good back-old"'
deployment new
printf 'NISAR_IMAGE_TAG=pinned\n' > "$DEPLOY/.env"
run restore
rm "$DEPLOY/.env"
check "restore makes podman-compose run the tag it restores, whatever the .env of the checkout says" \
  eval 'rc_is 0 && runs backend back-old && runs frontend front-old'
deployment new
run restore FAKE_COMPOSE_CONFIG_ERROR="while parsing a block mapping"
check "restore fails and changes nothing when podman-compose cannot read the compose file" \
  eval 'rc_is 1 && says "[FAIL] podman-compose cannot read the compose file" && says "ParserError" &&
    [[ "$(cat "$S/calls")" == "podman-compose config --services (in $DEPLOY)" ]] && cmp -s "$S/tags" "$S/tags.before" && untouched c-back c-front'
deployment new
run restore FAKE_CRASHES=backend
check "restore fails when the recreated backend does not stay up, with the podman-compose output" \
  eval 'rc_is 1 && says "[FAIL] Rollback incomplete, backend is exited" && says "podman-compose up -d (exit code 0):" &&
    says "  Error: creating container storage: the container name \"mysql_1\" is already in use" && runs frontend front-old'
deployment new
run restore FAKE_RUN_FAILS=frontend
check "restore fails when podman-compose does not create the frontend container" \
  eval 'rc_is 1 && says "frontend has 0 containers (expected 1)" && says "podman-compose up -d in $DEPLOY recreates them"'

echo "--- develop stack (DEPLOY_DIR=DEVELOP NISAR_IMAGE_TAG=develop), next to production's"
# shellcheck disable=SC2034 # used by the tests given to check
PRODUCTION_TAGS=("$BACK:latest" "$FRONT:latest" "$BACK:known-good" "$FRONT:known-good")
DEV=(DEPLOY_DIR="$DEVELOP" NISAR_IMAGE_TAG=develop)
deployment old
add_develop new
run status "${DEV[@]}"
check "status of the develop stack shows its containers and its develop and develop-known-good images" \
  eval 'rc_is 0 && says "Deployment in $DEVELOP" &&
    says "  container          running, image devback-new, built 2026-10-29 07:00 UTC, commit 4444444" &&
    says "  develop            image devfront-new" && says "  develop-known-good image devback-old" &&
    says "restore would switch backend frontend to the known-good images" && nothing_changed'
run mark "${DEV[@]}"
check "mark on the develop stack tags the images its containers run as develop-known-good, never production's tags" \
  eval 'rc_is 0 && tag_is "$BACK:develop-known-good" devback-new && tag_is "$FRONT:develop-known-good" devfront-new &&
    says "backend: marked develop-known-good, image devback-new" && tags_untouched "${PRODUCTION_TAGS[@]}"'

deployment new
add_develop new
run restore "${DEV[@]}" GITHUB_ACTIONS=true
check "restore of the develop stack: develop points to the develop-known-good images, production's tags are untouched" \
  eval 'rc_is 0 && tag_is "$BACK:develop" devback-old && tag_is "$FRONT:develop" devfront-old &&
    tag_is "$BACK:develop-known-good" devback-old && tags_untouched "${PRODUCTION_TAGS[@]}"'
check "restore of the develop stack: only its backend and frontend are removed and recreated, in its checkout" \
  eval 'called "podman rm --force d-back d-front" && called "podman-compose up -d (in $DEVELOP)" &&
    runs backend devback-old "$DEVELOP" && runs frontend devfront-old "$DEVELOP"'
check "restore of the develop stack: production's containers, the develop mysql and caddy and the other project's are untouched" \
  untouched c-mysql c-caddy c-back c-front d-mysql d-caddy o-back o-front
check "restore of the develop stack annotates the rollback on the run summary" \
  eval 'says "::warning title=Rollback::Rolled back to the known-good images: backend image devback-old, built 2026-10-28 10:00 UTC, commit 3333333"'
deployment new
add_develop new
run restore "${DEV[@]}" FAKE_RUN_FAILS=backend
check "restore of the develop stack that fails tells how to finish it by hand, with the develop tag" \
  eval 'rc_is 1 && says "NISAR_IMAGE_TAG=develop podman-compose up -d in $DEVELOP recreates them" && runs backend back-new'
KNOWN_GOOD=0 deployment new
KNOWN_GOOD=0 add_develop new
run restore "${DEV[@]}"
check "restore of the develop stack without develop-known-good images fails and changes nothing" \
  eval 'rc_is 1 && says "[FAIL] No known-good image for backend ($BACK:develop-known-good)" && nothing_changed'

# develop_deployment: fresh state, both stacks after a failed deployment
develop_deployment() { deployment new && add_develop new; }
develop_deployment
run restore DEPLOY_DIR="$DEVELOP"
check "another checkout than production's without NISAR_IMAGE_TAG is a usage error and changes nothing (latest is production's)" \
  eval 'rc_is 2 && says "is not production" && says "set NISAR_IMAGE_TAG" && nothing_changed'
develop_deployment
run mark NISAR_IMAGE_TAG=develop
check "production's checkout with another stack's NISAR_IMAGE_TAG is a usage error and changes nothing" \
  eval 'rc_is 2 && says "checkout, which runs latest: NISAR_IMAGE_TAG=develop is another stack" && nothing_changed'
develop_deployment
run mark DEPLOY_DIR="$DEVELOP" NISAR_IMAGE_TAG=develop-known-good
check "a known-good NISAR_IMAGE_TAG is a usage error and changes nothing" \
  eval 'rc_is 2 && says "is a known-good tag" && nothing_changed'
develop_deployment
run restore DEPLOY_DIR="$DEVELOP" NISAR_IMAGE_TAG="dev elop"
check "a NISAR_IMAGE_TAG that is not an image tag is a usage error and changes nothing" \
  eval 'rc_is 2 && says "must be an image tag" && nothing_changed'

echo "--- usage"
deployment new
run ""
check "no command is a usage error" eval 'rc_is 2 && says "usage: rollback.sh status|mark|restore" && nothing_changed'
run rollback
check "an unknown command is a usage error" eval 'rc_is 2 && says "unknown command '"'"'rollback'"'"'" && nothing_changed'
run status DEPLOY_DIR="$TMP"
check "a DEPLOY_DIR without podman-compose.yml is a usage error" eval 'rc_is 2 && says "has no podman-compose.yml" && nothing_changed'

echo
if (( failures > 0 )); then
  echo "rollback.sh tests FAILED: $failures of $checks checks failed"
  exit 1
fi
echo "rollback.sh tests passed: $checks checks"
