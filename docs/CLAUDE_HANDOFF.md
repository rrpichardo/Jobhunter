# Claude Code continuation handoff

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
5. In actual JobHunterEnv, write the already validated real posting, repeat its
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
  Trusted original harvest SHA256:
  `84423ba33cc8923e9cdfa6548da0da08f35b4e56bebce92def20f6be0ff49a8e`.
  Never regenerate the trust reference from a modified artifact. If missing,
  report loss and make a new bounded public harvest with independently retained hash.

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
  server exists yet. X twscrape still needs stop-rule fixes. On challenge/429 stop
  immediately, never bypass or retry that day. Daily source allowances in `_State`.
- Preserve existing Claude Gmail connector, read only forwarded JobHunter-labeled
  job alerts, never expand empty label to inbox/unrelated thread/security mail.
  Forwarding/label/connected identity remain unverified. Routine makes no Gmail writes.
- Unknown mutation recovery needs evidence that the server request has finished,
  plus reconciliation and stopped writers. A timer or stopped client is insufficient.
- Use cheaper models for bounded tasks; Astra helped the receipt-safety design.
  Announce parallel agents and keep them read-only while one agent implements.
