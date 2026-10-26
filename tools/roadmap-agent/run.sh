#!/usr/bin/env bash
# Roadmap agent orchestrator.
# Picks the next roadmap (round-robin, skipping roadmaps without pending items or
# with an open PR), lets Claude implement one item on a branch from develop,
# then pushes it and opens a PR. It never merges nor approves anything.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"

# Overridable via ~/.config/roadmap-agent.env (loaded by the systemd unit) or the environment
REMOTE="${ROADMAP_AGENT_REMOTE:-origin}"
BASE_BRANCH="${ROADMAP_AGENT_BASE:-develop}"
MODEL="${ROADMAP_AGENT_MODEL:-opus}"
EFFORT="${ROADMAP_AGENT_EFFORT:-max}"
TIMEOUT="${ROADMAP_AGENT_TIMEOUT:-4h}"
ROADMAP_DIR="${ROADMAP_AGENT_ROADMAP_DIR:-docs}"
DRY_RUN="${ROADMAP_AGENT_DRY_RUN:-0}"   # 1 = only print the selected roadmap
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/roadmap-agent"
BASE_REF="$REMOTE/$BASE_BRANCH"

mkdir -p "$STATE_DIR/runs" "$STATE_DIR/worktrees"
exec 9>"$STATE_DIR/lock"
flock -n 9 || { echo "Another roadmap agent run is in progress, exiting."; exit 0; }

RUN_ID="$(date +%Y%m%d-%H%M%S)"
RUN_DIR="$STATE_DIR/runs/$RUN_ID"
mkdir -p "$RUN_DIR"
exec > >(tee -a "$RUN_DIR/orchestrator.log") 2>&1

log() { printf '[%s] %s\n' "$(date +%T)" "$*"; }
die() { log "ERROR: $*"; exit 1; }

# Unchecked items inside the "## Roadmap" section, ignoring HTML comments
pending_items() {
  awk '
    /<!--/ { in_comment = 1 }
    in_comment { if (/-->/) in_comment = 0; next }
    /^## / { in_roadmap = ($0 ~ /^## Roadmap[[:space:]]*$/); next }
    in_roadmap && /^[[:space:]]*- \[ \]/ { print }
  '
}

roadmap_name() { basename "$1" .md | sed 's/^roadmap-//'; }

command -v claude >/dev/null || die "claude CLI not found in PATH"
gh auth status >/dev/null 2>&1 || die "gh is not authenticated (run: gh auth login)"

cd "$REPO_DIR"
log "Fetching $REMOTE"
git fetch --prune --quiet "$REMOTE"
git rev-parse --verify --quiet "$BASE_REF" >/dev/null || die "$BASE_REF does not exist"

mapfile -t ROADMAPS < <(git ls-tree --name-only "$BASE_REF" "$ROADMAP_DIR/" | grep -E '/roadmap-[^/]+\.md$' | sort)
(( ${#ROADMAPS[@]} )) || die "No $ROADMAP_DIR/roadmap-*.md found in $BASE_REF"

mapfile -t OPEN_HEADS < <(gh pr list --state open --limit 500 --json headRefName -q '.[].headRefName')

# Round-robin starting after the last roadmap used
last="$(cat "$STATE_DIR/last-roadmap" 2>/dev/null || true)"
start=0
for i in "${!ROADMAPS[@]}"; do
  [[ "${ROADMAPS[i]}" == "$last" ]] && start=$(( (i + 1) % ${#ROADMAPS[@]} ))
done

ROADMAP=""
for (( k = 0; k < ${#ROADMAPS[@]}; k++ )); do
  candidate="${ROADMAPS[(start + k) % ${#ROADMAPS[@]}]}"
  prefix="roadmap/$(roadmap_name "$candidate")/"
  count="$(git show "$BASE_REF:$candidate" | pending_items | wc -l)"
  if (( count == 0 )); then
    log "Skip $candidate: no pending items"
    continue
  fi
  open_pr=""
  for head in "${OPEN_HEADS[@]}"; do [[ "$head" == "$prefix"* ]] && open_pr="$head"; done
  if [[ -n "$open_pr" ]]; then
    log "Skip $candidate: open PR from $open_pr"
    continue
  fi
  ROADMAP="$candidate"
  log "Selected $ROADMAP ($count pending items)"
  break
done

[[ -n "$ROADMAP" ]] || { log "Nothing to do."; exit 0; }
[[ "$DRY_RUN" == 1 ]] && { log "Dry run, stopping here."; exit 0; }

# Advance the rotation even if this run fails, so a broken roadmap can't block the others
echo "$ROADMAP" > "$STATE_DIR/last-roadmap"

BRANCH_PREFIX="roadmap/$(roadmap_name "$ROADMAP")/"
WT="$STATE_DIR/worktrees/$RUN_ID"
BRANCH=""
PUSHED=0

cleanup() {
  git -C "$REPO_DIR" worktree remove --force "$WT" 2>/dev/null || true
  # Keep the local branch if it could not be pushed, so the work isn't lost
  if [[ -n "$BRANCH" && "$PUSHED" == 1 ]]; then
    git -C "$REPO_DIR" branch -D "$BRANCH" >/dev/null 2>&1 || true
  fi
  git -C "$REPO_DIR" worktree prune
}
trap cleanup EXIT

git worktree add --quiet --detach "$WT" "$BASE_REF"

PROMPT="$(cat "$SCRIPT_DIR/prompt.md")"
PROMPT="${PROMPT//\{\{BASE_REF\}\}/$BASE_REF}"
PROMPT="${PROMPT//\{\{ROADMAP\}\}/$ROADMAP}"
PROMPT="${PROMPT//\{\{BRANCH_PREFIX\}\}/$BRANCH_PREFIX}"
PROMPT="${PROMPT//\{\{RUN_DIR\}\}/$RUN_DIR}"

log "Running Claude (model=$MODEL effort=$EFFORT timeout=$TIMEOUT) in $WT"
rc=0
(
  cd "$WT"
  timeout --kill-after=2m "$TIMEOUT" claude -p "$PROMPT" \
    --model "$MODEL" \
    --effort "$EFFORT" \
    --dangerously-skip-permissions \
    --disallowedTools "Bash(git push:*)" "Bash(gh:*)" "Bash(git merge:*)" \
      "Bash(podman stop:*)" "Bash(podman rm:*)" "Bash(podman-compose:*)" "Bash(systemctl:*)" \
    --add-dir "$RUN_DIR" \
    --output-format json < /dev/null
) > "$RUN_DIR/claude.json" || rc=$?
log "Claude exited with code $rc"
jq -r '"Cost: \(.total_cost_usd // "?") USD, turns: \(.num_turns // "?"), duration: \((.duration_ms // 0) / 60000 | floor) min"' \
  "$RUN_DIR/claude.json" 2>/dev/null || true

STATUS="$(head -n1 "$RUN_DIR/status" 2>/dev/null || echo "MISSING")"
log "Agent status: $STATUS"

cd "$WT"
BRANCH="$(git symbolic-ref --short -q HEAD || true)"
AHEAD="$(git rev-list --count "$BASE_REF"..HEAD)"
if (( AHEAD == 0 )); then
  log "No commits on top of $BASE_REF, no PR will be opened."
  exit 0
fi

if [[ -z "$BRANCH" ]]; then
  BRANCH="${BRANCH_PREFIX}run-$RUN_ID"
  git switch --quiet -c "$BRANCH"
elif [[ "$BRANCH" != "$BRANCH_PREFIX"* ]]; then
  new="${BRANCH_PREFIX}${BRANCH##*/}"
  git branch -m "$BRANCH" "$new"
  BRANCH="$new"
fi

# Guard: roadmaps may only change by moving one item, verbatim, to Completed
WARNINGS=()
[[ "$STATUS" == DONE* ]] || WARNINGS+=("Agent status is '$STATUS' but there are commits.")
[[ -z "$(git status --porcelain)" ]] || WARNINGS+=("The agent left uncommitted changes (not included in this PR).")

while IFS= read -r f; do
  [[ "$f" == "$ROADMAP" ]] || WARNINGS+=("Another roadmap was modified: \`$f\`.")
done < <(git diff --name-only "$BASE_REF"...HEAD -- "$ROADMAP_DIR/" | grep -E '/roadmap-[^/]+\.md$' || true)

roadmap_diff="$(git diff -U0 "$BASE_REF"...HEAD -- "$ROADMAP")"
removed="$(awk '/^@@/ { h = 1; next } h && /^-/ { print substr($0, 2) }' <<<"$roadmap_diff" | grep -v '^[[:space:]]*$' || true)"
added="$(awk '/^@@/ { h = 1; next } h && /^\+/ { print substr($0, 2) }' <<<"$roadmap_diff" | grep -v '^[[:space:]]*$' || true)"
moved=0
while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  if [[ "$line" =~ ^[[:space:]]*-\ \[\ \]\ (.*)$ ]]; then
    moved=$(( moved + 1 ))
    grep -qF -- "- [x] ${BASH_REMATCH[1]}" <<<"$added" \
      || WARNINGS+=("Item not moved verbatim to Completed: \`$line\`")
  else
    WARNINGS+=("Roadmap line removed or edited: \`$line\`")
  fi
done <<<"$removed"
while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  [[ "$line" =~ ^[[:space:]]*-\ \[x\]\  ]] || WARNINGS+=("Unexpected line added to the roadmap: \`$line\`")
done <<<"$added"
(( moved == 1 )) || WARNINGS+=("Expected exactly 1 item moved to Completed, found $moved.")

TITLE="$(head -n1 "$RUN_DIR/pr-title.txt" 2>/dev/null || true)"
[[ -n "$TITLE" ]] || TITLE="$(git log -1 --format=%s)"
BODY_FILE="$RUN_DIR/pr-body.final.md"
{
  cat "$RUN_DIR/pr-body.md" 2>/dev/null || echo "_The agent did not provide a PR description._"
  if (( ${#WARNINGS[@]} )); then
    printf '\n## ⚠️ Orchestrator warnings\n\nThis PR was opened as draft because the run did not pass the automatic checks:\n\n'
    printf -- '- %s\n' "${WARNINGS[@]}"
  fi
  printf '\n---\nRoadmap: `%s` · Run: `%s` · Opened automatically by `tools/roadmap-agent`. Review required, the agent never merges.\n' "$ROADMAP" "$RUN_ID"
} > "$BODY_FILE"

log "Pushing $BRANCH"
git push --quiet -u "$REMOTE" "$BRANCH"
PUSHED=1

DRAFT=()
(( ${#WARNINGS[@]} )) && { DRAFT=(--draft); log "Opening as draft: ${#WARNINGS[@]} warning(s)"; }
PR_URL="$(gh pr create --base "$BASE_BRANCH" --head "$BRANCH" --title "$TITLE" --body-file "$BODY_FILE" "${DRAFT[@]}")"
PR_NUMBER="${PR_URL##*/}"
log "Opened PR #$PR_NUMBER: $PR_URL"

if grep -q 'PR: pending' "$ROADMAP"; then
  sed -i "s/PR: pending/PR: #$PR_NUMBER/" "$ROADMAP"
  git commit --quiet -m "doc(roadmap): link item to PR #$PR_NUMBER" -- "$ROADMAP"
  git push --quiet "$REMOTE" "$BRANCH"
fi

log "Done."
