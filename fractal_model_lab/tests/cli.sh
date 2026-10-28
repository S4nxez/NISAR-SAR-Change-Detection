#!/usr/bin/env bash
# Tests of the command line mode of fractal_lab: with arguments it generates the
# schema without the TUI (no terminal needed) and prints the 'gen' and 'stats'
# report (--text, the default) or the whole schema as JSON (--json).
#
# Usage: tests/cli.sh [FRACTAL_LAB]
#   FRACTAL_LAB  binary to test (default: ./fractal_lab). 'make test' builds it
#                and passes its path.
#
# Checks:
#   - the text and JSON output of the default schema, exactly
#   - field options: names, aliases, --name=value, profile fields, last value wins
#   - edge cases: single level, saturated counts, schemas that need a cluster
#   - --help lists every field of the JSON output
#   - invalid arguments: exit 2, a message on stderr and nothing on stdout
#   - write errors: exit 1
# The syntax of the JSON outputs is checked with jq or python3 when available.
#
# Exits 1 if any check fails, 2 on usage errors. Run by the validate job
# (.github/workflows/build.yml).
set -euo pipefail

BIN="${1:-./fractal_lab}"
if [[ ! -x "$BIN" ]]; then
  echo "cli-test: '$BIN' is not an executable file, build it first (make)" >&2
  exit 2
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

checks=0
failures=0

pass() {
  checks=$((checks + 1))
  printf '[ OK ] %s\n' "$1"
}

# fail SUMMARY [DETAIL...] (empty details are skipped, multi-line ones indented)
fail() {
  local summary="$1" detail
  shift
  checks=$((checks + 1))
  failures=$((failures + 1))
  printf '[FAIL] %s\n' "$summary"
  for detail in "$@"; do
    if [[ -n "$detail" ]]; then printf '%s\n' "$detail" | sed 's/^/       /'; fi
  done
  if [[ "${GITHUB_ACTIONS:-}" == true ]]; then
    # Annotation shown on the run summary; % and newlines must be escaped
    summary="${summary//%/%25}"
    printf '::error title=Model lab CLI test::%s\n' "${summary//$'\n'/%0A}"
  fi
}

# run ARGS...: runs fractal_lab without a terminal (no TERM, stdin from /dev/null);
# stdout in $TMP/out, stderr in $TMP/err, exit code in RC
run() {
  ARGS="$*"
  RC=0
  env -u TERM "$BIN" "$@" </dev/null >"$TMP/out" 2>"$TMP/err" || RC=$?
}

# The last run, for failure details
last_run() {
  printf 'command: fractal_lab %s\nexit code: %s\nstdout: %s\nstderr: %s\n' "$ARGS" "$RC" \
    "$(head -c 400 "$TMP/out")" "$(head -c 400 "$TMP/err")"
}

# succeeded: the last run exited 0 without writing to stderr
succeeded() { [[ "$RC" -eq 0 && ! -s "$TMP/err" ]]; }

if command -v jq >/dev/null; then
  JSON_PARSER=(jq -e .)
elif command -v python3 >/dev/null; then
  JSON_PARSER=(python3 -c 'import json, sys; json.load(sys.stdin)')
else
  JSON_PARSER=()
  echo "[SKIP] JSON syntax checks: neither jq nor python3 is installed"
fi

# json_valid: the stdout of the last run parses as JSON (true without a parser)
json_valid() {
  if (( ${#JSON_PARSER[@]} == 0 )); then return 0; fi
  "${JSON_PARSER[@]}" <"$TMP/out" >/dev/null 2>"$TMP/json_err"
}

# expect_output DESCRIPTION ARGS... <EXPECTED: succeeds and prints exactly EXPECTED
expect_output() {
  local description="$1"
  shift
  cat >"$TMP/expected"
  run "$@"
  if ! succeeded; then
    fail "$description: fractal_lab $ARGS failed" "$(last_run)"
  elif ! diff -u "$TMP/expected" "$TMP/out" >"$TMP/diff"; then
    fail "$description: fractal_lab $ARGS printed an unexpected output" "$(cat "$TMP/diff")"
  elif [[ "$(head -c 1 "$TMP/out")" == "{" ]] && ! json_valid; then
    fail "$description: fractal_lab $ARGS printed invalid JSON" "$(cat "$TMP/json_err")"
  else
    pass "$description"
  fi
}

# expect_contains DESCRIPTION TEXT...: the last run succeeded and its stdout contains
# every TEXT (one line each), and is valid JSON if it is JSON
expect_contains() {
  local description="$1" text missing=()
  shift
  for text in "$@"; do
    grep -qF -- "$text" "$TMP/out" || missing+=("missing: $text")
  done
  if ! succeeded; then
    fail "$description: fractal_lab $ARGS failed" "$(last_run)"
  elif (( ${#missing[@]} )); then
    fail "$description: unexpected output of fractal_lab $ARGS" "${missing[@]}" \
      "stdout: $(head -c 2000 "$TMP/out")"
  elif [[ "$(head -c 1 "$TMP/out")" == "{" ]] && ! json_valid; then
    fail "$description: fractal_lab $ARGS printed invalid JSON" "$(cat "$TMP/json_err")"
  else
    pass "$description"
  fi
}

# expect_usage_error MESSAGE ARGS...: exits 2, MESSAGE on stderr and nothing on stdout
expect_usage_error() {
  local message="$1"
  shift
  run "$@"
  if [[ "$RC" -eq 2 && ! -s "$TMP/out" ]] && grep -qF -- "$message" "$TMP/err"; then
    pass "rejects 'fractal_lab $ARGS': $message"
  else
    fail "'fractal_lab $ARGS' must exit 2 with \"$message\" on stderr and nothing on stdout" "$(last_run)"
  fi
}

echo "Testing the command line mode of $BIN"

# --- Default schema (L=3 D=3 E=2, the README example)
expect_output "text report of the default schema, without a terminal (--text)" --text <<'EOF'
--- esquema L=3 D=3 E=2 ---
5 niveles, 121 nodos, 81 decisores
RAM 4.5 GiB (con margen 5.7 GiB), disco 1.6 GiB
CPU 413.0 ms/inferencia -> 2 vCPU, latencia 103.2 ms
Contenedor: medium (4 vCPU / 8 GiB)
--- nodos por nivel ---
N1  votantes  1  (copia 1)
N2  votantes  3  (copia 1)
N3  votantes  9  (copia 2)
N4  votantes  27  (copia 2)
N5  decisores 81
EOF

expect_output "JSON of the default schema (--json)" --json <<'EOF'
{
  "params": {"levels": 3, "depth": 3, "exponent": 2},
  "profile": {"runtime_mib": 512, "leaf_mib": 48, "voter_mib": 6, "disk_pct": 40, "leaf_us": 5000, "voter_us": 200, "target_ms": 250, "headroom_pct": 25},
  "tree": {"total_levels": 5, "nodes": 121, "leaves": 81, "voters": 40, "saturated": false,
    "levels": [
      {"level": 1, "nodes": 1, "role": "voter", "copy": 1, "copy_root": false},
      {"level": 2, "nodes": 3, "role": "voter", "copy": 1, "copy_root": false},
      {"level": 3, "nodes": 9, "role": "voter", "copy": 2, "copy_root": true},
      {"level": 4, "nodes": 27, "role": "voter", "copy": 2, "copy_root": false},
      {"level": 5, "nodes": 81, "role": "leaf", "copy": 2, "copy_root": false}
    ]},
  "resources": {"leaves_mib": 3888, "voters_mib": 240, "runtime_mib": 512,
    "ram_mib": 4640, "required_mib": 5800, "disk_mib": 1652,
    "cpu_us": 413000, "path_us": 5800, "vcpus": 2, "latency_us": 103250},
  "container": {"tier": "medium", "vcpus": 4, "ram_gib": 8, "replicas": 1, "cluster": false}
}
EOF

# --- Field options
run --json --levels 4 --depth=5 --profundidad 2 --exponencial 1 --leaf_mib 100 --margen=0
expect_contains "field options: names, aliases, --name=value, profile fields, last value wins" \
  '"params": {"levels": 4, "depth": 2, "exponent": 1},' \
  '"profile": {"runtime_mib": 512, "leaf_mib": 100, "voter_mib": 6, "disk_pct": 40, "leaf_us": 5000, "voter_us": 200, "target_ms": 250, "headroom_pct": 0},' \
  '"tree": {"total_levels": 4, "nodes": 15, "leaves": 8, "voters": 7, "saturated": false,' \
  '"resources": {"leaves_mib": 800, "voters_mib": 42, "runtime_mib": 512,' \
  '"ram_mib": 1354, "required_mib": 1354, "disk_mib": 337,' \
  '"cpu_us": 41400, "path_us": 5600, "vcpus": 1, "latency_us": 20700},' \
  '"container": {"tier": "small", "vcpus": 2, "ram_gib": 4, "replicas": 1, "cluster": false}'

run --levels 4 --depth=2 --exponent 1
expect_contains "field options in the text report" '--- esquema L=4 D=2 E=1 ---' \
  '4 niveles, 15 nodos, 8 decisores' 'N4  decisores 8'

run --json --text
expect_contains "the last output option wins (--json --text)" '--- esquema L=3 D=3 E=2 ---'
run --text --json
expect_contains "the last output option wins (--text --json)" '"params": {"levels": 3, "depth": 3, "exponent": 2},'

# --- Edge cases
run --json --levels 1
expect_contains "single level schema: the root is the only decider" \
  '"tree": {"total_levels": 1, "nodes": 1, "leaves": 1, "voters": 0, "saturated": false,' \
  '      {"level": 1, "nodes": 1, "role": "leaf", "copy": 1, "copy_root": false}'

run --json --levels 12 --depth 12 --exponent 5
expect_contains "saturated counts are capped at 2^64-1 and flagged (L=12 D=12 E=5)" \
  '"tree": {"total_levels": 56, "nodes": 18446744073709551615, "leaves": 18446744073709551615, "voters": 18446744073709551615, "saturated": true,' \
  '{"level": 56, "nodes": 18446744073709551615, "role": "leaf", "copy": 5, "copy_root": false}' \
  '"cluster": true}'
run --levels 12 --depth 12 --exponent 5
expect_contains "saturated counts in the text report" '56 niveles, >1.8E nodos, >1.8E decisores'

run --json --levels 7 --depth 6 --exponent 1
expect_contains "schema that does not fit in one container: cluster of the largest tier" \
  '"tree": {"total_levels": 7, "nodes": 55987, "leaves": 46656, "voters": 9331, "saturated": false,' \
  '"ram_mib": 2295986, "required_mib": 2869983, "disk_mib": 918190,' \
  '"cpu_us": 235146200, "path_us": 6200, "vcpus": 941, "latency_us": 244944},' \
  '"container": {"tier": "8xlarge", "vcpus": 96, "ram_gib": 384, "replicas": 10, "cluster": true}'
run --levels 7 --depth 6 --exponent 1
expect_contains "cluster in the text report" 'aviso: no cabe en un contenedor; cluster de 10 x 8xlarge'

# --- Help: every field of the JSON output (params and profile) is listed
run --json
mapfile -t fields < <(grep -E '^  "(params|profile)": ' "$TMP/out" | grep -oE '"[a-z_]+": [0-9]+' | cut -d '"' -f 2)
if (( ${#fields[@]} < 11 )); then
  fail "help: expected the 11 fields of src/field.c in the JSON output, found ${#fields[@]}: ${fields[*]}"
fi
for args in --help -h "--levels 4 --help"; do
  # shellcheck disable=SC2086 # split the arguments of the case on purpose
  run $args
  expect_contains "help (fractal_lab $args)" "Uso: fractal_lab" "${fields[@]/#/  --}"
done

# --- Invalid arguments
expect_usage_error "opcion desconocida '--foo'" --foo 1
expect_usage_error "opcion desconocida '--json=1'" --json=1
expect_usage_error "falta el valor de '--levels'" --levels
expect_usage_error "'abc' no es un entero positivo (--levels)" --levels abc
expect_usage_error "'-1' no es un entero positivo (--depth)" --depth -1
expect_usage_error "'' no es un entero positivo (--levels)" --levels=
expect_usage_error "levels fuera de rango (1-12): 13" --levels 13
expect_usage_error "exponent fuera de rango (1-5): 0" --exponencial=0
expect_usage_error "runtime_mib fuera de rango (0-65536): 65537" --runtime_mib 65537
expect_usage_error "argumento no valido 'foo'" --levels 4 foo
expect_usage_error "argumento no valido '-x'" -x
expect_usage_error "argumento no valido '--'" --
expect_usage_error "opcion desconocida '--foo'" --foo --help

# --- Write errors
if [[ -w /dev/full ]]; then
  ARGS="--json >/dev/full"
  RC=0
  env -u TERM "$BIN" --json </dev/null >/dev/full 2>"$TMP/err" || RC=$?
  : >"$TMP/out"
  if [[ "$RC" -eq 1 ]] && grep -qF "no se pudo escribir la salida" "$TMP/err"; then
    pass "write errors: exit 1 (fractal_lab --json >/dev/full)"
  else
    fail "write errors: 'fractal_lab --json >/dev/full' must exit 1 with an error on stderr" "$(last_run)"
  fi
fi

echo
if (( failures > 0 )); then
  echo "Model lab CLI tests FAILED: $failures of $checks checks failed"
  exit 1
fi
echo "Model lab CLI tests passed: $checks checks"
