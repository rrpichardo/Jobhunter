# Implementation attempt log

## October 18 input diagnostic follow-up — writer cycle 7

- Claude confirmed the unexpected writer failure fix, then reproduced that missing
  input files inherited the new unexpected-error label. A failing regression
  confirms this happens before Google access. File-read OS errors now map to
  `invalid_sync_input` at the read boundary; the existing artifact checkout-path
  error has an explicit safe label. Later unexpected writer errors remain distinct.
- Locked suite: 158 tests and 10 subtests passed. No remote or live writes. User's
  unlimited local repair-cycle direction applies; fresh static review requested.

## October 18 retrospective diagnostic follow-up — writer cycle 6

- Claude's context-complete retrospective review of superseded #7 found a CLI
  diagnostic that still applied to current #8: an unexpected writer failure was
  mislabeled invalid input. A regression failed after an injected post-mutation
  exception; the CLI now emits fixed `unexpected_sync_error`, retaining recovery
  guidance and suppressing raw exception details. No retry policy changed.
- The retrospective adapter/engine coverage concern is already addressed by the
  current fake-workbook live-harness tests, including applied/unapplied timeout
  cases. Pending replay follows recorded journal order; operators must not edit
  hidden recovery state. The one-megabyte journal bound remains intentional.
- Locked writer suite: 157 tests and 10 subtests passed. Local review cycle 6 is
  covered by the user's "do as many as needed" direction; no pushes or live calls.

## October 18 user continuation instruction — review limits superseded

- After the source milestone reached its original three-review cap, the user
  explicitly directed "do as many as needed" for local fix/review cycles.
  Continue the necessary cycles while retaining the historical counters. This
  removes the prior numeric pause for this repair task; it does not authorize
  further pushes, merges, new services or deployment. Keep source stop rules.
- Whole-PR Claude reviews were requested for #7, #8, #9 and #10, including already
  pushed heads. #7 is superseded; its retrospective findings are not instructions
  to revive it. #8 review at `e3536e4` found the missing `run_not_pending` CLI label.
  A failing CLI regression reproduced it, then the error was allowlisted.
- The reported sticky-lock-on-429 issue was not reproduced: 429 is already a
  rejected 4xx, and the existing fresh-receipt retry regression passed. Never
  treat a stale receipt as rejection proof for genuinely uncertain writes.
- This is writer repair/review cycle 5, authorized by the user's updated direction.
  No live calls ran; fresh Claude review of the local diagnostic fix is required.

## October 18 Codex review repairs — user-authorized extension

- Codex reviewed exact writer head `6a61f356d1e472f34ea6242a3c0b76bb02a88f6b`
  (the previously undelivered cycle 3). It reproduced reuse of a quarantined run ID
  when the damaged journal has no manifest. The #7 completed-Run-Log recovery issue
  is already fixed in #8 and is not a new outstanding repair.
- The user then instructed "Implement the changes", authorizing one additional
  writer fix/review cycle (4). Prior counters remain intact; this does not authorize
  an unlimited extension. Codex is the sole active implementation owner.
- Added an end-to-end regression: remove a pending run's manifest, quarantine its
  remaining chunks without changing their values, and refuse that ID before Jobs
  mutation. It failed on the reviewed code. Preparation now checks any quarantined
  key for the identity, including orphan chunks. Locked full suite: 155 tests and
  10 subtests passed; `git diff --check` passed. Fresh Claude review is required.
- This repair does not repeat live collection or Google writes, change deployment
  status, or satisfy the outstanding cloud/schedule acceptance gates.

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

### M0 review/repair cycle 2 and new setup direction

- Claude reviewed `aaed72b` and confirmed original findings resolved. New findings:
  Windows newline translation broke returned digests; nested server JSON could
  escape error handling; lone surrogates lost evidence; inconsistent-empty and
  duplicate-ID paths lost failure metadata; some storage wording was stale.
- Fixes: publish exact binary JSON bytes (ASCII escaping supports surrogates) and
  hash those same bytes; catch server JSON recursion; preserve schema-error attempt/
  HTTP evidence; report positive-total/empty lists as failed; align current setup
  and handoff wording with user-approved Sheet state and credential bootstrap.
- Regression failures were reproduced before fixing; the digest byte-equality test
  also runs on Windows CI. Full local suite: 61 tests, 10 subtests passed.
- Actual cloud recheck at `aaed72b` passed locked installation, 57 tests/10 subtests,
  a new single-request Greenhouse harvest (655 valid, 0 rejected, 15 PM candidates,
  1 selected, complete-response) and trusted-digest validation (1 record, exit 0).
  Commands and outputs were inspected in the UI. This predates the binary-output
  fix; recheck affected tests and saved-data validation without another live fetch.
- User approved the Google credential-variable fallback with workbook-only Editor,
  no project IAM roles, Sheets API only, in-memory loading or private 0600 temp-file
  cleanup. First inspect compatible GCP secret types. Re-inspection confirmed Add
  secret disabled, so types could not be inspected; no key/variable was entered.
- Review cycle 3 is the final allowed review/repair cycle for this PR. Submit the
  fixed current revision for review; do not merge unresolved actionable findings.

### M0 cycle 3 result — blocked from merge

- Claude reviewed `2a7e7dfa1af561cc017d8abade5474e6a47e7183`, ran 61 tests/10
  subtests, and confirmed the cycle-2 fixes. One remaining actual edge case:
  non-finite Retry-After values (`inf` / `1e999`) flow into failure metadata and
  prevent strict JSON serialization, losing the source-failure artifact.
- PR #5 remains unmerged. The three-cycle cap has been reached. The next action
  is a user decision to authorize one additional fix/review cycle or leave the
  PR open. Do not automatically reset/increase the cap or advance dependent code.
- Proposed bounded repair: reject non-finite retry delays, preserve finite HTTP
  status/attempt evidence, and add a CLI-level regression. Require another Claude
  review of the resulting exact head plus Linux/Windows checks before merging.

### Google Cloud setup access — attempt 1 / 3

- Inspected the selected account's Google Cloud console for the planned service
  account setup. Console reports Cloud access unavailable; no project/API/billing
  or credential changes made. No personal account identifiers are recorded here.
- User directed switching to another existing Google account. Account chooser is
  open; the specific account selection is pending. Do not create another account
  or attempt to bypass the access restriction. This is distinct from credential
  injection compatibility; its counter does not reset the earlier blockers.

### M0 cycle 4 — explicit one-cycle extension authorized

- User authorized exactly one additional fix-and-Claude-review cycle for PR #5.
  This extends the milestone counter to 4; it does not reset prior cycles or
  authorize a fifth cycle.
- Reproduced the missing failure artifact with CLI regressions for `inf` and
  `1e999` Retry-After values before the fix. Ignore non-finite or negative header
  delays and retain bounded local backoff; valid finite delays remain honored.
- Added CLI coverage for infinity, overflow, NaN and negative headers, checking
  three attempts, bounded waits and retained HTTP 429 evidence.
- `uv run --locked python -m pytest -q`: 65 passed, 10 subtests passed.
  `git diff --check` passed. Fresh exact-head Claude review and CI remain required.
- The user selected a different existing Google account and signed in. The
  Cloud console now opens successfully; an existing free trial is shown. No
  billing settings were changed, and no credentials have been created or entered.

### M0 first-stage integration and Google setup progress

- Cycle 4 review of `0f7b43659a496c80a25079dd9107ccda1439e154`: Claude
  Code Sonnet found no unresolved actionable findings. Linux/Windows CI passed.
- Actual JobHunterEnv replay at that exact head: locked sync exit 0; Python
  3.12.3 / uv 0.13.1; 65 tests and 10 subtests passed; saved harvest/extraction
  accepted the original trusted digest, 1 validated record, exit 0. No new live
  fetch, Sheet write or social access. Tool command outputs inspected in UI.
- PR #5 merged under standing authorization at `d77842d`; main tests passed
  again. This completes only the first M0 harvest/extraction stage.
- Dedicated Google project created outside the organization without selecting
  a billing account. Sheets API enabled. Dedicated writer service account created
  with no project roles. User explicitly confirmed workbook-only Editor sharing
  (notifications off) and JSON key creation. UI confirmed shared workbook and
  downloaded key; agent did not open/read the key.
- Reinspection now shows Add secret enabled and a GCP access token (with Service
  Account Key) type. This supersedes the earlier disabled-control evidence.
  Prepared host sheets.googleapis.com, workbook-specific path prefix and Sheets
  scope, with no impersonation. User is entering JSON directly; save and live
  Python compatibility remain outstanding. Do not use the variable fallback
  unless this preferred mechanism proves unavailable/incompatible.

### M0 writer branch — authentication foundation (not deployed)

- New feature branch `codex/m0-sheet-writer` starts from merged PR #5.
- Wrote failing connection/configuration/sanitization tests, then the explicit
  network-secret-only gspread connection helper. Full locked suite: 70 tests,
  10 subtests passed; diff whitespace check passed. No real Google API call.
- User is saving the preferred GCP secret directly. Pause screen inspection
  during private input. Next live action after user confirms saved/closed:
  read-only Python workbook access in actual JobHunterEnv, with metadata counts
  only in output. Do not print headers, auth/session internals, keys or tokens.
- Independent read-only helper checked the proposed sheet-creation lock against
  Google's atomic batch and unique ID/title documentation. It is a candidate for
  compliant writers, not a supported lock primitive or protection against human
  lock deletion. Live overlap proof remains mandatory. No writer code yet.

### Connection checkpoint PR #6 — review cycle 1 / 3

- PR #6: https://github.com/rrpichardo/Jobhunter/pull/6 . Claude reviewed exact
  `0260388`, found no blocking bug, and identified actionable safe-diagnostic and
  handoff consistency issues. Its plan-mode restrictions prevented running tests;
  local and Linux/Windows CI passed 70 tests/10 subtests independently. No invented
  reviewer test execution is claimed.
- Add allowlisted error categories / numeric HTTP status so a bounded failed auth
  attempt is diagnosable without provider bodies. New test first failed, then the
  full locked suite passed 71 tests/10 subtests. Clarify preferred auth in plan,
  user-authorized key use, write-endpoint proof still needed, and current counters.
- Credential-delivery attempt 3 / 3 now tests the newly available GCP network
  secret after the relevant external capability changed. No counter reset:
  earlier two delivery investigations remain recorded. Secret configuration
  succeeded; actual Python connectivity is being checked once. If incompatible,
  stop this blocker and report evidence/next action rather than trying repeatedly.
- User pasted the key into chat and expressly accepted disclosure and authorized
  continued use. Agent recommended replacement; user direction supersedes the
  earlier mandatory-rotation handoff. No key value is stored in repository or logs.
  Direct native JSON copy/paste saved the restricted GCP secret; non-secret
  workbook/auth-mode variables saved too. No application Sheet write occurred.
- Fresh current-revision review is required after these fixes (cycle 2 / 3).

- Credential delivery attempt 3 result: **initial read access succeeded** in
  JobHunterEnv at `0260388`. One bounded connection attempt (workbook open plus
  worksheet metadata read), `RESULT=success tab_count=1`, exit 0, tree clean.
  Actual command output expanded/verified. This resolves initial delivery/read
  connectivity, not write endpoints, recovery or serialization. No Google writes.
- Cycle 2 / 3 is the fresh review of the safe-discriminator and handoff fixes.
  Local locked suite: 71 tests/10 subtests passed. No secret value in tracked files.

## M0 writer/recovery implementation — continuation

- PR #6 merged at `fa899c32de3267507c51658274d5bc2509ef7193` after exact-head
  Claude cycle-2 review, 71 tests/10 subtests locally and in JobHunterEnv, plus
  Linux/Windows CI. Main rerun passed 71 tests/10 subtests. Code is a connection
  foundation only. User then directed Codex to continue rather than hand off now.
- New owner branch: `codex/m0-sheet-sync`; Codex remains sole implementer.
- Write-endpoint proof attempt 1 / 3 succeeded in actual JobHunterEnv at229a97b:
  one atomic addSheet/updateCells structural call created hidden `_M0AuthProbe`
  (sheet ID 2026101801), and one RAW values batch wrote a harmless literal.
  FORMULA readback exactly matched `=jobhunter_probe_literal`; it was not executed
  as a formula. All reported booleans true, exit 0, clean tree. Tool output
  expanded/verified. No retry, user cells unchanged, probe tab retained.
  This proves endpoint compatibility, not application writer/recovery/concurrency.
- Wrote failing planner, lock and adapter tests, then implementations. Planner
  tests preserve user fields/first seen, reordered headers, sorted rows, duplicate
  identities, ambiguous headers and RAW-ready literal values. Lock tests cover
  overlap and uncertain acquisition/deletion. Adapter tests prove atomic owner
  creation, RAW range writes, append-only grid growth and sanitized HTTP evidence.

- Journal, engine and CLI now pass test-first behavior checks, including bounded
  retries, exact long-delay stop, explicit pending Run Log before job mutation,
  same-ID repeat verification, multi-chunk replay and corruption rejection.
- `uv run --locked python -m pytest -q`: 107 tests/10 subtests passed locally;
  diff whitespace check passed. Application writer live proof and fresh Claude
  review remain outstanding; no milestone completion or deployment claim.

### M0 writer review/repair cycle 1 / 3

- First whole-change Claude Code review is being requested for the writer branch.
  It must cover the current committed head, not just the connection checkpoint.
  No existing review covers the new journal/lock/writer. Record findings and
  preserve this counter across handoffs; no review success is assumed in advance.


### User-requested Claude Code handoff — writer cycle 1 remains open

- Review of 4c9800c completed; actual findings posted on PR #7 at
  https://github.com/rrpichardo/Jobhunter/pull/7#issuecomment-6243645600 .
  Current fixes address control/line-ending validation, scoped journal checks,
  delayed-write safety with atomic unique receipts, hidden HTTP resubmissions,
  original-error preservation and release-outcome diagnostics. Read-only Astra
  analysis supported the receipt design; no second implementation owner edited.
- Internal test namespace added after its regression test failed as expected.
  Global lock remains shared. Full local suite:125 passed,10 subtests passed.
  Fresh current-head review is still outstanding; cycle2 has NOT been started.
- Remaining cycle-1 work: manual poisoned-journal quarantine/recovery, preventing
  completed Run Log downgrade on replay, additional uncertainty tests. Per-run
  source history and all application live checks remain outstanding.
- User now requests stopping for a committed/pushed handoff and PR. Preserve
  draft #7; no merge or deployment claim. CLAUDE_HANDOFF.md has exact next actions.
- Billing: user chose to leave existing free-trial link unchanged; dialog canceled,
  project linkage rechecked. No billing setting changed. Do not repeat this ask.

- Final handoff verification: `uv run --locked python -m pytest -q` passed
  125 tests/10 subtests; `git diff --check` passed. No new live API collection,
  writer mutation, or scheduled proof was attempted during handoff preparation.
- Reciprocal review: AGENTS.md/CLAUDE.md require Codex review for Claude work.
  User signed into ChatGPT in Richard. Official review settings load but show no
  repositories, including Jobhunter search; no saved Codex Cloud environments.
  Automatic review remains blocked on repository connection, not user sign-in.
  No permission, credits, billing or automatic-review setting changed. Local
  installed `codex review --help` verified; manual review route documented.

### Claude Code takeover of writer milestone — review cycle 2 / 3 requested

- Claude Code is now sole implementation owner. Branch `claude/m0-sheet-sync` starts
  at checkpoint `9f4fd58` (PR #7 head); replacement PR supersedes draft #7. Counters
  are carried over, not reset: writer review cycle 1 / 3 was consumed by the review
  of `4c9800c`; this push is the fix set for it and requests **cycle 2 / 3**
  from Codex (reciprocal review; no self-review).
- Finished the remaining cycle-1 fixes, tests first (3 failed before the code):
  a recovered run whose final Run Log row already landed is no longer rewritten to
  `pending`; manual `--quarantine-run` renames a poisoned run's `_State` keys without
  discarding values and refuses reuse of that run ID. Added receipt tests: failed
  receipt read, definitive 429 followed by a fresh-receipt retry, 408/500/503 treated
  as unknown, and an interrupt through the engine retaining the lock.
- `.venv/bin/python -m pytest -q`: 136 passed, 10 subtests. Still open: per-run
  source history, the paced live harness, actual JobHunterEnv proof, scheduled M0.

- Codex GitHub review of `d76caef` was started but not delivered (user reports its
  usage limit was reached). A same-model Claude `/engineering:code-review` was run on
  the user's instruction; it is **not** the required Codex review and does not count
  as approval. It produced minor findings, fixed in the next commit (completed runs
  cannot be quarantined, original Completed time kept on recovery, quarantine no
  longer creates `_State`, cell-count cap). Suite: 139 passed, 10 subtests.
  The new head still needs Codex review; no merge until it is obtained. The review
  counter stays at cycle 2 / 3 because these are self-review fixes, not a Codex cycle.

- Codex completed its review of `d76caef` (cycle 2 / 3): one P2 finding, refuse to
  quarantine completed runs; already fixed in `99b1154`. Cycle 3 / 3 (final) was then
  requested from Codex for `99b1154`. No further cycle remains for this milestone
  without a user decision. The earlier "never returned" note above is superseded.

### Writer live harness result (JobHunterEnv, October 18, 2026)

- Codex cycle 3 / 3 for `99b1154`: the GitHub reviewer answered only that its usage
  limit was reached (resets Oct 18, 12:12 AM per the local CLI). A local
  `codex review` fallback hit the same limit. **No cycle-3 review was delivered; no
  fourth cycle was started.** Request the same review again after the reset; do not
  buy credits or change plan.
- Built `scripts/live_harness.py` (commit `c5e2398`); the actual cloud run passed all
  eight clean scenarios, exit 0. Details: V0_VERIFICATION.md. Counters unchanged:
  this is a test of the existing writer, not a new blocker attempt.
- The saved real-posting data from the earlier cloud session no longer exists (the
  container was reclaimed, as the handoff warned). The user then approved one fresh
  bounded public harvest with an independently retained hash; see the next section
  once recorded.
