#!/usr/bin/env bash
# Smoke test for a running NISAR SAR stack, through the entry point users hit (Caddy).
#
# Usage: tools/ci/smoke-test.sh [BASE_URL]
#   BASE_URL       where Caddy serves the app (default: http://127.0.0.1:8089,
#                  the port published by podman-compose.yml)
#   SMOKE_TIMEOUT  seconds to wait for the backend to answer (default: 180)
#
# Checks:
#   - backend: GET <base>/api/sites, the request the frontend makes, answers 200
#     with a non-empty catalog read from MySQL: Spring started, the Flyway
#     migrations ran and the database connection works.
#   - frontend: GET <base>/ serves the app page and every local asset it
#     references answers 200 (JavaScript modules with a JavaScript MIME type).
#
# Exits 1 if any check fails, 2 on usage errors. Needs curl and jq.
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:8089}"
BASE_URL="${BASE_URL%/}"
TIMEOUT="${SMOKE_TIMEOUT:-180}"
RETRY_INTERVAL=5

usage_error() { echo "smoke-test: $*" >&2; exit 2; }

for cmd in curl jq; do
  command -v "$cmd" >/dev/null || usage_error "'$cmd' is required"
done
[[ "$TIMEOUT" =~ ^[0-9]+$ ]] || usage_error "SMOKE_TIMEOUT must be a number of seconds, got '$TIMEOUT'"
[[ "$BASE_URL" =~ ^https?://[^/]+ ]] || usage_error "BASE_URL must be an http(s) URL, got '$BASE_URL'"
ORIGIN="${BASH_REMATCH[0]}"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

checks=0
failures=0

pass() {
  checks=$((checks + 1))
  printf '[ OK ] %s\n' "$1"
}

# fail SUMMARY [DETAIL...] (empty details are skipped)
fail() {
  local summary="$1" detail
  shift
  checks=$((checks + 1))
  failures=$((failures + 1))
  printf '[FAIL] %s\n' "$summary"
  for detail in "$@"; do
    if [[ -n "$detail" ]]; then printf '       %s\n' "$detail"; fi
  done
  if [[ "${GITHUB_ACTIONS:-}" == true ]]; then
    # Annotation shown on the run summary; % and newlines must be escaped
    summary="${summary//%/%25}"
    printf '::error title=Smoke test::%s\n' "${summary//$'\n'/%0A}"
  fi
}

# fetch URL: body in $TMP/body; STATUS (000 without an HTTP response), CONTENT_TYPE and ERROR
fetch() {
  local out
  if out="$(curl -sS --max-time 10 -o "$TMP/body" -w '%{http_code} %{content_type}' "$1" 2>"$TMP/err")"; then
    STATUS="${out%% *}" CONTENT_TYPE="${out#* }" ERROR=""
  else
    STATUS="000" CONTENT_TYPE="" ERROR="$(head -n 1 "$TMP/err")"
    : > "$TMP/body"
  fi
}

# Outcome of the last fetch, for messages
result() { if [[ -n "$ERROR" ]]; then echo "$ERROR"; else echo "HTTP $STATUS"; fi; }

# "body: <start of a response body>" on one line (default: the last one), nothing if empty
body_detail() {
  local excerpt
  excerpt="$(head -c 300 "${1:-$TMP/body}" | tr -s '[:space:]' ' ')"
  if [[ -n "${excerpt// /}" ]]; then echo "body: $excerpt"; fi
}

# Where to look when the backend never answered 200, from the last fetch
backend_hint() {
  case "$STATUS" in
    000) echo "Nothing answered at $BASE_URL: is Caddy running and is the URL right?" ;;
    502|503|504) echo "Caddy is up but the backend is not answering: Spring initialization, Flyway migration and database connection errors are in the backend and mysql logs." ;;
    *) echo "Unexpected answer: check the backend logs and that Caddy routes /api/* to the backend." ;;
  esac
}

is_module() { [[ "${1%%[?#]*}" =~ \.m?js$ ]]; }

echo "Smoke testing $BASE_URL (backend timeout: ${TIMEOUT}s)"

# --- Backend: wait for Spring to answer, then check the catalog it reads from MySQL
start=$SECONDS
while :; do
  fetch "$BASE_URL/api/sites"
  elapsed=$((SECONDS - start))
  if [[ "$STATUS" == 200 ]] || (( elapsed >= TIMEOUT )); then break; fi
  echo "  waiting for the backend (${elapsed}s/${TIMEOUT}s): $(result)"
  sleep "$RETRY_INTERVAL"
done

CATALOG_IS_VALID='
  (.countries | type == "array" and length > 0)
  and ([.countries[].sites[]?] | length > 0 and all(.id | type == "string" and length > 0))
  and (.observationDates | type == "array" and length > 0)'
CATALOG_SUMMARY='"\(.countries | length) countries, \([.countries[].sites[]] | length) sites, \(.observationDates | length) observation dates"'

if [[ "$STATUS" != 200 ]]; then
  fail "backend: GET /api/sites did not answer 200 within ${TIMEOUT}s (last: $(result))" \
    "$(body_detail)" "$(backend_hint)"
elif ! jq -e "$CATALOG_IS_VALID" "$TMP/body" >/dev/null 2>&1; then
  fail "backend: GET /api/sites answered 200 without a non-empty site catalog" "$(body_detail)"
else
  pass "backend: GET /api/sites -> 200, $(jq -r "$CATALOG_SUMMARY" "$TMP/body") read from the database"
fi

# --- Frontend: the app page, then every local asset it references
fetch "$BASE_URL/"
if [[ "$STATUS" != 200 ]]; then
  fail "frontend: GET / -> $(result)" "$(body_detail)"
elif [[ "$CONTENT_TYPE" != text/html* ]]; then
  fail "frontend: GET / -> 200 with Content-Type '$CONTENT_TYPE', expected text/html"
else
  pass "frontend: GET / -> 200 ($CONTENT_TYPE)"
  cp "$TMP/body" "$TMP/page"
  # src/href attribute values, skipping URLs with a scheme (https:, data:...),
  # protocol-relative URLs and fragments
  mapfile -t assets < <(grep -oE "(^|[[:space:]])(src|href)=(\"[^\"]*\"|'[^']*')" "$TMP/page" \
    | sed -E 's/^[[:space:]]*(src|href)=.//; s/.$//' \
    | grep -vE '^([a-zA-Z][a-zA-Z0-9+.-]*:|//|#|$)' \
    | awk '!seen[$0]++')
  modules=0
  for asset in "${assets[@]}"; do
    case "$asset" in
      /*) url="$ORIGIN$asset" ;;
      *) url="$BASE_URL/${asset#./}" ;;
    esac
    fetch "$url"
    if [[ "$STATUS" != 200 ]]; then
      fail "frontend: GET $asset -> $(result)"
    elif is_module "$asset" && [[ "$CONTENT_TYPE" != *javascript* ]]; then
      fail "frontend: GET $asset -> 200 with Content-Type '$CONTENT_TYPE', browsers only run JavaScript modules served as JavaScript"
    else
      pass "frontend: GET $asset -> 200 ($CONTENT_TYPE)"
    fi
    if is_module "$asset"; then modules=$((modules + 1)); fi
  done
  if (( modules == 0 )); then
    fail "frontend: GET / references no local JavaScript module, is it the app page?" "$(body_detail "$TMP/page")"
  fi
fi

echo
if (( failures > 0 )); then
  echo "Smoke test FAILED: $failures of $checks checks failed against $BASE_URL"
  exit 1
fi
echo "Smoke test passed: $checks checks against $BASE_URL"
