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
