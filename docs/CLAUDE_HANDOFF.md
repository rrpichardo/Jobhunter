# Claude Code continuation handoff

## Next owner — LinkedIn hiring posts, then X, then real cloud test

User explicitly requested searches of LinkedIn profile posts because people
announce jobs outside the job board, followed by X and then the real test.
User then requested a handoff before further implementation because context
was running short. Resume this order; do not interpret the handoff as cancellation.

- Main baseline is `5200ac01773ee51f7ddf18ea6b13267ac7911ac6` (PR17 merged).
  PR16 is merged, reviewed and tested as recorded below. No social collector
  implementation has started; only read-only research/preflight in this segment.
- LinkedIn jobs **and hiring posts** remain distinct collection coverage under
  `linkedin-login`, with post permalinks retained as evidence. Broader approved
  roles and current salary/geography rules apply to both social sources. No
  likes, follows, replies, connections, messages, applications or account creation.
- Dedicated `LINKEDIN_LI_AT`, `X_AUTH_TOKEN`, `X_CT0` are already provisioned
  per prior verified setup; never request values in chat, print them, inspect
  cookies locally or dump environment values. Recheck only nonempty booleans.
- Implement/test LinkedIn as its own milestone PR, then X as its own PR.
  Codex implementation needs fresh Claude review of each pushed head and CI;
  standing authorized merges still apply. No same-agent review gate.
- The existing plan already defines cloud-only restoration, limits and output.
  Keep current LinkedIn <=5 searches / <=50 detail views, X <=10 queries /
  <=200 posts, one live attempt per source per America/New_York day. Existing
  eight-per-source / 150-total collection caps also remain pending a decision.
  Reserve each daily allowance durably in `_State` BEFORE live collection,
  under the structural workbook writer lock; `_State` itself is not an atomic
  lock. Fail closed on ambiguous writes. No allowance implementation exists yet.
- Research the cookie-compatible LinkedIn MCP route first; use the plan's small
  read-only Playwright fallback if unsupported. Current upstream candidates are
  not selected/pinned or installed by this work. Do not add local production
  dependencies, a hosted scraper, paid API/proxy or interactive cloud login.
- X uses pinned/tested twscrape with temporary private cookie account DB,
  deleted after the run. Suppress sensitive library logs, disable telemetry,
  bound requests/time/pagination and account waits; no password login/IMAP,
  automatic account rotation/relogin or indefinite rate-limit waiting.
- Claude extracts explicit facts into validated structured postings. Python
  owns filtering, stable identity, deduplication and Sheet writes. A post without
  a direct application URL remains a lead using its canonical post URL; preserve
  post/source evidence and unresolved fields, never infer salary eligibility.
- Real-test gate: after reviewed collectors and cloud-safe allowance/writer
  coordination exist, test actual JobHunterEnv LinkedIn posts then X within
  that day's allowance, record results/errors honestly in Sources/Run Log, and
  verify delivery/repeat from saved normalized data without a second live fetch.
  Gmail comparison is unavailable, not zero. Test fresh session restoration;
  manual tests still do not prove scheduled daily execution.
- Independent Gmail routing/live adapter and schedule remain open. Gmail UI
  blocker stays 3/3; this new social work does not authorize another UI retry.

### Read-only research and preflight

Cloud validation session (same JobHunterEnv):
https://claude.ai/code/session_01Kydab84oh1GMjzuFahVswG . Latest prompt begins
`Social-cloud preflight only`; it asks for a clean detached checkout at the
baseline above, pinned uv/Python/package versions, boolean cookie presence,
empty headless-browser launch, and read-only lock/pending/allowance readiness.
No social/Gmail requests, cookie injection or Sheet writes were authorized
for that preflight. Inspect its expanded command output before citing results;
no live social allowance has been consumed by the preflight itself.

Expanded outputs already inspected: exact baseline HEAD, clean tracked and
untracked tree; uv0.13.1, project Python3.12.3; all three cookie variables
nonempty (values never read back). Python `playwright`, `twscrape` and
`mcp-server-linkedin` are not installed in project or system Python. The image
has Node Playwright1.56.1 under `/opt/node-tools/node_modules/playwright`, Node
`/opt/node22/bin/node`, and Chromium141.0.7390.37 under `/opt/pw-browsers`.
An empty headless context launched, had zero cookies, stayed on `about:blank`
and closed cleanly, exit0. This is browser availability only, not social login.
Workbook readiness output was still pending when preparing this checkpoint;
inspect the final preflight receipt before reserving a social allowance.

Primary upstream references checked October 18:
- https://github.com/stickerdaniel/linkedin-mcp-server : current README lists
  `search_posts` as well as job searches, but its setup emphasizes saved local
  browser profiles/interactive login. Direct supplied-cookie cloud restoration
  remains unverified; inspect exact version/source before choosing it.
- https://github.com/bcharleson/linkedincli : supports cookie env configuration,
  but its current README expressly requires local MCP session origination, so
  it cannot be adopted as the production cloud route under this plan.
- https://github.com/vladkens/twscrape : current README shows
  `API.pool.add_account_cookies`, `API.search`, bounded pool-wait options and
  `TWS_TELEMETRY=0`. API/source/version compatibility and internal retry behavior
  still need inspection. `limit` is a target, not a hard fetch/response cap;
  enforce independent bounds in our collector. No installed version is assumed.


## Current checkpoint — PR #16 merged and manual cloud smoke passed

This checkpoint supersedes older pending-review/open-PR statements below;
those entries preserve chronology, not current status.

- PR #16 merged at `1df1e7ccbc7579b149085993ded07ca8f9829df7` on October 18.
  Claude cycle 9 found no actionable findings on reviewed head
  `110ea30d7cc4f97ac78a76ea6a05ea405db11632`. Required Linux/Windows checks and
  Claude action passed; the actual reviewer report, not the badge, satisfied
  reciprocal review. Evidence: PR16 comment `issuecomment-6255774750`.
- Offline post-merge suite: 577 tests / 10 subtests passed. Actual JobHunterEnv
  locked tests also passed 577/10 on the reviewed head before merge.
- Manual cloud run `pr16-broad-001` on the exact merge SHA fetched Stripe once,
  selected one real Product management role excluded by historical `ai_pm_match`,
  and delivered it through Python. Salary stayed unresolved. Identical repeat
  exited 0; readback confirmed 168 jobs, zero duplicate IDs, all 167 previous
  IDs present once, and unchanged Status/Notes/My rating. One complete Run Log
  row, accurate partial-response source counts and released lock were verified.
  See V0_VERIFICATION.md for digest and scope limits.
- This is not deployed daily collection. Gmail routing remains uninstalled;
  its UI blocker stays 3/3. The live Claude connector adapter/CLI binding, a
  genuine forwarded alert test, social cloud restoration/collectors and actual
  scheduled delivery remain open. Existing credentials/cookies are provisioned;
  do not recreate accounts or expose their values.
- Next independent code milestone: implement the actual cloud Gmail message
  adapter and extractor binding against verified connector payloads, retaining
  exact-label scope and security exclusions. End-to-end Gmail testing depends
  on a genuine alert plus precise forwarding/label filters. Do not retry the
  exhausted filter UI blocker without manual completion or a relevant change.
- User input still needed: correct Cosign and desired school/MBA URLs; settle
  the saved-cookie collector approach and proposed collection-cap change.
  Current caps remain eight per source / 150 per batch. Do not ask for account
  credentials in chat. PR16's extra repair authorization did not lift Gmail's cap.

## Latest continuation — broader alerts and salary preferences

Latest cycle-8 repair preserves mode alternatives at conjunction/double-separator
boundaries while keeping the verified JSearch Remote, country path. Local577/10
passes; fresh exact-head cycle-9 Claude review and CI remain required. Continued
PR16 repair authorization remains in force; no Gmail deployment is claimed.

Latest cycle-7 repair supports JSearch's `Remote, city/state/country` format,
with a parser-to-salary-to-row regression. Local565/10 passes; fresh exact-head
cycle-8 Claude review and CI remain required. Prior ambiguous mode alternatives
stay unresolved. Continued PR16 repair authorization remains in force.

Latest cycle-6 repair handles comma-separated unknown alternatives and attached
long-dash/Remoto labels. Explicit known regional hierarchy forms normalize before
splitting; unfamiliar qualifiers remain unresolved and retained. Local557/10
passes; exact pushed-head cycle-7 Claude review and CI remain required. User's
continued PR16 repair authorization is still in force; Gmail UI remains separate.

Latest cycle-5 repair keeps country-less city/department and unclassified places
unresolved; alternative locations cannot use the lower floor when another place
or mode-only option is unknown, including missing-comma US formats. Local suite
passes 540/10. Fresh exact-head cycle-6 Claude review and CI are required before
merge. User's continued PR16 repair authorization remains in force.

Latest repair after cycle 4 restricts department normalization so it cannot
consume a second locality and handles Bogotá DC/CO spellings. Unknown forms stay
unresolved. Local suite passes 518/10; fresh exact-head cycle-5 Claude review and
CI are required. Continued PR16 repair authorization remains in force.

**User resumed PR16:** "do it until is fixed" explicitly authorizes continued
PR16 repair/review cycles, superseding the cap stop below. Gmail UI stays at
3/3 independently. Root repaired the remaining mixed-location cases with
regressions; 505 tests / 10 subtests pass locally. Fresh pushed-head Claude
cycle-4 review and CI are required before merge; do not infer approval.

**Stop checkpoint:** PR16 cycle 3 reviewed code SHA
`9e1f2ff0de4b9a3163e689ce99831d9f81f46f16` and still found two mixed-location
defects: US-first regional city/CO/DO order can drop valid leads; ambiguous
CO/PA/AR US city codes can falsely satisfy LATAM pay. PR16 is open, unmerged,
three cycles exhausted. User was asked for one additional cycle; do not infer
approval from silence. See ATTEMPTS.md and PR16 cycle-3 comment for reproductions.
Current code passed 486/10 locally, in actual JobHunterEnv and required CI, but
that does not resolve the review findings. Gmail UI blocker remains separately
3/3, awaiting manual action or a relevant capability change.

PR #16 is the implementation milestone. Cycle-1 and cycle-2 Claude findings
were reproduced and repaired; latest local suite is 486 tests / 10 subtests.
Fresh pushed-head cycle 3/3 review and CI remain required. Actual JobHunterEnv
locked tests passed 475/10 on earlier repair `67ca7f8`; current-revision cloud
test confirmation is still needed. PR comments retain exact-SHA cloud evidence.

PR #15 was merged at `974ec2c`; its pending-review entries below are historical.
LinkedIn dedicated-account UI now confirms 18 daily email/notification alerts,
including broader non-AI roles and remote US/LATAM PM searches (SETUP.md).
User confirmed annual USD floors: US including remote-from-US 140,000; LATAM
including remote 70,000. This replaces the old any-salary remote LATAM exception.
LATAM on-site/hybrid scope remains Colombia/Dominican Republic.

Codex is continuing broader Python collection filtering and a message-scoped
Gmail intake boundary on `codex/salary-preferences`. Another Codex agent stopped
at a usage limit; root took implementation ownership. Tests/review/deployment
must be checked on the final pushed revision. Gmail intake currently accepts an
injected connector adapter; the real cloud adapter payload binding and CLI path
are not implemented or verified. Do not claim production Gmail collection.

Actual Claude cloud label listing verified `JobHunter` exists with zero messages
and threads; no message fetching occurred. Local dedicated-account job-alert
metadata search also returned no matches. Wait for a genuine alert to verify
precise forwarding/labeling rules. The forwarding-checkbox blocker remains at
three attempts, with manual completion or relevant UI change required. Do not
reset counters or replace cloud execution with local Gmail collection.

## Latest continuation — PR review and operator checklist

- Cycle-3 Claude review of `8fc2a7c` confirmed the code findings fixed but found
  request-before-watcher documentation could miss fast usage-limit replies. User
  explicitly waived this PR's repair cap. Corrected the manual request order and
  documented pre-start automatic-review limits; fresh pushed-head review/CI remain
  required. The Gmail UI blocker has three attempts and is still paused; no filter
  was installed. Dedicated alerts still need enabling. See ATTEMPTS.md.

- PLAN.md now records the unresolved user setup/decision list, including enabling
  dedicated-account alerts and later cleanup of old main-account subscriptions.
  Forwarding registration is verified, but fresh alert delivery/cloud Gmail access
  are not. Historical LinkedIn/TrueUp/Glassdoor alert metadata was inspected only
  under the user's explicit setup permission; it does not broaden routine scope.
- Claude reviewed `341560c` for PR #15 and confirmed the stale-head fix, but found
  an old usage-limit reply still ended automatic-review waits without a new human
  request. A regression failed before repair; fresh suite: 386 tests / 10 subtests.
  The new repair requires pushed-head Claude review and CI. The old head's green
  checks do not approve the repair. See ATTEMPTS.md cycle 2; do not reset counters.

## Codex continuation checkpoint — October 18, 2026

- PR #13 is merged. Another process merged PR #14 at `6c29058` while Codex was
  repairing its actual P1/P2 review findings. Repairs are preserved in follow-up
  PR #15 (`codex/review-watcher-repairs`), not pushed directly to remote main.
  Offline verification: 384 tests / 10 subtests, Bash syntax and diff check passed;
  Linux/Windows CI passed on repair `6f5c9b0`. Claude CLI returned a session limit,
  and the automatic Claude action failed. No Claude review/merge approval exists.
- Gmail destination confirmed by the user; `JobHunter` label created. Forwarding
  destination registration sent a verification link. User must verify directly;
  no forwarding/filter enabled yet. See SETUP.md. Preserve all label-only rules.
- User questioned the eight-jobs-per-source / 150-jobs-total collection caps.
  Proposed retaining all matching jobs found with safe batch delivery and a
  separate AI-processing budget; answer/implementation still pending. Existing
  caps remain unchanged. Explain browser/social setup in plain language before
  relying on the user's tentative preference as a final scope decision.
- No new social access, source harvest, Sheet write or deployment evidence.

## Handover from Claude (Opus) — October 18, 2026, evening

Start here in a new conversation or in Codex. Read AGENTS.md (opposite-agent review only:
Codex reviews Claude PRs, Claude reviews Codex PRs) and the sections below for history.

**State of GitHub.** `main` = `cf1424f` (PRs #4-#11 merged, CI green, 330 tests). Open: **PR #13**
`claude/m2-jsearch-jooble` (JSearch + Jooble keyed sources, JSearch moved to `/search-v2`, the
150-job writer cap now shared round-robin across sources). Needs Codex review; nothing merged.
PR #12 was closed unmerged (its 36539f4 cloud evidence was superseded by PR #11).

**Cloud evidence for PR #13** (JobHunterEnv session, see V0_VERIFICATION once recorded): at
`166304c` 379 tests passed, the probe exited 0 with JSearch delivering 6 and Jooble 4 jobs, and no
key value appeared in output, artifact or logs. `sheets_sync --run-id m4-sources-004` and its
identical repeat both exited 0; readback: 167 Jobs rows, no duplicate Job IDs, all earlier rows
present once, 6 jsearch + 4 jooble rows, their Sources rows OK, one Run Log row for the run, lock
released. Follow-ups: one jsearch row has a blank location and an odd company string (source
data, check the parser); Sources has 47 rows for 46 registry sources (likely the old adzuna row,
since the writer never deletes rows); a Sheets read quota (429) hit during readback cleared after
a minute; the Run Log status still reads `complete-with-source-failure` because `needs setup`
counts as non-OK.

**JobHunterEnv environment variables (names only, all verified set in a fresh session):**
`JOBHUNTER_SPREADSHEET_ID`, `JOBHUNTER_GOOGLE_AUTH_MODE`, `JSEARCH_API_KEY`, `JOOBLE_API_KEY`,
`LINKEDIN_LI_AT`, `X_AUTH_TOKEN`, `X_CT0`, `WAAS_SESSION_COOKIE` (Work at a Startup
`_bf_session_key`), `WAAS_SSO_KEY`, `YC_SSO_KEY`. Never print values. The env box warns values
are visible to environment users; settings reach only sessions started after saving. The cloud
image ships uv 0.11.32; install the pin with `python3 -m venv ~/uvvenv && ~/uvvenv/bin/pip install
uv==0.13.1`.

**User decisions recorded this session.** Adzuna skipped (paid-only, £8/month); removed from the
registry. Gmail uses the original plan: the dedicated job-alert account forwards job-alert senders to
the Gmail account connected to Claude, where a filter applies label `JobHunter`;
the user is doing the forwarding/filter setup (not yet verified). Real-sheet delivery is approved
for sources that pass their cloud test. PR grouping: low-risk sources bundled; LinkedIn and X each
get their own PR. The user asked to drop the fixed LinkedIn/X volume limits and wants a decision
after the research below.

**Open work, in order.**
1. Codex review of PR #13; record its sync evidence.
2. Work at a Startup (logged in): the site has far more jobs than the public YC page (157 startups
   with product roles vs 35 postings). Its list comes from an Algolia search keyed per session plus
   `POST /companies/fetch`. Inspecting those private requests from the user's logged-in tab was
   blocked by the host safety classifier ("exfiltration scouting"); do not retry that. The proposed
   route, pending the user's go-ahead, is a cloud headless browser that loads the page with the saved
   cookies and reads visible job cards only.
3. LinkedIn and X: same pending decision (headless browser with `li_at`; twscrape with
   `auth_token`/`ct0`). Research notes: there are no official LinkedIn limits; vendor guides suggest
   roughly 30-50 searches and about 100 profile views per day, spread out, with new accounts ramped
   slowly, and LinkedIn may invalidate `li_at` when requests come from a different country/IP than
   where it was issued (the cloud VM is not the user's home IP). X documents 429 on rate limits;
   no reliable public numbers for logged-in web search.
4. Gmail: verify the `JobHunter` label (read label names only), then build the alert parser.
5. Cosign: the correct URL is unknown (cosign.com is parked). School/MBA sites: the user must name
   them (mbaexchange.com is an admissions consultancy, not a job board).
6. Gmail connector settings: Delete label / Mark spam / Trash / Remove labels are "Always allow";
   recommend the user switch them to "Needs approval" before any unattended routine.
7. Daily routine (06:07 America/New_York) and its ROUTINE_PROMPT/CLOUD_RUNBOOK docs only after the
   sources are finished (user instruction: no guides for unfinished content).

**Lessons.** Never write a file with `open(p,'w')` before reading it (it truncated two docs once);
check `git diff --stat` before docs commits. When driving the user's Chrome, confirm the tab is
still the expected page before typing (a user tab once replaced the session tab).

## Post-merge review follow-up — October 18, 2026

An independent Codex review of merged main 36539f4 found three P2 source defects;
see reviews/2026-10-18-codex-postmerge-review.md. The original automated writer
cycle-3 review was usage-limited, and the later manual Codex report was not an
approval of the final revision. The final pre-merge confirmations below are
Claude reviews. The independent Codex report is explicitly post-merge.

Codex is fixing the findings on codex/fix-postmerge-review. Remote evidence from
Lever/WWR, durable discovery attribution/times and locally bound annual USD salary
amounts have regressions; 330 tests and 10 subtests pass offline. Fresh pushed-head
Claude review plus CI are required before the follow-up is merged. The user
explicitly requires opposite-agent review only: Codex reviews Claude's changes,
and Claude reviews Codex's changes. PR11 is Codex-authored; no Codex self-review
is pending or required.
The user's commit/merge/push authorization and unlimited repair-cycle direction
remain in force. Runtime/source-history/setup and deployment gates remain open.

## Current integration checkpoint — October 18, 2026

The user now explicitly directs "commit merge and push", superseding the earlier
local-only restriction for the reviewed repairs. Codex owns this integration.
PR #8 replaces #7; preserve its complete history, integrate #8, then retarget and
integrate #9 and #10 onto main after current checks pass. Close #7 as superseded.
Use normal merges and fast-forward branch updates; do not force-push.

All four discussed PRs received Claude reviews, including their previously pushed
heads. Final reviewed local implementation checkpoints:

- Writer: `52da0f1671fd780cfb9077bf4191e3fa36b4011a`, 160 tests/10 subtests.
  Claude report: https://github.com/rrpichardo/Jobhunter/pull/8#issuecomment-6246294366
- Evidence: `c11c4235c6375ddc969e51e0399ffb9b7650eb3e`; the evidence clarifications
  received a clean report before the reviewed writer ancestry was propagated:
  https://github.com/rrpichardo/Jobhunter/pull/9#issuecomment-6246161060
- Full source candidate: `5d20ae01f63f3dac42e4b4e9f94e4b920195caf2`, 304 tests/10
  subtests. Claude report:
  https://github.com/rrpichardo/Jobhunter/pull/10#issuecomment-6246318332

Those were static patch reviews, with local tests run separately by Codex. No
confirmed actionable findings remain. This documentation update records the new
integration authority; obtain pushed-head checks and reviewer acknowledgement.
Current-head live writer proof, the two lock-retaining live scenarios, durable
source history, remaining Gmail/social setup and scheduled production remain open.
Integration does not establish deployment. The material below is historical.

## Historical October 17 checkpoint

Handoff requested October 17, 2026. Codex is stopping implementation after this
checkpoint; Claude Code becomes the implementation owner when the user resumes
there. **V0 is not deployed; writer PR #7 is draft and must not be merged yet.**
Read AGENTS.md, PLAN.md, SETUP.md, ATTEMPTS.md and REVIEW_WORKFLOW.md first.

## Paste this into Claude Code

> Continue JobHunter from docs/CLAUDE_HANDOFF.md and current GitHub state. Take over
> as the sole implementation owner; do not restart completed work. Finish the
> outstanding PR #7 review repairs, obtain Codex review of the latest pushed SHA,
> and prove the writer in actual JobHunterEnv before requesting integration.
> Preserve the existing attempt/review counters. Keep all V0 sources, including
> logged-in LinkedIn and X, in scope. No local production dependency, new service,
> account, paid model API or billing upgrade. Explain progress in plain English.
> Never request or print secrets. Tests alone do not prove cloud deployment.

## Git and ownership

- Private repo: `rrpichardo/Jobhunter`. Main includes PR #4 bootstrap (7f77cb5),
  PR #5 harvest/extraction (`d77842dc91ebb236f959a3dc1702cbff561856d4`) and
  PR #6 proxy authentication (`fa899c32de3267507c51658274d5bc2509ef7193`).
- Current branch `codex/m0-sheet-sync`, draft PR
  https://github.com/rrpichardo/Jobhunter/pull/7 . Read its latest commits and
  `git status`; this handoff is committed with the checkpoint, so inspect HEAD
  rather than relying on a self-referential SHA in this file.
- For new Claude edits, create `claude/m0-sheet-sync` from this checkpoint and a
  replacement milestone PR against main, explicitly superseding #7. Carry its
  findings/counters forward, link both PRs, and close #7 only when the replacement
  preserves all work. Do not accidentally branch from older main and lose repairs.
- Opposite-agent review now works in both directions by repository instruction:
  Claude-authored work needs Codex review; see REVIEW_WORKFLOW.md. No self-review.
  Standing merge authorization expressly covers Codex-built milestones after
  current Claude review/tests/CI; other merges follow user direction.

## Current writer implementation and verification

Existing modules: sheet_records, sheet_io, sheet_lock, sheet_journal, sheets,
plus scripts/sheets_sync. Do not rebuild these from scratch. They provide keyed
Jobs upserts, preservation of Status/Notes/My rating/Date found, RAW writes,
bounded chunks, Sources/Run Log, hidden `_State` journal and structural global lock.

Latest local checkpoint: `.venv/bin/python -m pytest -q` → **125 passed,
10 subtests passed**. Locked rerun is recorded in ATTEMPTS.md. The previous
107-test head `4c9800ccd6882c3eb3573d35be62919d4de4fe07` passed Linux/Windows CI.
Current checkpoint requires fresh CI and reviewer coverage; an old green review
is not approval. No application writer has run in the cloud yet.

Claude Sonnet cycle-1 review of 4c9800c:
https://github.com/rrpichardo/Jobhunter/pull/7#issuecomment-6243645600 .
**Cycle 1 / 3 has been consumed; cycle 2 has not been requested.** Completing the
remaining first-cycle fixes before review does not reset the counter. PR #5's
one-off fourth-cycle authorization does not extend this milestone.

Repairs included in this checkpoint, still needing fresh independent review:

- Reject unsupported control characters/unpaired surrogates, canonicalize CRLF/CR
  to LF before journaling; reject whitespace in Job IDs.
- Journal validates only its own `m0/run/` values; unrelated numeric social counters
  no longer poison recovery.
- Every non-lock mutation atomically adds a fresh UUID receipt to global lock C1.
  After a transport/5xx/interrupt uncertainty, only matching owner + exact receipt
  confirms that request applied. Stale/missing/unreadable receipt retains lock
  and blocks all subsequent mutations, retries and deletion. HTTP 4xx except 408
  is treated as rejected; scrutinize this classification in review.
- Disable hidden transport retries, redirects and auth-refresh resubmissions.
  Preserve original exceptions/interrupts if release also fails; distinguish
  verified writes with unconfirmed lock release.
- Internal test namespace `_M0Test_[a-z0-9]{8,32}` maps the four data tabs to hidden
  prefixed tabs while keeping the global lock. Unit test only; no live harness yet.

## Next work, in order

1. Read the actual cycle-1 report and current diff. Complete the remaining fixes:
   manual-only poisoned-journal quarantine/recovery procedure (never silently
   discard work); avoid downgrading an already completed Run Log row to pending
   after a crash before journal.finish; add regression tests. The completed-run
   replay limitation is now documented. Per-run source evidence/history remains
   absent (Sources overwrites current rows); implement before full V0 acceptance.
2. Extend receipt tests for failed receipt read, definitive 429 rejection,
   interrupt through the engine, and delayed-before-apply outcomes. Current
   tests cover all three mutation stages, stale receipts and timeout-after-apply.
   Invariant: no later mutation/unlock when prior outcome is unknown. An old
   value already present does not prove a new request finished.
3. Run locked tests, push, request **Codex review** of the exact head (cycle 2/3)
   using REVIEW_WORKFLOW.md. Resolve issues and get current review/CI. Missing
   Codex access stays outstanding; a Claude Action reviewing Claude is insufficient.
4. **Done (c5e2398, cloud run exit 0; see V0_VERIFICATION.md): lock-retaining cases
   `timeout_before_apply`/`interrupt_before_apply` remain opt-in and un-run.**
   Original text: build a paced live test harness using a fresh hidden test namespace; reject
   any preexisting namespace initially, keep the global lock. No destructive
   fixture testing in real Jobs. Disable live social fetches. Test chunks,
   preservation of user fields, sorting between runs, timeout-after-apply,
   interrupt before/after Jobs, recovery and independent-process overlap. Retain
   hidden fixture tabs if cleanup cannot be proved safe. Pace requests to avoid
   Sheets per-user quotas; fail closed on unknown mutations. Do not auto-unlock.
5. **Done October 18, 2026 on code `c5e2398` with a fresh harvest (old data was lost):
   run `m0-real-001` and its repeat passed; see V0_VERIFICATION.md for scope and limits.
   This predates writer fix `e3536e4`; current-head live verification and scheduled
   M0 are still open.**
   Original text: in actual JobHunterEnv, write the already validated real posting, repeat its
   unchanged run ID, and inspect Jobs/Run Log evidence. Expand actual command
   output; an agent summary alone is insufficient. Then prove scheduled M0.
6. Continue full source groups, Gmail, LinkedIn/X, exact daily routine/runbook,
   06:07 America/New_York schedule and separate day-7/day-14 follow-ups. No routine,
   verified scheduled run or trial start dates exist yet.

## Actual Claude cloud evidence, not Codex cloud

Codex controlled Chrome Richard to select the repo and **JobHunterEnv** at
https://claude.ai/code/session_015wZ8bZKVEjazvzsqciHokQ . That is a manual Claude
cloud session, not a scheduled routine. Ubuntu24.04, Python3.12.3, uv0.13.1.
Local authenticated Claude Sonnet CLI reviews were separate development checks.

- Fresh Greenhouse probe at historical aaed72b: HTTP200, 655 valid, zero rejected,
  15 PM candidates, one selected; actual Claude excerpt validated by Python.
  Later checks replayed saved data, not new collection.
- PR #5 actual cloud: 65 tests/10 subtests; PR #6 actual cloud:71/10, clean tree.
  Cloud currently last tested at 229a97b, not the writer checkpoint.
- Scratchpad `/tmp/claude-0/-home-user-Jobhunter/bd94b49d-acc0-5310-ad78-3b3f143cc8cd/scratchpad`:
  `uvbin`, `venv`, `uvcache`; `m0dir2.txt` points to saved harvest/extraction,
  and normalized `records_0f7b436.json` has one posting. May disappear.
  Historical trusted harvest SHA256 (its scratch files were subsequently lost):
  `84423ba33cc8923e9cdfa6548da0da08f35b4e56bebce92def20f6be0ff49a8e`.
  Never regenerate the trust reference from a modified artifact. If missing,
  report loss and make a new bounded public harvest with independently retained hash.
  The approved replacement harvest used for `m0-real-001` has digest
  `d7849a78f6e81b637ef35dfeff9275a0be9c6180ab79b912311f8bcda33c7019`.
  See V0_VERIFICATION.md, "M0 real posting write in JobHunterEnv"; do not apply the
  old digest to that replacement or rely on the lost scratch paths above.

## Google setup: already completed; do not repeat

- Chrome profile Richard; dedicated jobs account selected and verified.
- Project `jobhunter-511923`; service account
  `jobhunter-sheets-writer@jobhunter-511923.iam.gserviceaccount.com`, no project
  IAM roles selected; Sheets API enabled. Workbook Restricted, owner plus writer
  Editor only; notification off.
- Workbook ID `1kG1QeLhYmiImPW4pMtEDIHI6I-dK1Ztig_77B8mGrPw`:
  https://docs.google.com/spreadsheets/d/1kG1QeLhYmiImPW4pMtEDIHI6I-dK1Ztig_77B8mGrPw/edit
- Saved JobHunterEnv GCP network secret, type “GCP access token (with Service
  Account Key)”. Host sheets.googleapis.com; path prefix `/v4/spreadsheets/`
  plus workbook ID; Sheets scope; Subject blank. Proxy injects token outside VM.
  No key/token file/env value is needed in Python. Non-secret environment:
  `JOBHUNTER_GOOGLE_AUTH_MODE=network-secret`, `JOBHUNTER_SPREADSHEET_ID=<ID above>`.
- Initial actual cloud read succeeded at0260388. At229a97b isolated hidden
  `_M0AuthProbe` (ID2026101801) atomic addSheet/updateCells and RAW literal
  `=jobhunter_probe_literal` readback all passed. Tab retained. This is endpoint
  compatibility only, not application recovery/locking proof. No real Jobs yet.
- Key was disclosed in chat. User explicitly authorized continued use of this
  specific dedicated key; rotation recommended, not a mandatory gate. Never copy
  its value into Git/logs/PRs/handoff. Do not inspect the local key or clipboard.
- Billing readback found JobHunter auto-linked to the existing free trial.
  **User explicitly chose “Leave the existing trial link unchanged.”** The
  disable-billing dialog was canceled and linkage rechecked. No billing setting
  was changed or upgrade made. Do not unlink, upgrade or ask again.

## Scope and attempt counters

- No new Cloudflare/hosting/account; user rejected that detour. No paid model API.
- Credential delivery/read access succeeded at attempt3/3. Write-endpoint proof
  succeeded at1/3. Persistent-state/concurrency and social-auth historical blockers
  remain2/3; read ATTEMPTS.md before counting a new distinct attempt. Do not reset.
- LinkedIn and X remain V0. Dedicated account/session setup is unverified. User
  completes local challenges and supplies dedicated cookies directly in settings.
  Cookie-compatible cloud MCP first if supported, then Playwright; no .mcp.json
  server exists yet. Daily source allowances in `_State`.
- Preserve existing Claude Gmail connector, read only forwarded JobHunter-labeled
  job alerts, never expand empty label to inbox/unrelated thread/security mail.
  Forwarding/label/connected identity remain unverified. Routine makes no Gmail writes.
- Unknown mutation recovery needs evidence that the server request has finished,
  plus reconciliation and stopped writers. A timer or stopped client is insufficient.
- Use cheaper models for bounded tasks; Astra helped the receipt-safety design.
  Announce parallel agents and keep them read-only while one agent implements.
