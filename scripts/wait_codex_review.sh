#!/usr/bin/env bash
# Wait for Codex's GitHub review of one exact PR head and report the outcome.
#
#   scripts/wait_codex_review.sh <pr-number> <head-sha> [timeout-minutes]
#
# Recognises every form Codex replies in: a "codex-review-receipt" issue comment
# ("Didn't find any major issues" = clean), a pull-request review whose body names the
# reviewed commit (with inline comments = findings), the "codex-review-state" summary JSON,
# and a usage-limit reply. Exit codes: 0 clean, 1 findings, 2 usage limit, 3 timeout.
set -euo pipefail
pr=${1:?pr number}; head=${2:?full head sha}; minutes=${3:-60}
short=${head:0:10}
bot='chatgpt-codex-connector'
deadline=$(( $(date +%s) + minutes * 60 ))
started=$(date -u +%Y-%m-%dT%H:%M:%SZ)

check_head() {
  current=$(gh pr view "$pr" --json headRefOid --jq .headRefOid)
  if [ "$current" != "$head" ]; then
    echo "CODEX_HEAD_CHANGED $short"
    exit 3
  fi
}

clean() {
  # A push may have happened while the review responses were being read.
  check_head
  echo "CODEX_CLEAN $short"
  exit 0
}

findings() {
  gh api "repos/{owner}/{repo}/pulls/$pr/comments" --paginate \
    --jq ".[] | select(.user.login | startswith(\"$bot\")) | select(.commit_id == \"$head\" or .original_commit_id == \"$head\")
          | \"- \(.path):\(.line // .original_line) \(.body | split(\"\n\")[0] | gsub(\"<[^>]*>|\\\\*\"; \"\"))\""
}

while :; do
  check_head
  comment_data=$(gh pr view "$pr" --json comments)
  comments=$(echo "$comment_data" | jq --arg b "$bot" '[.comments[] | select(.author.login == $b) | .body]')
  reviews=$(gh pr view "$pr" --json reviews --jq "[.reviews[] | select(.author.login == \"$bot\") | .body]")
  all=$(jq -s 'add' <(echo "$comments") <(echo "$reviews"))

  # 1. Receipt or review that names this exact commit.
  match=$(echo "$all" | jq -r --arg s "$short" '[.[] | select(contains("Reviewed commit:") and contains($s))] | last // empty')
  if [ -n "$match" ]; then
    if grep -q "Didn't find any major issues" <<<"$match"; then clean; fi
    echo "CODEX_FINDINGS $short"; findings; exit 1
  fi
  # 2. Summary state JSON for this commit, once completed.
  state=$(echo "$comments" | jq -r --arg h "$head" '[.[] | capture("\"code_review\":(?<j>\\{[^}]*\\})")? | .j | fromjson | select(.commit_sha == $h)] | last // empty | @json' 2>/dev/null || true)
  if [ -n "$state" ] && [ "$(jq -r .status <<<"$state")" = completed ]; then
    if [ "$(jq -r .has_unresolved_findings <<<"$state")" = true ]; then echo "CODEX_FINDINGS $short"; findings; exit 1; fi
    clean
  fi
  # 3. Only new usage-limit replies count: automatic reviews may have no new
  # human request. Historical replies cannot terminate a freshly started wait.
  if echo "$comment_data" | jq -e --arg b "$bot" --arg start "$started" '
    ([.comments[] | select(.author.login != $b)
      | select(.body | test("@codex[[:space:]]+review"; "i"))
      | .createdAt] + [$start] | max) as $since
    | [.comments[] | select(.author.login == $b and .createdAt > $since)]
    | sort_by(.createdAt) | last | .body // "" | test("usage limit"; "i")' >/dev/null; then
    echo "CODEX_USAGE_LIMIT $short"; exit 2
  fi
  [ "$(date +%s)" -ge "$deadline" ] && { echo "CODEX_TIMEOUT $short"; exit 3; }
  sleep 60
done
