#!/usr/bin/env bash
# Tests of tools/ci/preview.sh against a fake podman command: no container runs.
#
# Usage: tools/ci/test-preview.sh
#
# The fake keeps the images, volumes and containers in a temporary directory, logs every change it is asked
# for and only accepts the calls preview.sh makes: any other call fails the test, so a change in how the script
# calls podman shows up here. A temporary checkout plays the develop stack's (DEPLOY_DIR), whose running Caddy
# routes PR previews.
# preview.sh runs from stdin as in PR preview (bash -s) and the fake reads its stdin: a command reading it before
# bash has read the whole script would eat the rest of it.
#
# Exits 1 if any check fails. Run by the validate job (build.yml).
#
# The tests given to check are single-quoted: it evaluates them once the command has run.
# shellcheck disable=SC2016
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT="$ROOT/tools/ci/preview.sh"
BACK=ghcr.io/s4nxez/nisar-sar-change-detection-back
FRONT=ghcr.io/s4nxez/nisar-sar-change-detection-front
PROJECT=nisar-sar-change-detection-develop
RECORD="${PROJECT}_monitor_data"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
DEVELOP="$TMP/develop"
mkdir -p "$TMP/bin" "$DEVELOP"
cp "$ROOT/podman-compose.yml" "$DEVELOP/"
DEVELOP="$(cd "$DEVELOP" && pwd -P)"

# --- Fake. State files: images (refs), volumes (names), containers (name), calls (changes made)
cat > "$TMP/bin/podman" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
cat >/dev/null
S="$FAKE_STATE"
ARGS="$*"
unsupported() { echo "fake podman: unsupported call: podman $ARGS" >&2; exit 99; }
networks='{{range $name, $_ := .NetworkSettings.Networks}}{{$name}}{{"\n"}}{{end}}'
project='{{index .Config.Labels "com.docker.compose.project"}}'
describe='{{.Id}}|{{.Created.Format "2006-01-02 15:04 MST"}}|{{index .Labels "org.opencontainers.image.revision"}}'
case "${1:-} ${2:-}" in
  "ps --no-trunc")
    [[ "$ARGS" == "ps --no-trunc --filter label=com.docker.compose.project.working_dir=$FAKE_DEVELOP --filter label=com.docker.compose.service=caddy --filter status=running --format {{.ID}}" ]] \
      || unsupported
    if [[ -z "${FAKE_NO_CADDY:-}" ]]; then echo caddy-dev; fi ;;
  "ps -a")
    [[ "$ARGS" == "ps -a"*"--filter label=nisar.preview.pr"* ]] || unsupported ;;
  "exec caddy-dev")
    [[ "$ARGS" == "exec caddy-dev printenv NISAR_PR_PREVIEWS" ]] || unsupported
    echo true ;;
  "inspect --format")
    case "$3 $4" in
      "$networks caddy-dev") echo nisar-dev-net ;;
      "$project caddy-dev") echo "${FAKE_PROJECT-nisar-sar-change-detection-develop}" ;;
      "{{.State.Health.Status}} nisar-pr-"*-mysql) echo healthy ;;
      *) unsupported ;;
    esac ;;
  "info --format")
    [[ "$3" == '{{.Store.GraphRoot}}' ]] || unsupported
    echo "$S" ;;
  "image exists")
    grep -qxF "$3" "$S/images" ;;
  "image inspect")
    [[ "$3" == --format ]] || unsupported
    grep -qxF "$5" "$S/images" || { echo "Error: $5: image not known" >&2; exit 125; }
    case "$4" in
      '{{.Id}}') echo "id-${5##*/}" ;;
      "$describe") echo "id-${5##*/}|2026-11-10 17:54 UTC|513d16c0000" ;;
      '{{len .RepoTags}}') echo 1 ;;
      *) unsupported ;;
    esac ;;
  "pull -q")
    echo "$3" >> "$S/images"
    echo "podman $ARGS" >> "$S/calls" ;;
  "volume exists")
    grep -qxF "$3" "$S/volumes" ;;
  "run -d")
    [[ "$3" == --name ]] || unsupported
    echo "$4" >> "$S/containers"
    echo "podman $ARGS" >> "$S/calls"
    echo "id-$4" ;;
  "healthcheck run") ;;
  *) unsupported ;;
esac
EOF
chmod +x "$TMP/bin/podman"

# --- State helpers
S="$TMP/state"

# fresh [VOLUME...]: no preview yet, the pr-15 images are in the registry and the volumes exist on the Pi
fresh() {
  rm -rf "$S" && mkdir -p "$S"
  : > "$S/images" && : > "$S/containers" && : > "$S/calls"
  printf '%s\n' "$@" > "$S/volumes"
}

# run COMMAND... [VAR=value...]: preview.sh from stdin, as PR preview runs it, on DEVELOP. Sets OUT and RC
run() {
  local args=() vars=()
  for arg in "$@"; do
    if [[ "$arg" == *=* ]]; then vars+=("$arg"); else args+=("$arg"); fi
  done
  RC=0
  OUT="$(env -u GITHUB_ACTIONS PATH="$TMP/bin:$PATH" FAKE_STATE="$S" FAKE_DEVELOP="$DEVELOP" DEPLOY_DIR="$DEVELOP" \
    MIN_FREE_MB=0 "${vars[@]}" bash -s -- "${args[@]}" < "$SCRIPT" 2>&1)" || RC=$?
}

# --- Checks
checks=0
failures=0
indent() { local line; while IFS= read -r line; do printf '         | %s\n' "$line"; done; }
check() {
  checks=$((checks + 1))
  if "${@:2}"; then
    printf '[ OK ] %s\n' "$1"
  else
    failures=$((failures + 1))
    printf '[FAIL] %s\n       preview.sh exit code: %s, output:\n' "$1" "$RC"
    indent <<<"$OUT"
    echo "       changes made:"
    indent < "$S/calls"
  fi
}
rc_is() { [[ "$RC" == "$1" ]]; }
says() { grep -qF -- "$1" <<<"$OUT"; }
# started NAME: the podman run line of container NAME (fails if it was not started)
started() { grep -m 1 "^podman run -d --name $1 " "$S/calls"; }
# run_has NAME TEXT: container NAME was started with TEXT among its arguments
run_has() { [[ "$(started "$1")" == *" $2 "* ]]; }
nothing_started() { [[ ! -s "$S/containers" ]]; }

echo "Testing tools/ci/preview.sh with a fake podman"

echo "--- river record"
fresh "${PROJECT}_mysql_data" "$RECORD"
run deploy 15
check "deploy with develop's record volume succeeds and starts mysql, backend and frontend" \
  eval 'rc_is 0 && started nisar-pr-15-mysql >/dev/null && started nisar-pr-15-backend >/dev/null && started nisar-pr-15-frontend >/dev/null'
check "deploy with develop's record volume mounts it read-only in the backend" \
  eval 'run_has nisar-pr-15-backend "-v $RECORD:/data/monitor:ro" && run_has nisar-pr-15-backend "-e MONITOR_DATA_DIR=/data/monitor"'
check "deploy with develop's record volume says which record the preview serves" \
  says "river record: $RECORD (the develop stack's), read-only"
check "deploy mounts the record only in the backend, not in mysql or the frontend" \
  eval '[[ "$(started nisar-pr-15-mysql)" != *monitor* && "$(started nisar-pr-15-frontend)" != *monitor* ]]'
check "deploy runs the backend image of the pull request, after the record" \
  eval '[[ "$(started nisar-pr-15-backend)" == *"/data/monitor:ro $BACK:pr-15" ]] && run_has nisar-pr-15-frontend "--restart always --label nisar.preview.pr=15"'

fresh
run deploy 15
check "deploy without develop's record volume still starts the preview" \
  eval 'rc_is 0 && started nisar-pr-15-backend >/dev/null && started nisar-pr-15-frontend >/dev/null'
check "deploy without develop's record volume gives the backend no record (it creates no volume)" \
  eval '[[ "$(started nisar-pr-15-backend)" != *monitor* && "$(started nisar-pr-15-backend)" == *" $BACK:pr-15" ]]'
check "deploy without develop's record volume says the monitor page has no record" \
  says "river record: none, the develop stack has no $RECORD volume yet"

fresh "nisar-sar-change-detection_monitor_data"
run deploy 15
check "deploy never mounts production's record volume" \
  eval 'rc_is 0 && [[ "$(started nisar-pr-15-backend)" != *monitor* ]]'

fresh "other-stack_monitor_data"
run deploy 15 FAKE_PROJECT=other-stack
check "the record volume follows the develop stack's podman-compose project" \
  eval 'rc_is 0 && run_has nisar-pr-15-backend "-v other-stack_monitor_data:/data/monitor:ro"'

fresh "$RECORD"
run deploy 15 FAKE_PROJECT=
check "deploy fails and starts nothing when the develop stack's Caddy has no podman-compose project" \
  eval 'rc_is 1 && says "Could not find the podman-compose project of the develop stack" && nothing_started'

echo "--- develop stack"
fresh "$RECORD"
run deploy 15 FAKE_NO_CADDY=1
check "deploy fails and starts nothing without the develop stack's Caddy" \
  eval 'rc_is 1 && says "has no running caddy container" && nothing_started'

echo
if (( failures > 0 )); then
  echo "preview.sh tests FAILED: $failures of $checks checks failed"
  exit 1
fi
echo "preview.sh tests passed: $checks checks"
