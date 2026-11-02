#!/usr/bin/env bash
# Keeps one comment of github-actions[bot] up to date on a pull request: the one whose body starts with MARKER.
#
# Usage: tools/ci/pr-comment.sh PR_NUMBER MARKER BODY [--only-update]
#   BODY           the whole comment, MARKER included (as its first line, for the next run to find it)
#   --only-update  do nothing if there is no such comment yet
#
# Used by PR preview (preview.yml) for the preview link. Needs gh, with GH_TOKEN and GITHUB_REPOSITORY.
set -euo pipefail

(( $# == 3 || $# == 4 )) || { echo "usage: pr-comment.sh PR_NUMBER MARKER BODY [--only-update]" >&2; exit 2; }
pr="$1" marker="$2" body="$3" only_update="${4:-}"
[[ "$pr" =~ ^[1-9][0-9]*$ ]] || { echo "pr-comment: PR_NUMBER must be a number, got '$pr'" >&2; exit 2; }
[[ "$body" == "$marker"* ]] || { echo "pr-comment: BODY must start with MARKER" >&2; exit 2; }

id="$(gh api --paginate "repos/$GITHUB_REPOSITORY/issues/$pr/comments" \
  --jq ".[] | select(.user.login == \"github-actions[bot]\" and (.body | startswith(\"$marker\"))) | .id" | tail -n 1)"

if [[ -n "$id" ]]; then
  gh api -X PATCH "repos/$GITHUB_REPOSITORY/issues/comments/$id" -f body="$body" --jq .html_url
elif [[ "$only_update" != --only-update ]]; then
  gh api "repos/$GITHUB_REPOSITORY/issues/$pr/comments" -f body="$body" --jq .html_url
else
  echo "No preview comment on #$pr to update"
fi
