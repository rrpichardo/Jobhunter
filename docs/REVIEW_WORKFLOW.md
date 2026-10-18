# Reciprocal coding-agent review

Codex builds → Claude Code reviews. Claude Code builds → Codex reviews.
The user requires opposite-agent review only. Do not request the implementation
agent to review its own fixes or add that approval as another merge gate.
Only one implementation owner edits at a time; a reviewer reads and reports.
Read AGENTS.md and PLAN.md before review. Record the full reviewed commit SHA,
concrete findings, test evidence, and remaining cloud gaps on the PR. Re-review
substantive fixes. Existing three-cycle counters apply across handoffs and PRs.

## Claude-authored PRs: request Codex

1. Push the feature branch, open the milestone PR and get its head SHA:
   `gh pr view <number> --json headRefOid,url`.
2. Post `@codex review` on that PR, with the intended acceptance criteria and
   explicit request for review only. This request is authorized by the user's
   reciprocal-review instruction. Do not ask Codex to implement fixes concurrently.
3. Wait for an actual Codex review covering that SHA. A reaction, CI badge,
   comment asking for setup, or absence of findings without a completed review
   does not satisfy the gate. After fixes, push and request another review.
   Use `scripts/wait_codex_review.sh <pr> <full-head-sha> [minutes]` to wait: it recognises
   Codex's clean receipt, a review with inline findings, the summary state and a usage-limit
   reply (exit 0 clean, 1 findings, 2 usage limit, 3 timeout or changed head). It checks
   the live PR head before polling and again before reporting clean. Usage-limit
   replies must be newer than both the wait start and the latest human review
   request, if any. Historical usage-limit replies are ignored even when automatic
   review adds no request comment. A reply in the same timestamp second is also
   ignored, conservatively waiting for a review or timeout. Only exit 0 for the exact current head
   counts as a clean review. Recheck the SHA at merge time as well.
4. If the GitHub integration is unavailable, have Codex review the PR in the
   Codex app/IDE, or use the already-installed local Codex CLI in a clean separate
   checkout of the PR: `git fetch origin`, `gh pr checkout <number>`, then
   `codex review --base origin/main`. Keep this review read-only; inspect its
   actual report and post it with the exact SHA and test evidence. This local
   review is development evidence, never production cloud-runtime evidence.
   CLI authentication/access in a Claude cloud session is **not verified**.
5. Missing reviewer access remains outstanding. Do not self-approve or merge.
   Follow the separate merge authorization in AGENTS.md; it currently expressly
   covers Codex-built milestones and does not automatically authorize all other merges.

## Automatic GitHub reviews

Official setup: https://learn.chatgpt.com/docs/third-party/github . In Codex
settings select `rrpichardo/Jobhunter`, enable code review and automatic reviews,
then choose the desired review trigger. Check repository and personal settings.
No API key, paid Actions-based model call, or new service is required by this
procedure. Availability and usage remain subject to the existing account.

**Checkpoint:** the user signed in to ChatGPT in Chrome Richard. The official
`https://chatgpt.com/settings/code-review?provider=github` page loads, but shows
“No repositories found,” including after searching Jobhunter. Codex Cloud settings
also show no saved environments. Automatic review is **not enabled or verified**.
Next action: connect/authorize this repository to Codex in this signed-in account,
then enable repository reviews and verify a real response on a Claude PR. Do not
change unrelated repositories or enable “Use credits for reviews.” If connection
requires new sensitive repository permissions, show the exact access request and
obtain action-time confirmation before granting it. Local Codex CLI is installed
and `codex review --help` verified, so app/CLI review remains the fallback. Do not
mistake the existing Claude GitHub Action for Codex review.

## Codex-authored PRs: request Claude

Use the existing Claude Code review integration or authenticated Claude CLI for a
read-only review. Record actual findings and SHA; a green action can skip a draft
or a previously reviewed PR. Review the latest revision after substantive fixes.
Do not install a paid model API workflow to work around missing access.
