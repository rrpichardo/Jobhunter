# How each source is read: code, or Claude plus a code check

Written October 19, 2026 for the user. It is checked against `sources/v0_sources.yaml` and the parsers in
`jobhunter/postings.py`. Nothing here is detected automatically: a person decides how each source is read when
the source is added, and that decision is built into the code. If a structured source changes its layout, its
reader rejects the items and the Sources tab shows it as failed or with rejected items; code never quietly
re-labels it as messy text.

## The three ways a source is read

| Way | Who reads the text | Used for |
| --- | --- | --- |
| **A. Fields** | Plain Python code reads named fields (title, company, location, date, link) straight from the data. No AI. | Sources that already give separate fields |
| **B. Listing, then each job's page** | Code reads the listing for links, then opens each job page and reads its standard job-details block (JSON-LD or page data). No AI. | YC, Built In, Getro |
| **C. Claude reads, code checks** | A Claude model reads free text and proposes the facts. Code accepts a value only if it appears word for word in that text, and code makes the Job ID, the date and the fallback link. | Hacker News comments now; alert emails, newsletters, LinkedIn and X posts when built |

The model for way C is whatever model the routine session runs (Sonnet 5.5 in the first test). The code does not
choose it. The plan's idea of using Haiku for this step has not been built or tested.

## Every source

| Source | Way | Reader in the code | State recorded after the first manual pull (October 19; historical evidence from an earlier session, see V0_VERIFICATION.md) |
| --- | --- | --- | --- |
| Greenhouse boards (Anthropic, Stripe, Pinterest and the others in the registry) | A | `parse_greenhouse` | Ran in the first pull |
| Lever boards | A | `parse_lever` | Ran |
| Ashby boards | A | `parse_ashby` | Ran |
| Remotive | A | `parse_remotive` | Ran; delivered 0 (its few product jobs did not match the collection rules) |
| Remote OK | A | `parse_remoteok` | Ran |
| Himalayas | A | `parse_himalayas` | Ran; delivered 0; dates unreliable (see BACKFILL_WINDOWS.md) |
| Jobicy | A | `parse_jobicy` (pages by cursor) | Ran |
| The Muse | A | `parse_themuse` (every page) | Ran; the biggest source, 177 jobs |
| We Work Remotely | A (an RSS feed read with a feed library) | `parse_wwr_rss` | Ran |
| JSearch (needs the key in the environment) | A | `parse_jsearch` | Ran, one request |
| Jooble (needs the key) | A | `parse_jooble` | Ran, one request |
| YC public product jobs | B | `stubs_yc`, `detail_yc` | Ran |
| Built In | B | `stubs_builtin`, `detail_builtin` | Ran |
| Getro boards (Accel, Primary) | B | `stubs_getro`, `detail_getro` | Primary ran; Accel was flagged failed by a bug fixed in PR #29 |
| Hacker News "Who is hiring?" | C | `jobhunter/hn_hiring.py` plus the shared checker in `jobhunter/post_facts.py` | Ran: 28 comments read, 14 jobs delivered |
| a16z portfolio jobs | none yet | `count_a16z` counts links only | Listing-only: delivers no jobs |
| Gmail job alerts | C | `jobhunter/gmail_alerts.py` | Not live: no forwarded alert yet and the connector adapter is not built |
| Newsletters: Next Play, Ali Rohde | C (planned) | not built | Needs verified feed URLs |
| LinkedIn job listings | none yet | not built | Needs your approval (A1) and a first run (A2) |
| LinkedIn hiring posts | C | checker built (`post_facts.py`); the collector that fetches posts is not | Not run |
| X hiring posts | C | checker built; the collector is not | Not run |
| Work at a Startup, public pages (product and operations role pages) | B | `stubs_waas`, `detail_waas` | Read live without a login on October 19: 24 product listings (15 matched the rules) and 29 operations listings (1 matched). The site answers HTTP 406 unless the request says it accepts HTML. Shows no posting date, and only the first ~25 jobs of each role page |
| Work at a Startup, logged in (full lists: ~240 product, ~1,400 operations) | B | not built | Optional: needs your session cookies |
| Cosign, school and MBA sites | to be decided | not built | Need your URLs |

## What stops a wrong value reaching the Sheet

- Way A and B: a reader that cannot find a required field rejects that item. The rejection is counted and shown.
- Way C: a fact that is not word for word in the post is rejected and counted; a fact for a post the AI did not
  report reading is rejected; the application link must be one the post really contains, otherwise the post's own
  link becomes the lead.
- All ways: the same filter then applies your role, location and salary rules, and the writer keeps your Status,
  Notes and My rating.
