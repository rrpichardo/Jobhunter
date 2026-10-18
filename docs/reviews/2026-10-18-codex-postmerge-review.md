# Post-merge Codex review of Jobhunter

Review date: 2026-10-18 UTC. Reviewer: this Codex session, independently reading and testing the checkout; not the GitHub Codex bot. This report was created **after** PRs #8–#10 had merged. It neither establishes a pre-merge Codex review nor retroactively supplies one.

**Verdict: changes needed. Three confirmed P2 defects remain in the reviewed implementation. This is not an approval.** The existing offline suite passes, but does not cover these scenarios. No confirmed P0/P1 defect, user-owned-cell overwrite, duplicate append from an uncertain mutation, unsafe automatic lock release after an unknown mutation, or credential disclosure was found in the paths reviewed. That statement is bounded by the offline scope below.

Reviewed cumulative change:

- Base: `fa899c32de3267507c51658274d5bc2509ef7193`.
- Head: `36539f47ee6c550c9cf5e2f521831a17ad13f16c`.
- Both refs resolved to those exact full SHAs. HEAD matched the reviewed head before and after checks. `git status --porcelain=v1` was empty before and after review. No tracked files were changed.

## Confirmed actionable findings

### 1. P2 — Preserve the discovery sources of duplicates merged in the same harvest

Primary location: `jobhunter/sheet_records.py:112–113` (`_discovery_details`); originating representation: `jobhunter/postings.py:497–498`.

Concrete scenario: Greenhouse and Remotive return the same verified Greenhouse requisition in one harvest. `dedupe` keeps the Greenhouse posting and puts `Also listed by: remotive` in its details. The next harvest returns only the Greenhouse posting. `_discovery_details` reads only `First seen by ...` lines; when the surviving row's source has not changed and no such history exists, it returns the incoming details and discards the previous `Also listed by` attribution.

Impact: normal successful daily updates erase a previously verified discovery source. The original merge also does not retain its first-seen date. This breaks the requirement to preserve all discovery sources and their first-seen times, undermining overlap and source-yield comparisons. The safe identity merge and user-owned cells are not the problem; the merged provenance is lost.

Reproduction evidence: reproduction 1 in `/workspace/scratch/jobhunter-review-repro.py` calls the actual `dedupe`, `to_row`, and `sync_jobs` implementations with an in-memory store. Day 1 persisted:

```text
Source: https://job-boards.greenhouse.io/acme/jobs/123
Evidence: Build AI.
Also listed by: remotive
```

After a new run containing the unchanged direct posting only, the persisted details became:

```text
Source: https://job-boards.greenhouse.io/acme/jobs/123
Evidence: Build AI.
```

The script asserts that `remotive` disappeared and passes. Store all discovery-source/date entries at the initial merge and union that structured history on every later update; add a regression spanning both runs.

### 2. P2 — Carry explicit remote evidence through the Lever and WWR parsers

Primary location: `jobhunter/postings.py:221–223` (`parse_lever`). The same omission exists at `jobhunter/postings.py:320–322` (`parse_wwr_rss`). The resulting exclusion happens at `jobhunter/postings.py:156–157`.

Concrete scenario: a valid Lever posting has title `Product Manager, AI`, location `Colombia`, description `Build AI.`, and explicit `workplaceType: remote`. `parse_lever` ignores that field and leaves `Posting.remote=False`. Because its location string itself does not say remote and its salary is blank, `ai_pm_match` rejects it. A WWR remote-product feed entry with region `Colombia` likewise receives `remote=False`, despite the remote-only source contract, and is rejected.

Impact: remote Latin/South American roles are silently dropped contrary to the user's policy to keep them regardless of salary. The same remote evidence is also missing from the saved row's work-mode details. This is loss of supplied evidence, not a request to infer permission or resolve an ambiguous location.

Reproduction evidence: reproduction 2 in the standalone script parses both complete synthetic source records and calls `ai_pm_match`. Actual results:

```text
Lever workplaceType=remote, location=Colombia: remote= False match= False
WWR remote-only source, region=Colombia: remote= False match= False
```

Both should be retained under the collection policy. Propagate the explicit remote field/source contract while preserving the original location; do not treat absent metadata as proof of remote work. Add parser-to-filter regressions.

### 3. P2 — Do not treat unrelated numbers in salary text as an annual USD salary

Primary location: `jobhunter/postings.py:139–143` (`regional_salary_match`).

Concrete scenario: a Colombia on-site posting supplies salary text `USD 50,000 - 60,000 per year + 401k`. The function checks that USD and an annual token occur somewhere, then extracts every number and interprets the benefit token `401k` as 401,000. It therefore accepts the role even though the only stated salary range tops out below USD 70,000.

Impact: on-site/hybrid regional roles enter collection without an explicitly qualifying annual USD salary range, violating the new country/salary exception. An unrelated amount or benefit cannot establish that exception. This is a collection-filter error; the current path does not claim full employer eligibility.

Reproduction evidence: reproduction 3 in the standalone script calls both relevant functions and obtains:

```text
'USD 50,000 - 60,000 per year + 401k' salary match= True Colombia onsite accepted= True
```

Parse amounts bound to the annual USD salary expression instead of taking the maximum of every number in the text; leave ambiguous additional figures unresolved. Add a regression for benefits/bonus figures alongside a below-floor salary range.

## Verification actually performed

From `/workspace/Jobhunter`, with Python 3.12.14:

```sh
/tmp/jobhunter-review-tools/bin/uv run --locked --cache-dir /tmp/jobhunter-uv-cache python -m pytest -q
```

Result: **304 passed, 10 subtests passed in 0.73s**, exit 0. This was run independently, not copied from an earlier report.

```sh
/tmp/jobhunter-review-tools/bin/uv run --locked --cache-dir /tmp/jobhunter-uv-cache python /workspace/scratch/jobhunter-review-repro.py
```

Result: exit 0; all assertions for the three findings above passed. Reproduction 4 separately confirms the already-documented per-source-history limitation below; it is not counted as a new finding.

```sh
git diff --check fa899c32de3267507c51658274d5bc2509ef7193 36539f47ee6c550c9cf5e2f521831a17ad13f16c
git status --porcelain=v1
git rev-parse HEAD
```

Result: diff check exit 0, empty status, exact reviewed HEAD. Tests and reproductions used fixtures/in-memory stores, with no live source calls or Google writes.

## Scope actually read

Required instructions read in full before review: `AGENTS.md`, the full 463-line `docs/PLAN.md`, `docs/REVIEW_WORKFLOW.md`, and `CLAUDE.md`.

Changed implementation read: `jobhunter/google_auth.py`, `jobhunter/job_identity.py`, `jobhunter/postings.py`, `jobhunter/sheet_io.py`, `jobhunter/sheet_journal.py`, `jobhunter/sheet_lock.py`, `jobhunter/sheet_records.py`, `jobhunter/sheets.py`, `scripts/live_harness.py`, `scripts/sheets_sync.py`, `scripts/source_probe.py`, and `sources/v0_sources.yaml`. Supporting `jobhunter/records.py` was also read to check URL validation and normalized-record contracts.

Corresponding changed tests/fakes read: `tests/fake_workbook.py`, `tests/sheet_fakes.py`, `tests/test_cross_source_sync.py`, `tests/test_google_auth.py`, `tests/test_live_harness.py`, `tests/test_postings.py`, `tests/test_sheet_io.py`, `tests/test_sheet_journal.py`, `tests/test_sheet_lock.py`, `tests/test_sheet_records.py`, `tests/test_sheets.py`, `tests/test_sheets_cli.py`, and `tests/test_source_probe.py`. The full repository test suite was run, including unchanged tests not individually rereviewed.

Additional documentation read: `docs/M0_WRITER_RUNBOOK.md` and `docs/V0_VERIFICATION.md`. This was a review of the cumulative implementation, not an audit of every historical documentation edit or every prior review conversation. I did not use the earlier manual report's findings as review conclusions.

The writer review checked RAW writes, column ownership, Date found preservation, reordered headers/rows, canonical requisition reconciliation, bounds and retry behavior, receipt confirmation, sticky unknown mutation state, lock acquisition/release, pending payload validation, hashes/chunks, recovery, completed-run behavior, and quarantine retirement. Static inspection and existing tests support those paths, but do not prove every external provider/runtime behavior.

## Accepted limits and outstanding gates, not new findings

- The eight-detail-page/source and 150-job global caps are accepted partial coverage. AI signals beyond the inspected detail budget remain unexamined.
- Multiple conflicting existing verified identities require operator reconciliation; uncertain generic links remain separate with review notes. No title/company-only merge was requested.
- The current configured parsers emit configured source IDs. I did not elevate a hypothetical future parser/schema mismatch to a bug.
- Conservative handling of ambiguous regional place/state codes is accepted. No inference of US permission or full eligibility is warranted by collection.
- Durable per-run source history remains explicitly documented as absent before full V0 acceptance. Reproduction 4 confirms that a later source success overwrites its prior `http_429` evidence in Sources, while completed journal chunks have been cleared and Run Log retains only the general failure status. This is an existing open gate, not a newly discovered integration defect.
- Listing-only/unconfigured sources, scheduling, current-head live verification, session restoration, and the day-7/day-14 observation process remain separate runtime/product gates. Historical cloud evidence covers only the revisions it names.

## Review limits

No source, Google, GitHub, connector, social, or external-user tool calls were made. No credentials, cookies, environment contents, or secret files were inspected. No pushes, merges, deployment, external posting, or tracked-file edits occurred. Only this report and a standalone reproduction script outside Git were written. Offline tests cannot establish live source access, Google/proxy behavior, scheduler concurrency, current-head cloud deployment, or trial completion.

Optional improvements and unverified hypotheses are not counted as findings. The three P2 items are concrete reproduced defects; fix them, run the affected regressions and full suite, and review the exact resulting pushed head before describing that revision as approved.


## Follow-up implementation

The follow-up branch adds permanent regressions in tests/test_postings.py and
tests/test_cross_source_sync.py for these findings. The report above remains a
changes-requested review of the exact old main SHA, not approval of its fixes.
The new branch requires fresh reviews and checks before integration.
