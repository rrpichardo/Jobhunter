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
examples, not production integration tests. Linux and Windows evidence and the
reviewed revision will be recorded after CI and Claude review.

Live cloud checks: only configuration UI inspected so far, as recorded in
`CLOUD_CAPABILITIES.md`. No real source-to-Sheet, live extraction, Gmail read,
social collection, schedule, session restoration, or recovery evidence exists yet.
No trial start or day-7/day-14 review dates have been assigned.
