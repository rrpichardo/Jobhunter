# JobHunter instructions

Read `AGENTS.md` for shared implementation and review rules, `docs/PLAN.md` for
product scope, and `docs/SETUP.md` for setup answers. Codex may build the code;
the full V0 daily workflow runs in the Claude Code cloud environment.

For implementation continuation, read [docs/CLAUDE_HANDOFF.md](docs/CLAUDE_HANDOFF.md)
first for current commits, setup state, counters and exact next actions. Preserve
the distinction between local review, manual cloud proof and scheduled production.

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
