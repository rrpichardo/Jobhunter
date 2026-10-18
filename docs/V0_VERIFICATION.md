# V0 verification evidence

## Bootstrap prerequisite — October 17, 2026

Scope: reproducible installation and CI plus cloud readiness inventory. This is
an early prerequisite PR, **not completed M0** (thin source-to-Sheet + recovery),
and **not V0 deployment**.

Local macOS ARM64 checks used uv 0.13.1 and uv-managed Python 3.12.15:

```sh
uv lock
uv sync --locked
uv run --locked python -c "import bs4, feedparser, google.auth, gspread, httpx, yaml"
uv run --locked python -m pytest -q
```

Result: lock resolved; locked installation and all six runtime imports passed;
**6 tests and 10 subtests passed**. The tests are unchanged historical writer
examples, not production integration tests.

At implementation revision `e7c9c750e2f59f3e87e277fc0a39569337bcf873`:

- [Linux and Windows CI](https://github.com/rrpichardo/Jobhunter/actions/runs/39075258194)
  both passed locked installation, six runtime imports, and the complete suite.
- [Claude Code Sonnet review](https://github.com/rrpichardo/Jobhunter/pull/4#issuecomment-6242298543)
  found no actionable findings. It inspected the diff; it did not reproduce tests
  or cloud UI checks. This review does not cover subsequent documentation changes.

Live cloud evidence: the [bounded cloud session](https://claude.ai/code/session_015wZ8bZKVEjazvzsqciHokQ)
made one real Greenhouse request (HTTP 200, 655 jobs, one PM posting inspected).
The underlying command/output was expanded in the UI and verified. See
`CLOUD_CAPABILITIES.md` for the precise scope, runtime versions and unknowns.
This is a manual cloud probe, not a scheduled routine or application run.
No source-to-Sheet delivery, validated Claude extraction contract, Gmail read,
social collection, schedule, session restoration, or recovery evidence exists yet.
No trial start or day-7/day-14 review dates have been assigned.

Workbook setup: exact-title search found no existing workbook; the empty private
`Jobhunter V0` was created in the approved browser profile. Title, URL, Saved to
Drive, and private sharing status were read back from the UI. See `SETUP.md`.
Creation is setup evidence only; no application Sheet write has occurred.

## M0 source/extraction stage — local evidence

- `uv run --locked python -m pytest -q`: **43 passed, 10 subtests passed**.
- Tests first failed for missing modules, then passed after implementation.
- New synthetic-data tests cover deterministic public IDs, strict model excerpt
  validation, duplicate/unknown IDs, inert embedded instructions, explicit
  timeouts and bounded retries, Retry-After seconds/dates, source schema errors,
  empty vs failed source results, bounded sample/coverage metadata, and CLI
  roundtrip. Artifacts cannot overwrite files or be written inside the checkout.
- No new live source request, Claude extraction, Sheet write, or deployment is
  established by these tests. See the next PR for final revision/CI/review evidence.

### Actual cloud code-path test

Tested revision `f913601f36b329fcc81f3e84f31542277cfcffe6` in the existing
JobHunterEnv [cloud session](https://claude.ai/code/session_015wZ8bZKVEjazvzsqciHokQ).
This was a manual test of the proposed revision, not a deployed/scheduled run.

- Cloud installation used official uv 0.13.1 and Python 3.12.3. `uv sync --locked`
  passed; `uv run --locked python -m pytest -q` passed 43 tests and 10 subtests.
- One `python -m scripts.v0_harvest` run returned `OK: fetched=655 selected_for_m0=1`,
  exit 0. Saved metadata reports 15 PM candidates and complete-response coverage.
- Claude Sonnet selected a 23-word exact excerpt through the existing subscription
  and saved the extraction JSON. `python -m scripts.validate_extractions` returned
  `validated_records=1; Sheet delivery not attempted`, exit 0. Both application
  command outputs were expanded and inspected in the browser.
- Job ID: `greenhouse:anthropic:5434361008`; public
  [posting](https://job-boards.greenhouse.io/anthropic/jobs/5434361008).
- A tester-authored summary one-liner used `records` instead of `jobs` and failed
  after the validation CLI had succeeded. The corrected summary was read back;
  no application code/assertions were changed or live fetch repeated.
- Cloud working tree stayed clean. Artifacts were in a private ephemeral directory
  outside the checkout. This proves no cross-session persistence. No Sheet write,
  Gmail/social access, account setup, cookies, schedule or new service was involved.

### Review-fix verification

Fresh Claude review found actionable edge cases in the first revision. Regression
tests first reproduced the failures; the fixed full local suite passed **57 tests,
10 subtests**. Changes are listed in ATTEMPTS.md. The earlier live cloud check
above covers `f913601` only. Recheck the affected code using saved public payloads
and current cloud tests; do not imply the old cloud result covers new code.

Cloud recheck at `aaed72b23710873db4241fd6f8b048489b4a494c`: locked install and
57 tests/10 subtests passed in JobHunterEnv; one fresh harvest returned 655 valid,
0 rejected, 15 PM candidates, 1 selected, HTTP 200 after 1 attempt, complete-response.
Claude selected an exact excerpt; validation with the printed harvest digest
returned 1 complete record and exit 0. The actual command outputs were expanded
and inspected. No Sheet/Gmail/social/credential/scheduling actions were performed.

After review cycle 2, the full local suite passes **61 tests and 10 subtests**.
Binary artifact publication now makes digest bytes portable to Windows; server
schema/decode edge cases retain sanitized failure evidence. Final current-revision
review, Linux/Windows CI and cloud replay evidence will be linked from PR #5.

## M0 first-stage final integration and initial Google read access

PR #5 final head `0f7b43659a496c80a25079dd9107ccda1439e154` received fresh
Claude Code review with no unresolved actionable findings. Linux/Windows CI
passed; actual JobHunterEnv locked install and 65 tests/10 subtests passed.
Saved extraction validated against the original trusted digest: 1 record, exit 0.
No additional live source fetch. PR #5 merged as `d77842d`; main tests passed again.
See [final evidence](https://github.com/rrpichardo/Jobhunter/pull/5#issuecomment-6243315386).

The connection foundation at `02603884be0ba98b57094f100ba7eeb76d64b8a5` was
checked in the same actual JobHunterEnv cloud session after user-approved GCP
network-secret provisioning. Native copy/paste put the complete JSON directly
into that secret, without printing the key. The UI confirmed saved restricted
host/workbook path and non-secret configuration. No credential variable/file was
placed in the VM. Using gspread with AnonymousCredentials, `open_workbook(cfg)`
and `worksheets()` printed only `RESULT=success tab_count=1`, exit 0, exact HEAD,
and clean-tree status. Tool output was expanded and inspected. There was one
bounded connection attempt (two metadata reads), no write or retry.

This is initial cloud read-access proof, not successful write authorization,
write-path proxy compatibility, locking, recovery, a scheduled run, or deployment.
Writer tests and harmless write/readback/structural-endpoint checks remain required.
The user accepted continued use of the disclosed dedicated key; see SETUP.md.

## M0 writer live harness in JobHunterEnv — October 18, 2026

Scope: failure-injection and concurrency checks of the Sheet writer against Google,
using only fresh hidden `_M0Test_` fixture tabs and the shared lock tab. This is
**not** the real-posting write, not a scheduled run and not V0 deployment.

Actual Claude cloud session
https://claude.ai/code/session_01DsCkZnt2X9EtuQRVq6Gq5u (JobHunterEnv, branch
`claude/m0-sheet-sync`, HEAD `c5e2398`, clean tree). The container's uv was 0.11.32 and
the repo pins 0.13.1; with the user's approval uv 0.13.1 was installed with pip into a
scratch virtualenv outside the checkout. No tracked file or setting changed.

- `uv sync --locked` and `uv run --locked python -m pytest -q`: **154 passed,
  10 subtests passed** in the cloud.
- `uv run --locked python -m scripts.live_harness` (paced 1.5 s, eight clean scenarios,
  run in the background and read from the output file after it finished):
  **`summary: scenarios=8 failures=0`**, exit code 0, process not running afterwards.
  The expanded command output had 54 PASS lines and no FAIL line. Namespaces:
  `_M0Test_ea1312753eb7` (chunks), `d51081372f06` (repeat), `4bf8cc375569` (preserve),
  `d850038cd74a` (sorted), `dffa80a01b24` (timeout after apply), `7eb8b875924b`
  (timeout after structural apply), `48489e778b42` (interrupt after apply),
  `aa48b655cc1d` (overlap).
- Checked live: 40 jobs in 9 write requests with no duplicates and a complete Run Log
  row; same run ID rewrote nothing; a new run ID with unchanged data added no Jobs
  rows; changed data under an old run ID was refused (`run_id_payload_conflict`);
  user-edited Status/Notes/My rating/Date found survived a second sync and
  formula-looking text stayed literal; after rows were sorted by a user, a rerun
  updated each job by ID and notes stayed with their job; a timeout after Google had
  applied a cell write and after a structural change were both confirmed by the lock
  receipt and the sync completed; an interrupt after an applied write released the
  lock, kept the pending journal, and the rerun recovered it (`recovered=1`); two
  independent processes raced and exactly one won while the other reported
  `writer_locked`, with one Run Log row and no duplicate jobs. Every scenario ended
  with `no_writes_outside_namespace` and `lock_released` passing.
- **Not run on purpose:** `timeout_before_apply` and `interrupt_before_apply`, which
  deliberately leave the global lock in place. The harness never unlocks. Those cases
  remain covered only by unit tests. The eight fixture tabs were retained, hidden.
- **Not proven yet:** the real posting write and repeated-run readback in the real
  Jobs/Run Log, scheduled M0, per-run source history, and Codex review of the writer
  (cycle 3 / 3 requested for `99b1154`; Codex reported its usage limit, so no review
  of that revision has been delivered).
