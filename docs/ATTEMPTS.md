# Implementation attempt log

This is the durable log for implementation blockers and milestone repair cycles.
Read it before retrying work. Maximum: three distinct attempts per blocker and
three repair/review cycles per milestone. Counters survive handoffs and restarts.
Do not store secrets, raw email, cookies, or personal account data here.

The production daily routine never edits this document. Runtime source failures,
retry evidence, and daily social-collection allowances belong in protected cloud
run state and the Sources/Run Log records specified in the plan.

## Documentation handoff

- PR: https://github.com/rrpichardo/Jobhunter/pull/3
- Repair cycle 1: Claude reviewed `136dc4f`, found no blocking problems, and requested
  clearer follow-up wording, social verification limits, and an explicit attempt-log
  location. These clarifications were applied and submitted for re-review; see the
  PR for the final review result and reviewed revision.
- V0 application implementation has not started. No implementation blockers or
  runtime success claims are recorded yet.

## Record format for future blockers

For each blocker, record a stable name, affected requirement, attempt number/date,
sanitized evidence, the distinct approach tried, outcome, and next required action.
At the attempt limit, stop that blocker and state what changed condition or user
direction is required to resume. Do not reset a counter merely by renaming it.

## Bootstrap prerequisite PR #4 — October 17, 2026

- Branch: `codex/bootstrap-cloud-readiness`. Acceptance is locked setup, Linux and
  Windows CI, current Claude Code review, and an explicit capability inventory.
  This prerequisite PR does not complete M0 or authorize dependent implementation.
- Review cycle 1: local Claude Code Sonnet reviewed `e7c9c75` against `b37e483`;
  no actionable findings. Review posted to PR #4. Installation/test CI passed on
  both required platforms. New cloud evidence documentation will require review
  of the final revision; do not apply the old review to newer content.
- Existing GitHub Claude review workflows were preserved. Draft-PR check status
  alone is not treated as substantive feedback; local review text is recorded.

### Cloud credential delivery — attempt 1 / 3

- Requirement: secure service-account temporary file for Python Google auth.
- Approach/evidence: inspected JobHunterEnv UI and official cloud environment docs;
  bounded actual cloud probe found no established secret-file provider. Ordinary
  environment variables are explicitly visible; proxy secrets attach HTTP headers.
- Outcome: unresolved, not an authentication failure (no credential provisioned).
- Next action: identify and prove a supported protected credential delivery route
  within the existing approved budget before creating/provisioning a private key.

### Cloud persistent state and concurrency — attempt 1 / 3

- Requirement: protected state across distinct daily sessions and one atomic writer.
- Approach/evidence: inspected official routine/environment docs and actual cloud
  tool capabilities. New sessions and ephemeral VMs do not prove protected shared
  storage; no cross-session atomic lock was established.
- Outcome: unresolved. No session data or recovery artifacts have been stored.
- Next action: verify a supported durable store/lock and scheduler concurrency
  mechanism. Do not use a Sheet marker as an atomic lock or Git for secret state.

### Interactive cloud social authentication — attempt 1 / 3

- Requirement: user authenticates dedicated cloud LinkedIn/X sessions, then restores
  them across routine runs. Accounts remain not created per confirmed setup.
- Approach/evidence: actual cloud capability probe reports Chromium/Playwright
  installed but no LinkedIn MCP or supported user-operated login flow established.
- Outcome: setup unresolved; no live social request made, no challenge encountered.
- Next action: prove supported interactive cloud auth and protected persistence
  before asking the user to create/authenticate the dedicated accounts.

These are distinct unresolved prerequisites, not exhausted retries. The initial
cloud public Greenhouse fetch succeeded and is recorded in V0_VERIFICATION.md.

## October 17 continuation

- PR #4 merged as `7f77cb5` after Linux/Windows CI and fresh local Claude review of
  `4e104fa`. Post-merge `uv sync --locked` and the complete suite passed (6 tests,
  10 subtests). The user granted standing authorization for future Codex milestone
  merges after passing checks and a current Claude review; AGENTS.md records it.
- Existing automatic review plugin skips PRs once Claude has commented, so a
  green job alone is insufficient for updated revisions. Fresh local Claude
  reviews are available; preserve exact reviewed SHAs and post results to each PR.
- User confirms **no existing external cloud resources**. A proposed Cloudflare
  Free workaround was questioned as outside the plan and is not authorized.
  No Cloudflare implementation, account, or service activation is planned.

### Cloud prerequisites — attempt 2 / 3 (each existing blocker)

- Distinct approach: checked official provider alternatives and self-hosted runner
  availability instead of repeating the earlier live public-network probe.
- Credential delivery: Anthropic request-header secrets do not document provision
  of the private-key file required by the planned service-account auth. Google
  workload federation requires an identity provider credential that this runtime
  has not been shown to issue. No secret was provisioned or inspected.
- Persistent state/concurrency: no hosted Pro protected cross-session volume or
  atomic writer primitive established. Official self-hosted runners are documented
  for Team/Enterprise and require infrastructure, so they are not an approved
  substitute for the current Pro setup.
- Interactive cloud social auth: no documented user-operated browser handoff or
  session-restore mechanism established. A headless browser installation alone
  still does not satisfy the requirement. No social fetch/account setup attempted.
- Outcome: all three remain open. Do not count new-service research as an approved
  architecture change or perform another identical probe. Next action is a
  provider-supported mechanism within the approved plan; if none can be verified,
  report the specific limitation and obtain a scope decision. Independent Python
  implementation/testing can continue. One distinct attempt remains per blocker.
- Primary references: https://code.claude.com/docs/en/cloud-environments,
  https://code.claude.com/docs/en/routines,
  https://code.claude.com/docs/en/self-hosted-environments,
  https://docs.cloud.google.com/iam/docs/workload-identity-federation.

## M0 source/extraction code stage

- Branch `codex/m0-thin-pipeline`; acceptance and module interfaces are in
  `docs/superpowers/plans/2026-10-17-m0-data-path.md`.
- Initial tests observed failing before production modules existed; source,
  validation, HTTP and CLI tests now pass. A test-file parenthesis typo was fixed
  before its intended missing-module failures were verified; assertions unchanged.
- This stage has no Sheet writer, recovery, production auth or daily schedule.
  Review cycle 1 has not yet started; live code-path proof remains outstanding.

### User clarification after attempt 2

- User supplied local-login → direct cookie settings → fresh cloud restore as the
  intended social bootstrap. Adopt it without adding infrastructure. Interactive
  login inside the cloud VM is no longer required. This changes that prerequisite;
  it is not proof of authenticated collection, and counters are not reset.
- Non-secret pending work, markers and daily social allowances may live in Sheet
  `_State`; no secret cross-run session volume is needed under this approach.
  Atomic serialization and safe state reconciliation remain separate open gates.
- Cookie provisioning and tool compatibility still need testing, with no secret
  values printed or inspected. Current repo has no `.mcp.json`; select and pin the
  package before claiming a declared cookie-compatible MCP exists.
- Keep three attempts total per blocker across collector options, and immediate
  challenge/429 stops. The proposed three fresh attempts per tool would reset the
  existing shared cap, so that portion of the suggestion was not adopted.
- Read-only primary-doc check: twscrape supports `auth_token` / `ct0` cookie
  activation (https://github.com/vladkens/twscrape). Its default indefinite account
  waits and rate-limit rotation are not approved runtime behavior. No live social
  request or authentication attempted; this is compatibility research, not a third
  attempt to provision/authenticate the missing accounts.

### M0 review/repair cycle 1

- Claude Code read the complete plan and reviewed `f913601` against `7f77cb5`.
  Review posted on PR #5. It reproduced protocol/proxy failures, per-item schema
  failure, absent-total coverage and input hygiene problems; it also ran all 43
  tests/10 subtests successfully without installing anything.
- Fixed with regressions: sanitize all HTTP errors and retain attempt/status/wait
  evidence; quarantine malformed items without dropping valid jobs; preflight
  output paths before fetching; unknown completeness when total is absent; strict
  URL whitespace and canonical board case; bounded nested JSON; explicit empty/
  partial extraction count/status; trusted-reference SHA-256 check; atomic
  exclusive artifact publication; remove obvious hidden markup from source text.
- Atomic publication regression was also run against the prior implementation
  and failed before the fixed full suite passed. No assertion was weakened.
- The source API's public post ID remains the M0 key; the official API documents
  its uniqueness (https://docs.greenhouse.io/job-board.html). Broader cross-source
  or multiple-post/requisition reconciliation is not implemented or claimed by
  this one-post M0 stage. Speculative repost equivalence is not inferred.
- Artifact hash checks depend on a trusted reference retained outside source
  artifacts; they are not protection against an agent changing both file and
  reference. HTML cleaning does not execute CSS or prove rendered visibility.
- `uv run --locked python -m pytest -q`: 57 passed, 10 subtests passed. The full
  changed revision, including user-supplied cookie/bootstrap documentation, must
  receive a fresh review and affected cloud checks before merge.
