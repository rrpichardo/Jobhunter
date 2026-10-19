# JobHunter instructions

Read `AGENTS.md` for shared implementation and review rules, `docs/PLAN.md` for
product scope, and `docs/SETUP.md` for setup answers. Codex may build the code;
the full V0 daily workflow runs in the Claude Code cloud environment.

For implementation continuation, read [docs/CLAUDE_HANDOFF.md](docs/CLAUDE_HANDOFF.md)
first for current commits, setup state, counters and exact next actions. Preserve
the distinction between local review, manual cloud proof and scheduled production.

## What is pending (keep this consistent)

When the user asks what is pending, what Claude needs from them, or where things stand, read section 0 of
`docs/PENDING.md` first, check it against GitHub (open PRs, Codex replies), answer in plain, non-technical language,
and correct that section if it is out of date. Update section 0 in the same change whenever a decision, a task, a PR
or a review state changes. Do not keep a second list anywhere else.

## Review instructions

When reviewing a pull request:

- Read docs/PLAN.md to understand the intended behavior.
- Look for actual bugs, duplicate jobs, overwritten user notes,
  incorrect eligibility decisions, exposed credentials,
  and failures during retries.
- Explain each finding in plain English.
- Include the affected file, line, and a concrete failure example.
- Prioritize actionable problems over cosmetic preferences.
- Post findings on the pull request.
- Review only: do not change code or merge the pull request.

## When Claude authors changes

Request **Codex** review of the latest pushed revision using
[docs/REVIEW_WORKFLOW.md](docs/REVIEW_WORKFLOW.md). Claude reviewing its own PR
does not satisfy the opposite-agent gate. Post the reviewed SHA and findings,
resolve actionable issues, rerun checks, and request fresh review after fixes.
