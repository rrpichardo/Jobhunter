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
