# First-run backfill: 4-week window per source

PLAN.md (October 18 decision 3): the first run collects jobs posted in the last
28 days, then every daily run repeats the same window. Repeats are harmless
because Python upserts by Job ID and preserves Status, Notes and My rating.
`scripts/source_probe.py --lookback-days 28` is the default; `Posting.posted_at`
is the posting date from source metadata (UTC) or empty. A posting with no usable
date is KEPT and counted as `date_unknown`, never dropped on missing data. The
probe note per source reads `outside_window=N; date_unknown=N`.

"Checked" below means one polite GET of a public endpoint on October 18 from a
development machine to read field names (no login, nothing stored). That is
development evidence only: retest in JobHunterEnv before relying on a row.

| Source | Date field | Server-side date filter | Status of the window |
| --- | --- | --- | --- |
| Greenhouse boards | `first_published` (checked). `updated_at` is ignored: it changes on every edit | none | Client-side filter. Complete board response, so no coverage gap |
| Lever boards | `createdAt`, epoch ms (checked) | none | Client-side. Complete response |
| Ashby boards | `publishedAt` (checked) | none | Client-side. Complete response |
| Remotive | `publication_date`, no zone, read as UTC (checked) | none | Client-side. Registry asks for the product category; depth unverified |
| Remote OK | `date` / `epoch` (checked) | none | Client-side. Feed returns about the 100 newest only: **GAP** for a full 4 weeks |
| Himalayas | `pubDate`, epoch seconds (checked) | none known | Registry fetches `limit=50` of ALL categories, which may span only hours: **GAP**. Needs pagination (parameters not yet verified) |
| Jobicy | `pubDate` (checked) | none used | `count=50` product tag: depth for 28 days unverified, **GAP** until measured |
| The Muse | `publication_date` (checked) | none | Page 1 only (about 20 jobs): **GAP**. Needs a page loop (ordering not yet verified) |
| We Work Remotely RSS | RSS `pubDate` | none | Feed depth unknown: **GAP** until measured |
| JSearch | `job_posted_at_datetime_utc` | yes: `date_posted` today / 3days / week / month, chosen from the window | One request per run (200 requests a month free). A page holds about 10 jobs: **GAP**; more pages cost quota, so that needs your approval |
| Jooble | `updated` | none verified | Client-side. Page 1 only: **GAP** |
| YC public product jobs | detail page JSON-LD `datePosted` (schema.org; not yet checked live) | none | Listing dates are NOT used. Every shortlisted page is opened, and only its own `datePosted` can set the date; otherwise `date_unknown` and kept |
| Built In | detail page JSON-LD `datePosted` (not yet checked live) | none | Every shortlisted page is opened (up to the 300 safety stop); the page's own date decides |
| Getro (Accel, Primary) | no verified date field | none | Always `date_unknown` and kept until a field is verified |
| a16z | none | none | Listing-only, delivers no jobs yet |
| Hacker News Who Is Hiring | comment `created_at` | thread per month | Listing-only today. Backfill = the current thread, plus last month's if it is inside 28 days (not built) |
| Gmail alerts | message date | Gmail `newer_than:28d` (planned) | Live adapter not built |
| LinkedIn jobs / posts | page filters "Past month" | yes, in the search | Collector not built |
| X hiring posts | post date | yes: `since:` search operator | Collector not built |
| Work at a Startup, school/MBA, Cosign | unknown | unknown | Not collected yet |

Safety stops, not targets (all reported, never silent):

- `DETAIL_SAFETY_STOP = 300` job pages per detail source per run. Candidates past
  it appear as `details_skipped=N` in the source note. Because the same candidates
  sort first on every run, a source that regularly hits the stop would starve its
  tail; the planned fix is to skip Job IDs already in the Sheet.
- `EXTRACTION_SAFETY_STOP = 1000` Gmail AI extractions per run.
- One writer batch holds at most `JOB_BATCH_SIZE = 150` jobs (its recovery journal
  must fit in `_State`). Larger runs are split into `<run id>-b001`, `-b002`, ...
  and rerunning the same run ID finishes the remaining batches without duplicates.

Design notes from the October 18 self-review:

- Old-but-open roles are excluded by design. Greenhouse `first_published` can be
  years old for a role that is still open, so the 28-day window drops it. That
  follows the user's "last 4 weeks" decision; widening it for company boards is a
  user choice, not an oversight.
- `More details` carries "First seen by <source>: <run time>", which the writer
  refreshes on every run. With a 28-day window that rewrites that machine-owned
  column for every in-window job each day. It was already true for board jobs; the
  window makes it more rows. A stable first-seen time needs a separate follow-up.
- Writer batches pause `BATCH_PAUSE_SECONDS = 2.0` between each other to stay under
  the Sheets quota. A 3,000-job first run is about 20 batches; it is untested live.
