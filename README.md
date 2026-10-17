# JobHunter

JobHunter is being built as a daily Claude Code cloud routine. Google Sheets
will hold the jobs and user notes. **It is not deployed yet.** See
[the product plan](docs/PLAN.md) and [setup status](docs/SETUP.md).

## Development setup

Install [uv 0.13.1](https://docs.astral.sh/uv/getting-started/installation/),
then run these commands from this checkout on Linux, Windows, or macOS:

```sh
uv sync --locked
uv run --locked python -c "import bs4, feedparser, google.auth, gspread, httpx, yaml"
uv run --locked python -m pytest -q
```

uv installs Python 3.12 when needed. Commit dependency changes together with
`uv.lock`; normal installations must use `--locked`. CI repeats installation,
runtime imports, and the complete current offline suite on Linux and Windows.

The application is not packaged yet. The current tests under `review_probe/`
exercise a historical in-memory writer example. Passing them proves neither a
production Sheet writer nor source access, recovery, or cloud deployment.
Scripts under `scripts/` are historical experiments, not production commands.

Social dependencies and JobSpy are not installed or enabled by this bootstrap.
They need separate tested extras and cloud authentication before collection.
No direct paid model API is used.

Keep credentials, email, browser profiles, and session/recovery data outside this
checkout. Local development is permitted; daily production must run entirely
in Claude's cloud. Read [AGENTS.md](AGENTS.md) before changing the repository.
