# Search coverage audit — parallel test only

**Status (October 27, 2026): TEST EXPERIMENT.** This branch does not schedule or modify the existing 6:00 AM America/New_York ChatGPT task. No GitHub/Codex routine is scheduled by this change, and the code does not contact employers, retrieve jobs, or apply.

## What is here

- `scripts/coverage_audit.py`: standalone standard-library Python that compares *supplied, real search observations* across primary, MBA, functional, employer-category, secondary, and evergreen searches.
- `tests/test_coverage_audit.py`: nine deterministic regression tests, runnable offline.
- No changes to Jobhunter collectors, its existing Google Sheet, secrets, schedules, or resume assets.

### Run the isolated code test

```bash
python -m unittest discover -s tests -p 'test_coverage_audit.py' -v
```

The existing `.github/workflows/checks.yml` already runs Python tests when a pull request opens. Review those checks before merging; per `AGENTS.md`, obtain independent Claude Code review of the exact branch head. **Do not merge** this experiment based only on offline tests.

## Why it is not a second job search yet

The Python script takes a JSON input containing:
- `searches`: search IDs, method names, and the queries actually executed.
- `observations`: jobs actually discovered, each linked to a search ID and source URL, with separately reviewed fit, employer status and application history.

Without that input, there is nothing meaningful to audit. The existing ChatGPT task does not automatically deposit a query-level ledger into GitHub, and this branch does not install a bridge. Running Python on a timer **alone** will not detect missed jobs from the ChatGPT search.

A future independent GitHub/Cloud run can gather its own observations, then execute:

```bash
python scripts/coverage_audit.py --input /private/observations.json --output /private/audit.json --markdown /private/audit.md
```

Keep private run files **outside** the checkout, consistent with `AGENTS.md`. Do not check application histories, cookies, keys or private output into Git.

## Decision boundary

**Keep the ChatGPT 6:00 AM job scan unchanged and enabled.** Test this independent audit first, then connect a proven source of query-level observations. Any later independent recurring cloud schedule requires explicit configuration, verified runtime access, and separate permission; it will not replace the ChatGPT scan without a new user instruction. The code does not prove internet-wide recall or employer verification: it reports overlap among *recorded* observations only.
