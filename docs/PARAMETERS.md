# JobHunter parameters: every setting in one place, in plain language

For a person who does not write code. Last checked against the real code on **October 19, 2026**, using the combined
result of all open pull requests (PRs #40 to #49). Where a setting only exists after a PR is merged, the PR is named.

**How to use this file.** Find the setting in the tables, read what it does and what changes if you move it, then use
section 12 ("How to change a setting") to either edit it yourself (searches and company lists) or tell Claude exactly what
to change (numbers kept in the program). Today most numbers live inside the program, not in one editable file; section 13
explains the plan to move them all into one file you can edit.

**Safety rule that overrides everything below.** LinkedIn and X can restrict an account that looks like a robot. The
program therefore reads each of them **once per New York day**, with random 3 to 9 second pauses between searches, and never types, likes,
follows or messages. Raising a number below raises that risk. Nothing here is a guarantee that an account stays safe.

---

## 1. The big picture: what one run does

1. **Choose the look-back window** (section 3): 28 days for a hand-started "manual" run, 3 days for the daily routine.
2. **Collect** jobs from many places (section 6): company job boards, public job sites, venture-capital portfolio boards,
   Hacker News, a newsletter, and (with your cookies) X and LinkedIn.
3. **Read** the free-text sources (Hacker News, X, LinkedIn, the newsletter) with the AI (section 7). Haiku does the reading
   (you accepted it on October 19). Code then checks every value word for word.
4. **Decide who matches** (section 5): roles we collect, places we accept, salary floors.
5. **Write** the matches to the Google Sheet in batches (section 8), never duplicating a job already there.

## 2. The settings you are most likely to change

| # | Setting | Today | What it changes | Section |
| --- | --- | --- | --- | --- |
| 1 | Manual run look-back | 28 days | how far back a hand-started run looks | 3 |
| 2 | Daily run look-back | 3 days | how far back each daily run looks | 3 |
| 3 | X searches per day | 10 | how many X searches the one daily session makes | 4 |
| 4 | LinkedIn post searches per day | 5 | hiring-post searches in the one LinkedIn session | 4 |
| 5 | LinkedIn job searches per day | 5 | job-listing searches in the same session | 4 |
| 6 | The search wording itself | see section 4 | what is searched on X and LinkedIn | 4 |
| 7 | Salary floors | US $140,000, Latin America $70,000 | which jobs are dropped for low pay | 5 |
| 8 | Role families | six families plus forward-deployed strategist | which job titles count | 5 |
| 8b | MBA 2027 rule | on (October 21) | only roles meant for MBA graduates of 2027 are collected | 5 |
| 9 | Company boards | 24 companies | which companies are read directly | 6 |
| 10 | Pause between sheet batches | 45 seconds | how gently the Sheet is written | 8 |

---

## 3. Time windows and run modes

| Setting | Today | What it does | If you raise it | If you lower it | Where it lives |
| --- | --- | --- | --- | --- | --- |
| Manual run look-back | 28 days | A run you start by hand looks back this far. Used for the first big pull and for catch-ups. | more jobs, longer run | fewer old jobs | `MANUAL_DAYS` in `jobhunter/run_window.py` (PR #41) |
| Daily run look-back | 3 days | The scheduled routine looks back this far. | safer overlap, a little more work | risks missing jobs after a missed day | `DAILY_DAYS` in `jobhunter/run_window.py` (PR #41) |
| Longest gap a daily run accepts | 2 days 6 hours since the last complete run **started** | If the last complete run started longer ago than this, the daily run **refuses** (exit 3) and asks for a manual run, so nothing is silently skipped. | tolerates longer breaks (but 3 days of look-back must still cover it) | refuses sooner | `MAX_GAP` in `jobhunter/run_window.py` (PR #41) |
| Default window for the collector tools | 28 days | What the collectors use if no window is passed. The routine always passes the window explicitly, so this matters only for hand runs. Several tools carry their own copy: change all of them together. | | | `LOOKBACK_DAYS` in `scripts/source_probe.py` and `scripts/hn_hiring.py`; `default=28` in `scripts/x_collect.py`, `linkedin_collect.py`, `newsletter_collect.py` |
| Hacker News threads read | the monthly "Who is hiring?" threads that can hold comments inside the window | The tool also reads the previous month's thread when it could still hold recent comments. | | | `select_threads` in `jobhunter/hn_hiring.py` |

Important: the daily window (3 days) must stay larger than the longest accepted gap (2 days 6 hours), or jobs can fall
between two runs. Change them together.

## 4. Searches on X and LinkedIn

### 4a. The search wording (you can edit this yourself)

File: `sources/social_queries.yaml`. One line per search. Every quoted phrase must be a role the program actually collects
(a test checks this), so a search never wastes part of the daily allowance on a role that would be thrown away.

**X** (10 searches today): hiring "AI product manager"; hiring "product manager" AI; hiring "senior product manager";
hiring "head of product"; hiring "chief of staff"; hiring "head of strategy"; hiring "founder in residence" OR
"entrepreneur in residence"; hiring "leadership development program"; hiring "group product manager"; hiring "strategy manager".

**LinkedIn hiring posts** (5 today): hiring "AI product manager"; hiring "senior product manager" AI; hiring "chief of staff";
hiring "head of strategy"; hiring "leadership development program".

**LinkedIn job listings** (5 today, PR #48; plain words, no quotes): AI product manager; senior product manager; chief of
staff; head of strategy; AI deployment strategist.

### 4b. The limits (numbers kept in the program)

| Setting | Today | What it does | Where it lives |
| --- | --- | --- | --- |
| X searches per run | 10 | The most X searches in the one daily session. | `LIMITS['x-twscrape']['queries']` in `jobhunter/social_collect.py` (PR #40) |
| X posts kept per run | 200 | Stops the run once this many posts are collected. | `LIMITS['x-twscrape']['posts']` |
| X posts kept per search | 40 | One busy search cannot use up the whole 200. | `LIMITS['x-twscrape']['per_query']` |
| X result pages per search | 10 (about 20 posts a page) | A hard stop on paging; well above the post limit. | `MAX_PAGES` in `scripts/x_collect.py` |
| LinkedIn post searches per run | 5 | Hiring-post searches in the one LinkedIn session. | `LIMITS['linkedin-login']['post_searches']` (PR #43) |
| LinkedIn job searches per run | 5 | Job-listing searches in the same session and allowance. | `LIMITS['linkedin-login']['job_searches']` (PR #48) |
| LinkedIn posts kept per run | 100 | Stops collecting posts at this many. | `LIMITS['linkedin-login']['posts']` |
| LinkedIn posts kept per search | 30 | Keeps one search from using the whole 100. | `LIMITS['linkedin-login']['per_query']` |
| LinkedIn job cards kept per run | 125 | Stops collecting job cards at this many (PR #48). | `LIMITS['linkedin-login']['jobs']` |
| LinkedIn job cards kept per search | 30 | Same idea for job searches (PR #48). | `LIMITS['linkedin-login']['job_per_query']` |
| LinkedIn "detail views" | 50 | **Not used today.** The number exists in the file but no code opens detail pages; the program reads only the result cards. Changing it does nothing until detail views are built. | `LIMITS['linkedin-login']['detail_views']` |
| Pause between searches | random 3.0 to 9.0 seconds | Makes the pace look human and gentle. It is applied between searches (and between the LinkedIn post phase and job phase); inside one search the page is read at the tool's own pace (X pages in turn, LinkedIn 4 scrolls with 1.2 to 2.7 second waits). | `DELAY_SECONDS` in `jobhunter/social_collect.py` |
| Sessions per source per day | 1 (America/New_York calendar day) | The day's allowance is reserved in the Sheet's `_State` tab **before** any request and is spent even if the run fails. The program refuses a second run the same day. | `jobhunter/allowance.py` (a rule, not a number to tune) |
| Scrolls per LinkedIn results page | 4 | How far the page is scrolled so more results load. | `SCROLLS` in `scripts/linkedin_collect.py` |
| "See more" expansions per page | up to 40 | Opens cut-off posts to read their full text. | `MAX_EXPANDS` in `scripts/linkedin_collect.py` |
| Wait for results to appear | 25 seconds | If no result shows up in this time the page is read as it is. | `READY_SECONDS` in `scripts/linkedin_collect.py` |

How to think about risk: LinkedIn publishes no safe number. Third-party guides quote 30 to 50 searches a day as typical, but
that is not a guarantee. On October 18 you declined 50 searches a day and chose 5 job + 5 post searches (10 total) for LinkedIn
and 10 for X. On October 19 you chose to **keep these numbers for the first live run** and revise them after reading its results.

## 5. Who counts as a match (eligibility)

All of this is applied by code after the AI has copied the facts out of a post. File: `jobhunter/postings.py`.

**Roles that are collected** (a job title must match one of these families):

| Family | Matches (examples) |
| --- | --- |
| Product management | product manager, product lead, group product manager, head of product, director of product, VP of product (also "VP, Product" and the bare "PM", for example "AI PM") |
| Chief of Staff | chief of staff |
| Leadership program | leadership (development) program; MBA or management development/rotation program |
| Strategy | strategy manager/lead/director; manager/director/head/VP of (corporate or business) strategy |
| Entrepreneurship | entrepreneur in residence; founder in residence |
| Project management | project manager; project management lead; project director (plural titles are not matched, see below) |
| Forward-deployed strategy (PR #42) | Forward-Deployed AI Strategist and name variants; AI Deployment Strategist; AI Implementation Strategist; Deployment Strategist. Any title naming an engineer or developer (Engineer, Engineering, Eng., Engr, Developer, Dev, SDE, SWE, "Software Development", plus plurals) is **not** accepted in this family. A title like "Forward Deployed Strategy Lead" is still collected, through the general Strategy family. |

**MBA 2027 rule (your decision, October 21; applied after role and place, before pay).** A job is collected only when its own
text (title plus description; for posts, the title plus the quoted sentence) says who may apply: MBA students or graduates of 2027.
Seniority does not matter: a Senior Product Manager role open to MBAs graduating in 2027 passes; a plain one does not. Code:
`mba_class_evidence` in `jobhunter/postings.py`. **What counts** (October 21, tightened after Codex's review of PR #52): an applicant
statement such as "this role is open to MBA students graduating in spring 2027", "we are recruiting MBA candidates", "open to recent MBA
graduates", "program for MBA graduates"; a named program or class ("MBA Leadership Development Program", "MBA Class of 2027", "MBA Grad 2027",
"(Full-Time MBA)", "post-MBA role", "MBA campus recruiting"); or "applicants must be pursuing an MBA". The graduating year is read from that
same statement: a different year there (class of 2028) drops the job as `mba_other_class_year`, and an unrelated "2027" elsewhere in the
posting (a product launch, a fiscal year) changes nothing. Every alternative and range in that statement is read ("graduating in May 2026
or May 2027", "between December 2026 and June 2027", "2026-2028" all include 2027). A statement the posting denies ("not open to MBA
students", "MBA graduates 2027 should not apply") never counts, and a title such as "(MBA)" cannot bring it back; a negative word in another
clause ("Experience is not required, open to MBA students graduating in May 2027") does not deny anything. **What does not count:** "MBA preferred", "MBA or equivalent experience", "MBA or
advanced degree" (qualifications), and MBAs mentioned as customers or users ("products for MBA students"). Three drop codes: `not_mba_2027`
(no such statement), `class_2027_without_mba` (a statement for the 2027 graduating class, for example "New Grad (2027 Start)" or "you will graduate
in Spring 2027", that does not mention an MBA; decision A23), `mba_other_class_year`. The kept row's "More details" quotes the words that
qualified it ("MBA 2027 evidence: ..."). Measured on 6,812 real postings from the 24 company boards on October 21: 2 meet the rule (one is an
internship, which role rules drop anyway) and 38 more are class-of-2027 roles without an MBA. Sources that show only a short snippet
(job-site search results, LinkedIn job cards, plain newsletter lines) rarely contain the wording, so they will mostly be dropped until their
reader quotes the sentence that says who the role is for.

**Roles that are always dropped:** intern, internship, summer associate, product marketing, product design(er), product
communications. "BizOps" is out of scope (your decision, October 19). Plain "program manager" is not a family.

**Known gap (your call, item A13):** a plural title such as "Product Managers" or "Project Managers" is **not** matched today, while the singular is. The same gap applies to the first filter on Hacker News and social posts: a post that says only "Product Managers" is never sent to the AI.

**Places accepted:** the United States; Latin America **only in narrow cases**; or "unclear". Latin America is accepted when
the job is remote (the source says so, or the place text says remote), or when the country is Colombia or the Dominican
Republic. An on-site job in another Latin American country (for example Brazil, Argentina or Mexico) is dropped. A city plus
country such as "Sao Paulo, Brazil" counts as unclear: kept and flagged, with the $70,000 minimum. A place that is clearly
elsewhere (for example Canada or Europe) is dropped. If the place is unclear the job is kept and flagged for you to check.
Remote roles are read from the text ("remote" alone does not prove a country).

**Salary floors (annual USD base):**

| Setting | Today | What it does |
| --- | --- | --- |
| Floor for United States jobs | $140,000 | A job whose top pay is below this is dropped. |
| Floor for Latin America jobs | $70,000 | Same, for Latin America. |
| Absolute minimum when the place is unclear | $70,000 | Anything clearly under this is dropped whatever the place. |
| Where pay comes from (October 21 fix) | Greenhouse `pay_input_ranges`, Ashby `compensation`, then a yearly USD range written in the posting text | Greenhouse and Ashby publish pay in a separate field that was never requested or read, so every Anthropic, OpenAI, Stripe, Databricks (and so on) row had a blank Salary. The tiers of one posting (zones, states) merge into one range. Text reading is narrow and reads the whole compensation sentence: two amounts of at least $30,000, a base-pay word (salary, base pay, pay range) in the same sentence, and no total-compensation, OTE, bonus, equity, commission, monthly, weekly, hourly or other-currency word before or right after the range. A Greenhouse label such as "Monthly Salary", "Annual Bonus" or "Annual Total Compensation" is kept with its own unit word (month, bonus, total compensation) and reads as unresolved; an unlabeled range is yearly. |
| Pay missing, or not an explicit annual USD figure (hourly, monthly, another currency, OTE, total compensation, equity) | kept | The row is kept. "More details" says "Salary preference: unresolved" and "Check first: verify annual USD base salary reaches ..." so you check the pay yourself. |

Where: `salary_preference`, `collection_stub_match` and `collection_match` in `jobhunter/postings.py` (the numbers 140,000
and 70,000 appear there and in the row text; 70,000 is also `MIN_REGIONAL_ANNUAL_USD`).

## 6. Where jobs come from (the source list)

Most of this is in `sources/v0_sources.yaml`, which you can edit (see section 12).

| Group | Today | Notes |
| --- | --- | --- |
| Company boards read directly (24) | Greenhouse: Anthropic, Scale AI, Databricks, Stripe, Figma, Airbnb, Coinbase, Instacart, Datadog, Cloudflare, Reddit, Pinterest. Lever: Palantir, Spotify, Mistral. Ashby: OpenAI, Ramp, Notion, Linear, Cohere, Perplexity, ElevenLabs, Sierra, Harvey. | A board that does not exist is dropped silently. To add a company, copy one line and change the board name. |
| Public job sites (6) | Remotive, Remote OK, Himalayas, Jobicy, The Muse, We Work Remotely | Himalayas returns 20 per page and its dates are unreliable; Jobicy pages 50 at a time; The Muse 20 at a time. |
| Keyed services (2) | JSearch (about 200 requests a month on the free plan, 1 request and about 10 jobs per run), Jooble (1 request) | Need keys in the environment (section 9). No new spending is authorised. More pages would use more of the monthly quota (decided: none). |
| Pages opened one by one (10) | Y Combinator product jobs, Built In, Work at a Startup (product, operations; PR #44), a16z (product manager, chief of staff, strategy, founder in residence; PR #45), Getro boards (Accel, Primary) | Work at a Startup shows only the first ~24 jobs per public page. |
| Hacker News | monthly "Who is hiring?" threads | Read by AI, then checked by code. |
| Newsletter | Ali Rohde Jobs (weekly; PR #47) | Next Play: waiting for the correct address (your task B9). |
| X and LinkedIn | sections 4 | Need your cookies (section 9). |
| Needs setup | Gmail alerts, Next Play, Cosign, school/MBA sites, Work at a Startup logged-in lists | Each waits on something from you (see `docs/PENDING.md`). |

| Setting | Today | What it does | Where |
| --- | --- | --- | --- |
| Pages opened per detail source per run | 300 | Safety stop (reported as `details_skipped`). | `DETAIL_SAFETY_STOP` in `scripts/source_probe.py`, or `--detail-safety-stop` |
| Pages per paged service per run | 100 (the first page counts, so 99 extra) | Safety stop (reported as `paging_stopped`). Only The Muse and Jobicy are paged; Himalayas reads one page of 20. | `PAGE_SAFETY_STOP`, or `--page-safety-stop` |
| Pause between ordinary requests | 1.0 second | Politeness. | `--delay` |
| Largest answer accepted | 40 MB | Safety stop. | `MAX_BYTES` |
| Newsletter editions read | the first 12 entries in the feed's own order | The feed lists newest first; the program does not sort. | `MAX_ENTRIES` in `jobhunter/newsletter.py` (PR #47) |

## 7. The AI reading step

| Setting | Today | What it does | Where |
| --- | --- | --- | --- |
| Model for reading | **Haiku** (accepted October 19) | Copies title, company, place and pay out of posts. Code then rejects any value that is not word for word in the post. | the routine prompt, `docs/ROUTINE_PROMPT.md` section 1 ("Which model reads") |
| Items handed to the AI per run | 1,000 | Safety stop; the rest wait for the next run. | `WORK_SAFETY_STOP` in `jobhunter/ai_queue.py` |
| Size of the file handed to the AI | 3 MB | The rest stays pending. | `WORK_BYTE_STOP` |
| Hacker News comments collected per run | 1,500 | Safety stop. | `CANDIDATE_SAFETY_STOP` in `jobhunter/hn_hiring.py` |
| Hacker News comment length | 20,000 characters | Longer comments are counted but not read. | `MAX_COMMENT_CHARS` |
| Quote kept for each job | 300 characters | A short exact excerpt from the post. A quote longer than this makes the fact **rejected**; it is not cut. | the validators |
| Gmail extractions per run | 1,000 | Safety stop (Gmail is not live yet). | `EXTRACTION_SAFETY_STOP` in `jobhunter/gmail_alerts.py` |
| Items not read within the window | cleared and reported | An unread item that leaves the window is dropped, and the run says how many. | `jobhunter/ai_queue.py` |

**Other built-in limits (all kept in the program; rarely worth changing):**

| Setting | Today | What it does | Where |
| --- | --- | --- | --- |
| Longest post read | 10,000 characters (24,000 for a newsletter edition) | A longer one is counted as unreadable rather than read. | `MAX_POST_CHARS` in `jobhunter/post_facts.py` |
| Newsletter feed size | 5 MiB | Larger feeds are refused. | `MAX_FEED_BYTES` in `jobhunter/newsletter.py` |
| Hand-off file size | 5 MiB (64 MiB for the final writer input) | Safety limit on the files passed between steps. | `DEFAULT_MAX_BYTES`, `SYNC_MAX_BYTES` in `jobhunter/artifacts.py` |
| Gmail messages read per run | 50 | Gmail is not live yet. | `jobhunter/gmail_alerts.py` |

## 8. Writing to the Google Sheet

| Setting | Today | What it does | Where |
| --- | --- | --- | --- |
| Jobs per writing batch | 150 | A bigger run is split into numbered batches. Not a limit on jobs delivered. | `JOB_BATCH_SIZE` in `jobhunter/sheet_records.py` |
| Pause between batches | 45 seconds | Keeps under Google's per-minute quota. | `BATCH_PAUSE_SECONDS` in `scripts/sheets_sync.py`, or `--batch-pause` (0 to 60) |
| Writes per request | up to 100 | Also kept near 1 MB. | `--chunk-size` |
| Retries on a temporary error | 3 attempts, waits up to 60 seconds; a quota error waits 20 then 40 seconds | Protects against Google's quota errors. | `jobhunter/sheets.py` |
| Duplicates | never added | A job already in the Sheet is recognised by its Job ID and is not added again. Its program-written columns can be refreshed; your columns (Status, Notes, My rating) and the Date found are never touched. | the writer (`plan_jobs` in `jobhunter/sheet_records.py`) |

## 9. Secrets and connections (names only: never paste a value into a chat or a file)

These are set in the Claude Code environment settings for `JobHunterEnv`. This session cannot see them.

| Name | What it is for |
| --- | --- |
| `X_AUTH_TOKEN` and `X_CT0` | the two X cookies for the dedicated X account |
| `LINKEDIN_LI_AT` (or `LI_AT`) | the LinkedIn cookie for the dedicated LinkedIn account |
| `WAAS_SESSION_COOKIE` | reserved for a future logged-in Work at a Startup reader; **no code reads it today** (it needs a cookie name, task B10) |
| `JSEARCH_API_KEY` and `JOOBLE_API_KEY` | the two keyed job services |
| `JOBHUNTER_SPREADSHEET_ID` | which Google Sheet is written (a copy has a different ID; a backup copy does not redirect the run) |
| `JOBHUNTER_GOOGLE_AUTH_MODE` | how the program signs in to Google |

## 10. The daily schedule

The `JobHunter Daily` routine is **not created yet** (decision A3: only after one manual run is checked). The plan: 06:07
America/New_York, repository `rrpichardo/Jobhunter`, environment `JobHunterEnv`, using the 3-day window.

## 11. Run modes at a glance

| Mode | Look-back | Starts how | Refuses when |
| --- | --- | --- | --- |
| Manual (first pull, catch-ups) | 28 days | by hand | never refuses; each social source still allows only one session per New York day |
| Daily | 3 days | the scheduled routine | the last complete run started more than 2 days 6 hours ago, or there never was one |

---

## 12. How to change a setting

**A. Things you can edit yourself** (plain text files; keep the spacing and the dash at the start of each line):
- the X and LinkedIn searches: `sources/social_queries.yaml`
- company boards, public sites and page sources: `sources/v0_sources.yaml`
After editing, ask Claude to "run the tests and open a PR" so the change is checked (a test refuses a search that names a
role the program does not collect).

**B. Numbers kept in the program** (sections 3, 4b, 5, 6, 7, 8): send Claude a message in this form:
> Change `<setting name from this file>` from `<today>` to `<new value>`. Keep everything else. Run the tests, open a PR,
> and update `docs/PARAMETERS.md` (and `docs/LIMITS.md`, which is out of date on the social sources and should be brought in line).

Claude changes one file, runs the 1,000+ tests, and opens a PR. Because the program reads real accounts, code changes wait
for a Codex review before merging (see `docs/CODEX_REVIEW_QUEUE.md`).

**C. Risky changes (ask for a second opinion first):** raising any X or LinkedIn number; shortening the pause between
requests; raising the daily window above the longest accepted gap or lowering it below it; lowering a salary floor.

**After any change to a search limit:** run once, read the printed lines (numbers only: LinkedIn prints `search_N:` lines; X prints one
`x_collected:` line with `queries_run=`, `posts=` and `error=`), and look for `wall=True` or a login or rate-limit word
(`social_login_failed`, `social_rate_limited`). If you see one, stop for the day and do not retry.

## 13. Planned: one editable file for all numbers (item E3)

Today the numbers above are written inside many program files. The plan is a single `config/parameters.yaml` with one
section per topic, every value explained in a comment, and range checks so a typo (for example 10000 searches) is refused.
It needs a code change in about ten places, with tests and a Codex review, so it is a separate PR after the first live run.
Until then this file is the map. If a value here ever disagrees with the code, the code wins and this file is wrong: tell Claude.

## 14. Words used

- **Allowance:** the one live session each of X and LinkedIn gets per New York day.
- **Safety stop:** a limit that protects against runaway work and is reported when hit.
- **Window / look-back:** how many days back a run keeps jobs.
- **Floor:** the lowest annual pay a job may offer and still be kept.
- **Candidate:** a post or card collected but not yet read by the AI.
- **Delivered:** a job that passed every check and reaches the Sheet.
- **Cookie:** the saved login token for an account; never pasted into chat.
