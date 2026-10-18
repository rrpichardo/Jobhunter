# JobHunter shared instructions

Read `docs/PLAN.md` before implementation or review. It defines product scope and
acceptance criteria. `docs/IMPLEMENTATION_PROMPT.md` is the implementation handoff;
`docs/SETUP.md` records setup answers and unresolved prerequisites. Treat older
probe results as historical evidence, not proof the current environment works.

## Build and execution

- Codex or Claude Code may build any repository component, including routine
  instructions, extraction prompts, schemas, and tests.
- Production runs in the Claude Code cloud routine. All V0 collection, including
  LinkedIn browsers and X, extraction, filtering, deduplication, Google Sheets
  writes, and scheduling must work without a local computer running.
- Prove the actual cloud runtime early. Verify network access, connectors,
  credentials, browser authentication, persistence, and scheduled execution.
  Report unsupported capabilities as blockers; do not replace cloud requirements
  with a local workflow or claim deployment from mocked tests.
- Claude extracts facts into validated structured records. Python owns identity,
  filtering, deduplication, reconciliation, and all Sheet writes. Preserve Status,
  Notes, and My rating on existing rows. Never infer eligibility from missing data.
- Keep keys, cookies, browser profiles, raw email, and personal account data out
  of Git, test fixtures, logs, and PR descriptions. Use sanitized fixtures and
  the dedicated environment for approved runtime secrets and Sheet `_State` for
  non-secret recovery data; temporary files stay private and outside Git.
- Follow the read-only social scope and source limits in the plan.
  Never apply to jobs or contact people. User completes account verification.
- Preserve the existing Claude Gmail connector. Read only forwarded job alerts
  carrying the `JobHunter` label in that connected account. Never broaden to the
  whole inbox if the label is absent or empty, or fetch unrelated messages from a
  matching thread. No Gmail writes; exclude account-verification/security messages.
  This is an application rule, not a restriction on the connector's account access.
- The user authorizes local computer/Chrome assistance for initial setup as listed
  in `docs/IMPLEMENTATION_PROMPT.md`, including the specific Gmail forwarding/filter
  and label configuration. That setup exception does not allow routine Gmail writes
  or a local production dependency. User enters private details and completes
  account creation and verification; never expose secrets in tool output.
- For the user-approved social bootstrap, the user logs in locally and provisions
  dedicated-account cookies directly in JobHunterEnv settings. Ordinary environment
  variables are permitted for these cookies; users/commands with environment access
  can read them. Never inspect or expose cookie values. Reconstruct temporary cloud
  sessions each run; put only non-secret allowance/recovery state in Sheet `_State`.
  Do not treat that tab as an atomic lock or add another hosting service/account.
  For Google authentication, first check for a compatible GCP service-account-key
  secret type. If unavailable, the user authorizes a dedicated JobHunterEnv
  credential variable: load in memory where possible; any required temp file is
  0600 in a private directory and deleted at run end. Use a dedicated service
  account with Editor on only the JobHunter workbook, no project IAM roles, and
  only the Sheets API enabled. Never dump environment variables, credentials or
  cookies. For the current dedicated Sheets key, the user explicitly accepted
  prior disclosure and authorized continued setup. Prior disclosure alone does
  not block this specific use; replacement remains recommended. This exception
  does not authorize copying credentials into Git, logs, PRs or the handoff.
  Read SETUP.md for actual provisioning status.

## Collaboration and verification

- One active implementation owner at a time. Work on a feature branch; use the
  `codex/` prefix for Codex work and `claude/` for Claude work. Preserve others'
  uncommitted changes. Coordinate handoffs through commits and PRs.
- Reciprocal review is required and belongs to the opposite agent only:
  Codex-authored changes receive Claude Code review; Claude-authored changes
  receive Codex review. Do not request a same-agent code-review approval or add
  it as another merge gate. Implementation tests and debugging still belong to
  the implementation owner. Before requesting review,
  push the revision and record its full SHA. Follow `docs/REVIEW_WORKFLOW.md`.
  Missing access, a skipped job, or an unanswered request is not approval.
- Open a PR for implementation changes. Have the other coding agent review the
  latest commit; resolve actionable findings, rerun affected checks, then obtain
  another review after substantive fixes. Do not represent an old review as
  covering newer changes. Missing reviewer access is an outstanding step.
- Open at least one PR per implementation milestone, with draft PRs for early
  feedback as needed. Do not batch the entire V0 into a final PR. For Codex-built
  milestones, obtain Claude Code feedback, resolve actionable findings, and verify
  the current revision before merging and advancing dependent implementation.
- The user grants standing authorization to merge Codex-built milestone PRs into
  main after all applicable tests and required CI checks pass, Claude Code has
  reviewed the latest revision, and all actionable findings are resolved. Obtain
  a fresh Claude review after substantive fixes and verify the revision being
  merged. A green review job or an older review alone does not satisfy this gate.
  Follow repository protection rules; never bypass a failed check or push
  implementation directly to main. Once these conditions pass, merge and continue
  dependent work without asking again. This authorization does not waive setup,
  spending, deployment-verification, or review-only restrictions. Other merges
  still follow the user's explicit direction.
- Run all applicable tests before claiming completion. Add regression tests for
  real bugs, fix failures without weakening assertions, and record commands and
  results. Separate offline tests, live integration checks, and scheduled evidence.
- Document blockers and the exact next action. Continue independent work when
  possible. Do not request secrets in chat or silently add paid services.
- Cap distinct attempts at three per blocker and repair/review cycles at three per
  milestone. Persist counters in `docs/ATTEMPTS.md` across implementation handoffs;
  do not reset them through delegation. The daily routine never edits this file;
  record runtime failures in Sources and Run Log instead.
  After exhaustion, report and stop that blocker;
  continue independent work. Follow the prompt's authorized pause/exit conditions
  and host goal rules rather than busy-polling or automatically extending the trial.

## Code Review Rules

- Read `docs/PLAN.md`; check the change against its intended behavior and scope.
- Prioritize actual bugs, duplicate jobs, overwritten user notes, incorrect
  eligibility, credential exposure, unsafe retries, cloud-only execution, and
  missing source/error evidence over cosmetic preferences.
- Each finding needs a file, line, concrete failure scenario, and practical impact.
- During a review-only task, do not edit code or merge the PR. Post findings when
  the review request authorizes posting them.
- A passing test suite does not prove external source access, scheduled execution,
  browser-session persistence, or completion of the observation period.
