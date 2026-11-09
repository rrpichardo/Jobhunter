# Search coverage audit — parallel test only

**Status (October 27, 2026): TEST EXPERIMENT.** This branch does not schedule or modify the existing 6:00 AM America/New_York ChatGPT task. No GitHub/Codex routine is scheduled by this change, and the code does not contact employers, retrieve jobs, or apply.

## What is here

- `scripts/coverage_audit.py`: standalone standard-library Python that compares *supplied, real search observations* across primary, MBA, functional, employer-category, secondary, and evergreen searches.
- `tests/test_coverage_audit.py`: deterministic regression tests, runnable offline (the original nine, plus one or more per finding of the Claude review of `87578ef`).
- No changes to Jobhunter collectors, its existing Google Sheet, secrets, schedules, or resume assets.

### Run the isolated code test

```bash
uv run --locked python -m pytest tests/test_coverage_audit.py -q
```

The existing `.github/workflows/checks.yml` already runs Python tests when a pull request opens. Review those checks before merging; per `AGENTS.md`, obtain independent Claude Code review of the exact branch head. **Do not merge** this experiment based only on offline tests.

## Why it is not a second job search yet

The Python script takes a JSON input containing:
- `searches`: search IDs, method names, and the queries actually executed.
- `observations`: jobs actually discovered, each linked to a search ID and source URL, with separately reviewed fit, employer status and application history.

Without that input, there is nothing meaningful to audit. The existing ChatGPT task does not automatically deposit a query-level ledger into GitHub, and this branch does not install a bridge. Running Python on a timer **alone** will not detect missed jobs from the ChatGPT search.

A future independent GitHub/Cloud run can gather its own observations, then execute:

```bash
uv run --locked python -m scripts.coverage_audit --input /private/observations.json --output /private/audit.json --markdown /private/audit.md
```

Keep private run files **outside** the checkout, consistent with `AGENTS.md`. The command never overwrites an existing file: if `--output` or `--markdown` already exists, or its folder is missing, it stops before doing any work (exit 2). Do not check application histories, cookies, keys or private output into Git.

## Decision boundary

**Keep the ChatGPT 6:00 AM job scan unchanged and enabled.** Test this independent audit first, then connect a proven source of query-level observations. Any later independent recurring cloud schedule requires explicit configuration, verified runtime access, and separate permission; it will not replace the ChatGPT scan without a new user instruction. The code does not prove internet-wide recall or employer verification: it reports overlap among *recorded* observations only.

## How the audit decides (after the review fixes)

- **Same job:** one requisition id is one job; links are compared with the project's own `jobhunter/job_identity.py` (so `boards.greenhouse.io/acme/jobs/123?gh_src=x` and `job-boards.greenhouse.io/acme/jobs/123` are one job). Different requisitions are never merged. A sighting with only a link that several requisitions share is kept apart and marked `ambiguous_link`, never guessed. The answer does not depend on the order of the input. Companies are matched by normalised name, so "Acme" and "Acme Inc" are two companies.
- **Actionable:** a strong-fit role is `actionable_strong` only when it is verified open, its application history is verified as not applied (`not_applied_verified`), and its eligibility is `confirmed_eligible`. `applied` and `company_receipt_unconfirmed` (sent, no receipt) both exclude a role.
- **Needs a human check:** a strong, verified-open role whose application history or eligibility is unknown (including an omitted field) is listed in `needs_check` with the reasons, and is **not** counted as actionable. Unknown is never treated as a go-ahead.
