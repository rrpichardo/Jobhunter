# JobHunter

A daily job-lead collector for one person's MBA job search. It reads many public job
sources, keeps only roles that match strict personal rules, and writes them to a Google
Sheet that doubles as a lightweight CRM. **It is not deployed yet** (no daily schedule
exists); it has run for real by hand once.

## About this project (read this first if you are new)

### What it is and who it is for

JobHunter exists for one user: an MBA student graduating in **May 2027** who wants a
daily, trustworthy list of roles worth applying to. Doing this by hand means opening
dozens of boards, newsletters and social feeds and re-reading the same postings. JobHunter
does the collecting, filtering and de-duplication, and leaves the judging and applying to
the person. The owner is non-technical and is learning to code, so every report and doc
should be in plain language.

### How one run works

1. **Pick the window.** `scripts.run_window` says how many days back to look: 28 for the
   one-off first pull, 3 for daily runs. A daily run refuses to start after a gap longer
   than 2 days 6 hours, so no postings fall into a hole.
2. **Collect.** `scripts.source_probe` visits every source in `sources/v0_sources.yaml`
   and builds one delivery file. It never writes to the Sheet.
3. **Read free text (only where needed).** Messy sources (Hacker News comments,
   newsletters, X and LinkedIn posts) go to a Claude **Haiku** subagent inside the same
   cloud session. Python then accepts a fact only if it appears **word for word** in the
   source text, and Python, not the AI, builds the Job ID, the date and the fallback link.
   Which source uses which method is in [docs/SOURCES_HOW_READ.md](docs/SOURCES_HOW_READ.md).
4. **Filter.** One shared set of rules (below) keeps or drops each job, and every drop has
   a printed reason (`trace:` lines, mapped in [docs/TRACEABILITY.md](docs/TRACEABILITY.md)).
5. **Deliver.** `scripts.sheets_sync` writes new jobs to the Sheet in paced batches
   (150 rows, 45 s apart, to stay under Google's quota), with a lock, a recovery journal and
   a read-back check. Re-running adds nothing new.

### What counts as a match

- **Roles:** product management, chief of staff, leadership/MBA rotation programs,
  strategy manager/lead/director, entrepreneur- or founder-in-residence, project
  management, and forward-deployed/AI-deployment strategist. Interns, product marketing and
  product design are excluded (`jobhunter/postings.py`).
- **MBA 2027 rule (new in PR #53):** a role is collected only when the posting itself says
  it is for **MBA students or graduates of 2027**. "MBA preferred" is not enough, and
  new-grad-2027 roles that never mention an MBA are dropped (`class_2027_without_mba`).
- **Pay:** United States (including remote from the US) at least **USD 140,000** a year;
  Latin America at least **USD 70,000**. On-site or hybrid Latin America means Colombia or
  the Dominican Republic only. **Missing pay is "unresolved", never a match.**
- **Unknown stays unknown:** nothing is dropped or accepted on a guess. Uncertain items are
  kept and flagged.

### Where the data lives

One Google Sheet is the database. Tabs: `Jobs` (one row per job, with every source and its
first-seen date kept when duplicates merge), `Sources` (health of each source), `Run Log`
(one row per run), and a hidden `_State` (locks, the AI read queue, the daily social
allowance). **Automation writes only the columns it owns; Status, Notes and My rating are
the person's and are never overwritten.** All access goes through a dedicated
service account that can edit only that workbook.

### Sources (registry: `sources/v0_sources.yaml`)

| Kind | Examples | Read by |
| --- | --- | --- |
| Company job boards | Greenhouse, Lever, Ashby (Anthropic, Stripe, Pinterest and more) | code, from fields |
| Public aggregators | Remotive, Remote OK, Himalayas, Jobicy, The Muse, We Work Remotely | code, from fields |
| Keyed APIs | JSearch, Jooble (free plans; no new spending) | code, from fields |
| Listing, then each job page | YC, Built In, Getro (Accel, Primary), a16z, Work at a Startup (public pages) | code, from the page's job data |
| Free text | Hacker News "Who is hiring?", Ali Rohde Jobs newsletter, X posts, LinkedIn posts and job cards | Haiku reads, code checks |
| Not live yet | Gmail job alerts, Next Play newsletter, school/MBA sites, Cosign, logged-in Work at a Startup | see Current state |

### Rules the project never breaks

- **No paid model API.** AI work runs only inside the user's Claude cloud session.
- **The daily run is cloud-only** (Claude Code routine, environment `JobHunterEnv`). Local use is for development.
- **Secrets stay out of git, logs, chat and PRs.** Cookies and keys live in the cloud environment's settings. Never paste a cookie value anywhere.
- **Social sources are read-only with random pauses and one live attempt per source per New York day**, reserved in `_State` before any request (`scripts.allowance`). A spent day is never retried.
- **Nothing merges without a review by the other AI.** Claude-written code is reviewed by Codex and the reverse, on the *exact* latest commit, with green CI. See [docs/REVIEW_WORKFLOW.md](docs/REVIEW_WORKFLOW.md) and [AGENTS.md](AGENTS.md).
- **Nothing touches the real Sheet, a live account or money without the owner's explicit "go".**

### Current state (as of `main` at `d28732b`, PR #53 merged October 23, 2026)

**Built and tested.** 305 commits on `main`; the offline suite passes (1,384 passed, 1 skipped
with `uv run --locked --extra social python -m pytest -q`). Done: the Sheet writer (lock,
journal, quota pacing, read-back), the source registry and readers, the shared fact checker,
the AI read queue, safety-stop flags (all printed per run), the social allowance guard,
rejection tracing, the MBA 2027 rule, structured pay reading and `scripts.field_audit` (flags
columns a source leaves blank when it actually publishes them).

**Proven live.** On **October 19, 2026** a manual 28-day pull in `JobHunterEnv` wrote **505
jobs from 51 sources** to the real Sheet. X (94 lead rows), the Ali Rohde newsletter, a16z and
the job boards worked. **LinkedIn was refused at login** and is on hold (decision A18); its
code is merged but must not run live until the owner decides. The unit tests do not prove
cloud behaviour; only that run did.

**Not done.** The `JobHunter Daily` routine (06:07 America/New_York) has **not been created**.
Gmail alert reading needs the owner's forwarding filters (B1). Next Play, school/MBA sites and
Cosign need URLs from the owner. A single settings file, a command-by-command README and a
control page are planned (E3, E1, E2). The docs (last checked October 21) say the old Sheet rows that are not for MBA 2027 are still
there; erasing them (A22) waits for the owner's "go" on a fresh list.

**Open pull requests:** #51 (Codex's repair PR; its fixes already reached `main`, closing awaits
the owner) and #54 (Codex's separate search-coverage audit, still a draft; adds no schedule).

**Not re-verified for this write-up:** the live Sheet's current contents, whether GitHub checks
are green on later branches, and anything that happened after October 23. The docs below carry
the dated detail; if they disagree with the code, trust the code.

### How to move it forward (in order)

1. Read [docs/START_HERE.md](docs/START_HERE.md) (what the owner answers, does and approves) and [docs/PENDING.md](docs/PENDING.md) section 0 (the live decision list; it can lag `main`, so check it against GitHub first).
2. Get the owner's answers: A22 (erase non-MBA rows), A25/B11 (which company MBA programs to read, General Motors first), A24/A23 (edge cases of the MBA rule), A18 (LinkedIn).
3. Do the next real run only on reviewed `main` using [docs/LIVE_RUN_PROMPT.md](docs/LIVE_RUN_PROMPT.md), with the owner's approval for that run.
4. After a clean run and a next-morning check of the Sheet and Run Log, create the daily routine from [docs/ROUTINE_PROMPT.md](docs/ROUTINE_PROMPT.md) (decision A3).
5. Then build, one PR each: settings file (E3), command README (E1), control page (E2).

### Map of the repository

| Path | What is there |
| --- | --- |
| `jobhunter/` | The library: postings and filters, Sheet writer (`sheets.py`, `sheet_*.py`), fact checker (`post_facts.py`), per-source readers, AI queue, allowance |
| `scripts/` | Commands run with `uv run --locked python -m scripts.<name>`; `try_*.py` are old experiments, not production |
| `sources/` | `v0_sources.yaml` (the source registry) and `social_queries.yaml` |
| `tests/` | The offline test suite (no network, fake Sheets) |
| `docs/` | `PLAN.md` (scope), `START_HERE.md` and `PENDING.md` (decisions), `CLAUDE_HANDOFF.md` (history and merge notes), `LIMITS.md` and `PARAMETERS.md` (every number), `SOURCES_HOW_READ.md`, `V0_VERIFICATION.md` and `ATTEMPTS.md` (evidence) |
| `AGENTS.md`, `CLAUDE.md` | Rules for AI contributors and reviewers |

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

The social collectors (X, LinkedIn) need the optional extra: `uv sync --locked --extra social`.
JobSpy is not installed or enabled. Real runs need cloud credentials that are never stored in
this checkout, and a passing test suite proves neither a source's live access nor the cloud run.
The tests under `review_probe/` exercise a historical in-memory writer example.
The `scripts/try_*.py` files are historical experiments, not production commands.

Keep credentials, email, browser profiles, and session/recovery data outside this
checkout. Local development is permitted; daily production must run entirely
in Claude's cloud. Read [AGENTS.md](AGENTS.md) before changing the repository.

## M0 source/extraction stage (historical first stage)

This early stage samples one public Greenhouse PM posting. It does not implement full
eligibility, all sources, or Google Sheets delivery; the current pipeline is the one described
above. Run from the repo root:

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
files may be ephemeral. The temporary directory is not persistent storage: production
pending work is saved in the Sheet's `_State` tab.
Follow [the cloud excerpt prompt](docs/M0_EXTRACTION_PROMPT.md) to produce the
Claude JSON through the existing subscription. Never manually label test data as
a live model result. Python validates quotations and derives record fields.
