# Claude Code continuation handoff

Updated October 17, 2026. Codex remains the active implementation owner; the user
chose to continue here after preparing this handoff. Read this first, then AGENTS.md, docs/PLAN.md,
docs/SETUP.md and docs/ATTEMPTS.md. This is an implementation handoff, not the
daily routine prompt. V0 is **not deployed**. Do not restart completed milestones.

## Resume instruction

> Continue JobHunter V0 from this handoff and the current Git state. Keep one
> implementation owner, preserve all existing changes, and check open PRs before
> coding. Production must run in Claude Code cloud JobHunterEnv. Use the existing
> subscription; no paid model API, new hosting service/account, or billing
> activation. Explain progress in plain English and announce parallel agents.
> Finish the earliest incomplete acceptance gate. Record bounded attempts and
> obtain current opposite-agent review before merging implementation. Never
> request secrets in chat. Do not call the application deployed until the actual
> cloud schedule, Sheet delivery and recovery gates pass.

## Repository and integration state

- Repository: `rrpichardo/Jobhunter` (private). Main includes PR #4 (`7f77cb5`)
  and PR #5 (`d77842dc91ebb236f959a3dc1702cbff561856d4`).
- PR #6 merged at `fa899c32de3267507c51658274d5bc2509ef7193`. Current writer
  work continues on `codex/m0-sheet-sync`; check for newer commits/open PRs.
- The connection checkpoint started on `codex/m0-sheet-writer`. Its initial commit is
  `4ebb680`; later handoff/review commits may follow. Inspect `git status`,
  `git log`, remote main and open PRs; do not assume this file is the latest SHA.
- PR #5 is merged: https://github.com/rrpichardo/Jobhunter/pull/5 . It implements
  one-board Greenhouse sampling and validated Claude excerpts only, with no
  writer, full eligibility, social integration, recovery or scheduling.
- The current change adds `jobhunter/google_auth.py` and tests: explicit
  `network-secret` mode, AnonymousCredentials for gspread, workbook-by-ID access,
  20-second timeout, sanitized failure. It is a connection foundation, **not a
  Sheet writer**. Initial cloud read and isolated structural/RAW endpoints are
  proven; full writer, locking, recovery and schedule remain unproved.
- User specifically requests all work committed/pushed, reviewed merges, and
  this ready-to-use handoff so Claude Code can continue when Codex runs out.
  Verify the current PR's status/review rather than treating this text as approval.
- When ownership transfers, stop the previous implementation owner. A Claude
  implementation branch uses `claude/`; do not have Codex and Claude edit together.

## Verified evidence and how it was launched

Production proof came from **Claude Code cloud**, not Codex cloud. Codex operated
Chrome's Richard profile, selected the repository and JobHunterEnv at
claude.ai/code, then submitted a bounded test prompt. Session:
https://claude.ai/code/session_015wZ8bZKVEjazvzsqciHokQ . It is a manual cloud
session, **not a scheduled routine**. Local Claude CLI was separately used for
read-only code review; local review is not cloud-execution evidence.

- Locked uv 0.13.1 / Python 3.12; Linux and Windows CI available. Local commands:
  `uv sync --locked` and `uv run --locked python -m pytest -q`.
- PR #5 final reviewed head `0f7b43659a496c80a25079dd9107ccda1439e154`:
  fresh Claude Code Sonnet review found no actionable issues; Linux/Windows CI
  passed. Actual JobHunterEnv locked install passed; 65 tests/10 subtests passed.
  Saved-data validation accepted the original trusted SHA and produced 1 record.
  Cloud command outputs were expanded and inspected in the UI; tree clean.
- Live Greenhouse request at earlier `aaed72b`: HTTP 200, 655 valid jobs,
  0 rejected, 15 PM candidates, 1 selected. Claude supplied an exact excerpt;
  Python validated it. Later replay used saved data, not another live request.
- The connection foundation's local locked suite passes 71 tests/10 subtests.
  These use mocks; see the separate live read-access evidence below.
- Saved cloud artifacts may disappear; don't rely on their persistence. The
  session scratchpad contains `m0dir2.txt` pointing at the saved harvest and
  extraction directory. Its original trusted harvest SHA-256 is
  `84423ba33cc8923e9cdfa6548da0da08f35b4e56bebce92def20f6be0ff49a8e`.
  Never recompute a trusted reference from an edited artifact. If gone, report
  that and run a new bounded public harvest with a new independently retained hash.

## Immediate Google setup — saved secret and successful read access

- Correct local Chrome profile: **Richard**. The user selected the existing
  dedicated jobs Google account. Its Cloud console works; an earlier account was
  closed to Cloud access. Do not switch back or inspect unrelated mail/accounts.
- Dedicated project and writer service account created. No project IAM roles
  were selected. Sheets API enabled. No billing account was selected during
  project creation; actual billing status has not been independently verified.
  Do not activate/upgrade billing. The account already displayed a free trial.
- Workbook: `1kG1QeLhYmiImPW4pMtEDIHI6I-dK1Ztig_77B8mGrPw`.
  https://docs.google.com/spreadsheets/d/1kG1QeLhYmiImPW4pMtEDIHI6I-dK1Ztig_77B8mGrPw/edit
- Dedicated identity:
  `jobhunter-sheets-writer@jobhunter-511923.iam.gserviceaccount.com`.
  User confirmed Editor access only to this workbook, notifications off. UI
  confirmed sharing. No application data/tabs/writes have been made.
- User explicitly approved downloading its JSON key and later directed the agent
  to use it. Agent privately opened only that approved file for direct copy/paste
  into the protected secret field; no contents were printed or put in Git. Do not
  inspect unrelated Downloads files, clipboard contents or environment dumps.
- **User-approved key exception:** the key was disclosed in chat. User explicitly
  accepted this and directed using it for this setup. Replacement was recommended
  but is not a mandatory gate under that direction. Do not repeat key contents
  in Git, logs, PRs or this handoff. The agent transferred the complete JSON
  directly through native copy/paste without printing it, saved the GCP network
  secret, and closed the editor. Never read the clipboard or local key for logs.
- The preferred GCP secret type **exists**. Earlier disabled Add secret evidence
  is superseded. Actual menu: Add secret → GCP access token (with Service Account
  Key) → GCP service account key JSON. The key belongs in that field, **not**
  Setup script. The approved secret is now saved; UI showed its restricted
  host/workbook path with Replace/Delete controls, with no secret value shown.
- The saved secret uses these non-secret restrictions: host `sheets.googleapis.com`; path prefix
  `/v4/spreadsheets/1kG1QeLhYmiImPW4pMtEDIHI6I-dK1Ztig_77B8mGrPw`;
  scope `https://www.googleapis.com/auth/spreadsheets`; Subject empty. Verify
  non-secret saved status only while the secret field is closed.
- Avoid printing/screenshotting secret contents. User expressly authorized the
  agent to use this existing key for setup; direct private transfer is permitted.
  Do not treat that as general authorization to publish or commit credentials.
- Claude docs say the network proxy mints/injects tokens after requests leave
  the VM; the key stays outside the VM. The current Python candidate uses
  `gspread.Client(auth=AnonymousCredentials())`; read access succeeded. Write-path
  compatibility passed an isolated hidden-tab test; application behavior remains
  unproved. See the latest ATTEMPTS.md entries.
- Non-secret config has been saved: `JOBHUNTER_GOOGLE_AUTH_MODE=network-secret` and
  `JOBHUNTER_SPREADSHEET_ID` set to the ID above. Existing sessions may need a
  fresh session for changed environment variables. Don't dump environment values.
- Initial live test completed in actual JobHunterEnv at `0260388`: the helper
  opened only this workbook and worksheets() returned `tab_count=1`, exit 0,
  clean tree. Command output was expanded and inspected. No key/token or raw
  response was printed. This proves read access only, not writer readiness.
- If the preferred secret type proves incompatible, the user already approved
  an in-memory credential-variable fallback, narrowly scoped to this workbook.
  It is a fallback, not a reason to skip testing the preferred supported secret.

## Next implementation gates

Follow `docs/superpowers/plans/2026-10-17-m0-sheet-writer.md` and the binding plan:

1. Read and isolated structural/RAW write/readback endpoints are proven. Finish
   the writer and its live recovery/lock checks; endpoint proof is not concurrency
   or application proof. Implement safe Jobs upserts keyed by
   Job ID, RAW writes, chunking, header/duplicate checks and readback. Preserve
   Status, Notes, My rating and original Date found on existing rows. Sampling
   records are not eligibility decisions.
2. Journal normalized pending work in Sheet `_State` before mutation. Reconcile
   ambiguous append outcomes by rereading IDs, never blind append retry. Add
   Sources and Run Log evidence; no raw email/cookies in state.
3. Enforce/prove one writer. Candidate: atomic Sheets batch adds hidden
   `_JobHunterLock` with fixed unique sheet ID/title plus unique owner token cells
   in the same batch. Owner-confirming read after ambiguous acquire; no stealing
   or automatic expiration. Release once; don't retry ambiguous delete. Google
   documents atomic batches and uniqueness failures, but contention safety is
   an inference needing live overlap proof. It only serializes compliant clients;
   manual deletion/tampering requires stopping all owners before recovery.
4. Test stop-after-extraction, stop-after-write, write-success-but-timeout,
   overlap, sorting between runs, multiple chunks, repeat sync/no duplicates,
   user-column preservation and source failure. Use sanitized saved data for
   repeated tests, not repeated live social collection.
5. Complete real M0 source→Claude extraction→Python→Sheet→Run Log, restart/recovery
   and a scheduled routine. Then integrate the remaining source groups, including
   LinkedIn and X; don't quietly reduce V0 scope to Greenhouse/email.
6. Deliver exact `docs/ROUTINE_PROMPT.md`, `docs/CLOUD_RUNBOOK.md`, source inventory,
   verified 06:07 America/New_York schedule and separate day-7/day-14 follow-ups.
   No routine or trial dates exist yet.

## Scope, permission and counter reminders

- No Cloudflare/new hosting work: user rejected that direction as outside scope.
  No paid services, paid model API usage or billing activation.
- LinkedIn and X remain V0. Dedicated accounts not verified as created. User logs
  in locally and completes challenges; cookies go directly into JobHunterEnv.
  Restore temporary cloud sessions; non-secret allowances/state in `_State`.
  LI cookie-compatible MCP first if supported/pinned/configured, then read-only
  Playwright. No `.mcp.json` server is configured. X twscrape needs stop-rule fixes.
- Stop immediately on social challenge/429; no bypass or same-day retry. At most
  one social attempt/day in America/New_York; LI <=5 searches/50 details, X <=10
  queries/200 posts. Missing setup remains outstanding, never successful zero.
- Preserve existing Claude Gmail connector. Only forwarded JobHunter-labeled job
  alerts; no unrelated thread messages, security mail or broadened empty search.
  Forwarding/label/connected identity remain unverified. One-time setup allowed;
  operational Gmail writes are forbidden.
- Read the full ATTEMPTS.md. Credential delivery/read access succeeded on attempt
  **3/3** after GCP secrets became available. Persistent-state/concurrency and
  social-auth remain at **2/3**; don't reset counters. GCP access attempt 1 is
  resolved by the selected account. PR #6 is at review cycle 2/3 for the current
  fixes; check its latest head/review/merge state before continuing.
  PR #5 exhausted 3 cycles, then user authorized exactly one fourth cycle, now
  completed/merged. That extension does not apply to new milestones.
- New milestones have the normal three-cycle cap. Obtain a current opposite-agent
  review; a green GitHub Claude review job may have skipped because of old
  comments/draft state. Post actual review text and exact revision evidence.
- Standing merge authorization exists after applicable tests/CI and latest Claude
  review pass with actionable issues resolved. Never bypass branch protections or
  merge unreviewed code. For Claude-authored changes obtain Codex review.

## Active writer implementation checkpoint

The user chose to continue with Codex. PR #6 is merged at fa899c3; the active branch
is codex/m0-sheet-sync. The initial writer commit is 25b62e7 (later bookkeeping and
review fixes may follow). Do not recreate these modules: sheet_records, sheet_io,
sheet_lock, sheet_journal, sheets and scripts/sheets_sync now exist. The full local
suite passes 107 tests/10 subtests. See M0_WRITER_RUNBOOK.md and the updated writer
execution plan. The first current-head Claude review is cycle 1/3; live application
write/recovery/overlap checks remain outstanding. Endpoint-only proof is not that
application proof. Resume at review findings and cloud verification, not from zero.
