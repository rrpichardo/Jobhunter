# JobHunter

JobHunter is being built as a daily Claude Code cloud routine. Google Sheets
will hold the jobs and user notes. **It is not deployed yet.** See
[the product plan](docs/PLAN.md) and [setup status](docs/SETUP.md).
For continuation in Claude Code, start with [the current handoff](docs/CLAUDE_HANDOFF.md).

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
The `scripts/try_*.py` files are historical experiments, not production commands.

Social dependencies and JobSpy are not installed or enabled by this bootstrap.
They need separate tested extras and cloud authentication before collection.
No direct paid model API is used.

Keep credentials, email, browser profiles, and session/recovery data outside this
checkout. Local development is permitted; daily production must run entirely
in Claude's cloud. Read [AGENTS.md](AGENTS.md) before changing the repository.

## M0 source/extraction stage

This stage samples one public Greenhouse PM posting. It does not implement full
eligibility, all V0 sources, or Google Sheets delivery. Run from the repo root:

```sh
uv run --locked python -m scripts.v0_harvest --output /protected/run/harvest.json
uv run --locked python -m scripts.validate_extractions \
  --harvest /protected/run/harvest.json \
  --harvest-sha256 <digest-printed-by-harvest> \
  --extractions /protected/run/extractions.json \
  --output /protected/run/records.json
```

Use new absolute paths outside the checkout in an existing private directory.
On Windows use equivalent absolute paths. Commands never overwrite existing
artifacts. Use a private directory with appropriate permissions/ACLs; intermediate
files may be ephemeral. Production pending normalized work must be saved in Sheet
`_State` by the upcoming writer. The temporary directory is not persistent storage.
Follow [the cloud excerpt prompt](docs/M0_EXTRACTION_PROMPT.md) to produce the
Claude JSON through the existing subscription. Never manually label test data as
a live model result. Python validates quotations and derives record fields.
