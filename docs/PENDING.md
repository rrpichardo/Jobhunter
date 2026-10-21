# Pending items: your decisions, your tasks, Codex, and what Claude does next

Created October 18, 2026; rewritten and re-checked against GitHub and the Sheet on October 19, 2026, about 23:30 UTC.
When the user asks "what is pending", "what do you need from me" or "where are we", Claude reads section 0 first,
checks it against GitHub, answers in plain language, and fixes this file if it is out of date. Nothing here is a claim
that work exists unless its status says so.

## 0. At a glance

**Fill-out form:** every question in 0.1 and every task in 0.2 is also in `docs/DECISIONS_FORM.md`, with an empty "Your answer"
column. Fill it in (or answer in chat); Claude copies each answer back here. The IDs are the same.

### 0.1 Decisions only you can make

| ID | Question | Claude's recommendation | Status |
| --- | --- | --- | --- |
| A18 | **LinkedIn: what now?** The first live run was refused at login on its first search (`social_login_failed`, a redirect loop). A fresh cookie fixes only one possible cause, so nothing guarantees it works next time. Options: (a) read your LinkedIn job-alert emails through Gmail (needs B1); (b) rely on JSearch and Jooble, which already bring LinkedIn listings into the Sheet; (c) one diagnostic try: Claude first makes the collector say what page it was sent to, then you refresh the cookie; (d) run the LinkedIn collector on your own computer (your home internet and browser) instead of the cloud; (e) drop the LinkedIn collectors (close #43 and #48); (f) your own proposal. | (a) plus (b) now; keep #43 and #48 open but on hold; remove `LINKEDIN_LI_AT` from JobHunterEnv until you decide, so the daily routine does not knock with a bad cookie. | open |
| A3 | **Create the daily routine?** First look at the new rows the first run added to the Sheet (505 jobs, 94 of them X leads) and say whether they are useful. Then Claude creates `JobHunter Daily` (06:07 New York, 3-day window, Haiku reads, LinkedIn off unless A18 says otherwise). | Yes, after you look at the Sheet. | open (needs your look at the Sheet) |
| A12 | **Codex "go".** All eleven open PRs need a Codex review of their exact head before anything merges. Say "go" when you have Codex credits; Claude requests one PR at a time in the order in `docs/CODEX_REVIEW_QUEUE.md`. | Go when credits are available. | open |
| A16 | **X posts that name no company** (E8). 39 facts from 34 X posts were rejected only because the company was empty (a person posting "we are hiring a Chief of Staff, DM me"). | Fill the company with the poster's `@handle` in code (not by the AI) and show the row as a lead; needs a PR and Codex. | open |
| A17 | **Pay written like `$190k-$220k`** (E7). The pay filter reads `USD 50,000 per year` but not plain `$Nk-$Mk`, so those jobs are kept as "pay unresolved" and the floors ($140k US, $70k Latin America) rarely act on X and Hacker News posts. | Count `$Nk-$Mk` as annual USD when no hourly or monthly word or other currency is next to it; anything else stays "unresolved". | open |
| A13 | **Plural titles** ("Product Managers"). Today the plural is dropped and the singular collected; it also keeps such posts from being read at all on Hacker News. | Yes, accept plurals. | open |
| A19 | **X replies** (E9). The searches do not drop replies (the query file wrongly says they do). One thread of replies gave 25 of the 94 X rows, and they were real roles. | Keep replies; fix the wrong comment. | open |
| A7 | **X search wording after the first run.** The 10 searches gave 178 posts; some results are off-target listings from aggregator accounts (for example Ugandan, Kenyan and Indian job pages). | Keep the wording for a week of daily runs, then revise with numbers; first record which search found each post (E10). | open |
| A20 | **More tracing** (E5, E6, E10): keep the rejection reasons in the Sheet (E5), print why job boards drop jobs (E6), record which search found each social post (E10). | Yes to E10 and E5; E6 later. | open |
| A21 | **Order of the bigger deliverables** (E1 README, E2 control page, E3 one editable settings file). | E3 first, then E1, then E2. | open |

Decisions already made are listed in section 2 so they are not asked again.

### 0.2 Your tasks (only you can do them)

| ID | Task | Status |
| --- | --- | --- |
| B1 | Gmail forwarding filter: in the dedicated job-alert Gmail, make a filter from a real alert that forwards to the Claude-connected Gmail and excludes security, login, verification and reset mail; in the connected Gmail, add a filter that applies the `JobHunter` label; confirm one fresh alert arrives at both ends. This also unlocks LinkedIn alerts (A18 a). | open |
| B2 | Turn on job alerts from Indeed, Glassdoor and Lenny's/TrueUp. | open |
| B3 | Send the names and web addresses of the school/MBA job sites you want, and the correct Cosign address (`cosign.com` is a parked domain). If a site needs a login, log in yourself and put the cookie in JobHunterEnv. | open |
| B4 | In the Claude Gmail connector settings, change Delete label, Mark spam, Trash and Remove labels from "Always allow" to "Needs approval". | open |
| B9 | Tell Claude the web address of the Next Play newsletter you read (`nextplay.substack.com` is a 2021 publication, not it). Claude then builds its reader like the Ali Rohde one. | open |
| B10 | Optional, only for the logged-in Work at a Startup lists: tell Claude the NAME of the cookie saved as `WAAS_SESSION_COOKIE` (or re-save it as `name=value`). Never paste the value in chat. | optional |
| B8 | Optional: rotate the Google service-account key. | optional |
| B5 | Re-copy a cookie into JobHunterEnv only if a source reports it is logged out (for LinkedIn see A18). Never paste a cookie in chat. | as needed |
| B6 | After the routine is live: rate leads in the Sheet and join the day-7 and day-14 reviews. | later |
| B7 | Later, when you ask: clean up old alert subscriptions in your main mailbox. Not authorized now. | deferred |

### 0.3 Waiting on Codex (your "go", A12)

Every open PR is Claude-written and needs a Codex review of its exact head plus green CI before it may merge. Heads, history and a
ready-to-paste request for each are in `docs/CODEX_REVIEW_QUEUE.md`. Until then each carries an interim independent review.

| PR | What | Note |
| --- | --- | --- |
| #42 | Forward-Deployed / AI Deployment / AI Implementation Strategist roles | Codex found 1 issue on `62fc1be`, fixed; needs review of the current head |
| #44 | Work at a Startup public pages | |
| #45 | a16z portfolio jobs | conflicts with #44 when both merge (keep both sides) |
| #46 | This status and handoff documentation | head moves with every docs update |
| #49 | Haiku-vs-Sonnet reading test (ran: 100 of 100 agree) | |
| #50 | E4: a reason for every rejected fact and every filter drop | CI green; Claude's automated review: no issues |
| #40 | X collector | ran live on October 19 (worked); base of #41, #43, #47 |
| #41 | Run modes: 28 days by hand, 3 days daily, refuses after a gap | after #40 |
| #43 | LinkedIn post collector | live login failed (A18); on hold until A18 |
| #47 | Ali Rohde newsletter | ran live on October 19 (worked) |
| #48 | LinkedIn job listings | live login failed (A18); on hold until A18 |

### 0.4 What Claude does as soon as you answer

- A18: builds or closes what you choose; (a) waits on B1. A3: creates the routine with the agreed sources and Haiku reading.
- A12: requests Codex one PR at a time, fixes findings in new commits, merges each only with an exact-head Codex review and green
  CI, in the order and with the conflict recipes in `docs/CLAUDE_HANDOFF.md` ("Merge plan").
- A16, A17, A13, A19, A20, A21: one small PR each, with tests, then Codex.
- B9, B3, B10: builds or retests the source with the address or name you give.

## 1. First live run and first manual run: results (October 19, 2026, about 22:17 to 22:36 UTC)

Run from `claude/combined-live-run` (commit `846f3be`) in JobHunterEnv, 28-day window, Haiku reading, 1,056 tests passed first,
every command exited 0. The Sheet was backed up first (A15).

- **X worked.** 10 of 10 searches, 178 posts, 175 readable. Haiku wrote 156 facts; 117 passed the checker; the collection filter
  dropped 23 (10 for role, 13 for place, none for pay); **94 became lead rows.** The printed `rejected=42` is 39 rejected facts plus
  3 unreadable posts. **All 39 had an empty company** (A16); the 34 posts holding them stay queued and will be rejected again until
  A16 is decided. About a third of the 94 rows come from two multi-role posts (25 and 7 rows); a few are off-target non-US listings
  kept because the place was unclear (A7).
- **Ali Rohde newsletter worked.** 4 editions, 66 valid facts, 20 dropped for role and 1 for place, 45 delivered, 44 Sheet rows (2
  shared an application link). Every newsletter row has its own application link.
- **Hacker News:** 15 comments, all read before; nothing new.
- **a16z:** 26 jobs from 3 of 4 searches; the Product search got a temporary 503 (recorded as a source problem).
- **LinkedIn did NOT work:** refused at login on the first search (`social_login_failed`, redirect loop); posts and job cards
  collected nothing; the tool still exited 0, so only its printed words show the failure (A18).
- **Sheet (checked by Claude directly, read-only):** the Run Log shows four batches of 150, 150, 150 and 55 (505 jobs, status
  `complete-with-source-failure`); the Jobs tab now holds 710 job rows (205 from before plus 505). The writer grows the sheet
  automatically when it needs more rows.
- **Where the explanations came from:** the counts were checked against the Sheet; the empty-company cause came from the run
  session reading its own saved files (you approved that), and a test now reproduces it exactly. PR #50 makes every future run
  print these reasons itself.

## 2. Decisions already made (do not ask again)

- A1: build LinkedIn, X and Work at a Startup collectors, read-only. A8: BizOps stays out; Forward-Deployed / AI Deployment /
  AI Implementation Strategist titles are in (#42).
- A2 and A15: the first live test and manual run happened on October 19 from the combined run branch, before Codex, at your
  request, after you backed up the Sheet. **Nothing merges to `main` without a Codex review of its exact head and green CI** (A4).
- A3 (October 19): create the routine only after one manual run in JobHunterEnv has been checked. The manual run happened; your
  look at the Sheet is what remains (0.1).
- A5: company boards keep the 28-day window. The window rolls forward every day; a job already in the Sheet stays there and is
  never re-added, so daily runs lose nothing; only roles first published more than 28 days ago stay out. A6: no extra JSearch
  pages (free plan). A7 (first run): keep today's limits; revisit now (0.1).
- A10: old PRs #19 to #30 closed (their content is in `main`; each was covered by Codex reviews, finally the combined #39).
- A11: Haiku does the reading step ("haiku is good to go"; a bigger test was declined: "with 100 we are good").
- A14: old commits stay as they are (no history rewrite); see the note in section 6.
- Windows: first manual run 28 days, daily routine 3 days, a daily run refuses after a gap of more than 2 days 6 hours.

## 3. Deliverables (asked for or proposed)

| ID | Deliverable | Status |
| --- | --- | --- |
| E1 | README that explains every command, in order, for a non-technical reader | pending (A21) |
| E2 | A basic control page: Run Log and source health without the terminal, and a plain way to change settings; must not become a local production dependency | pending, design to discuss (A21) |
| E3 | One editable settings file the program reads for every number (today they are constants in code; all explained in `docs/PARAMETERS.md`) | pending (A21) |
| E4 | A reason for every rejected fact and every filter drop, printed by each run (`trace:` lines) and mapped in `docs/TRACEABILITY.md` | **built, PR #50**, waiting for Codex; already in the run branch |
| E5 | Keep the reason counts in the Sheet so they outlive the session | proposed (A20) |
| E6 | Print why job boards drop jobs (role, place, pay) | proposed (A20) |
| E7 | Read pay written like `$190k-$220k` | your call (A17) |
| E8 | Fill the company of no-company posts with the poster's `@handle` | your call (A16) |
| E9 | X replies: keep them and fix the wrong comment, or filter them | your call (A19) |
| E10 | Record which search found each social post, so search wording can be tuned with numbers | proposed (A20) |
| E11 | A Run Log column for the AI queue counts | proposed (part of E5) |

## 4. Work that waits on a decision or task

| What | Waits on |
| --- | --- |
| Gmail alert collection (including LinkedIn alerts) | B1, B2 |
| Next Play newsletter reader | B9 |
| School/MBA sites and Cosign | B3 |
| Work at a Startup logged-in lists (the public page shows only 24 of 241 jobs) | B10 |
| LinkedIn collectors (#43, #48) | A18 |
| The daily routine | A3 |
| Merging anything | A12 (Codex) |
| The small rule fixes | A13, A16, A17, A19 |

## 5. How runs work (your direction, October 18)

1. The first pull is a one-off manual run that looks back four weeks (done October 19).
2. Then you check the Sheet (A3).
3. Then the scheduled routine runs daily at 06:07 New York with a 3-day window; only new posts are read by the AI.

Run modes (your decision, October 19):

| Run | Window | When |
| --- | --- | --- |
| First manual run | `--lookback-days 28` | once, by hand, before the routine exists (A3) |
| Daily routine | `--lookback-days 3` | 06:07 America/New_York, every day |
| Catch-up | `--lookback-days 28` | by hand, whenever the last complete Run Log row is more than about 2 days old |

`scripts/run_window.py` enforces this with one simple rule: the daily routine looks back 3 days and refuses to run
(exit 3, `catch_up_needed`) when the last complete run started more than about 2 days ago (2 days plus 6 hours of scheduler
drift) or there has never been one; `--mode manual` prints 28. Three days against a two-day limit leaves a full extra
day of room for run time, so one missed day is covered and nothing falls between two runs. Read-only, offline-tested. Overlap never duplicates jobs.

## 6. Note: the "Claude-Session" lines in old commits

Some of Claude's commits end with a line linking to the chat session that wrote them. They were left in on purpose: removing them
would re-create those commits and void every Codex approval tied to them. The link only opens for the account owner and carries no
secret. On October 19, 21 more commits got the line by mistake; they are treated the same way, and newer commits omit it. Codex
flagged it on #39 (that thread is left open on purpose); review requests tell Codex it is known and decided. Say "rewrite" if you
ever want them scrubbed (new commit IDs; reviews tied to them void).

## 7. History (kept for reference)

**First Codex round (October 19, morning).** Codex reviewed every Claude-written PR of the old stack and found seven real
problems in five of them; each was fixed in its own PR and Codex approved each fix on its exact head:

| Original PR | Codex finding (short) | Fix PR | Approved head |
| --- | --- | --- | --- |
| #19 | Large first pull rejected by the 5 MiB input limit | #32 | `d2b961e` |
| #21 | A misread Hacker News comment was marked read and lost; run labels could collide | #33 | `6ce257f` |
| #24 | A broken Jobicy item aborted the run; later-page failures were not recorded | #34 | `dd7a0ac` |
| #25 | Pages opened but not delivered starved the rest of a big source | #35 | `e40aba2` |
| #26 | The daily social allowance could not be closed after midnight (New York) | #36 | `042dedc` |
| #27 | Same lost-post bug in the X/LinkedIn validator | #37 | `b63a9f5` |

All of it then landed as one combined PR, #39, which Codex cleared on its exact merged head `c6e5f30` (15:35 UTC, merged 16:07 UTC).
Codex then hit its usage limit (about 16:10 UTC); one request at 20:09 UTC was answered at 20:11 UTC (#42).

**Earlier manual pull (October 18 to 19, public sources only):** 322 jobs from 46 sources in three paced batches; the first attempt
hit Google's quota and left a lock (fixed by #28; the lock was removed with your approval). Historical evidence recorded by that
session, not re-verified.

**Built earlier and now in `main`:** per-run safety-stop flags, paging for The Muse and Jobicy, skipping job pages already in the
Sheet, the daily social allowance in `_State`, and the shared validator for Hacker News, X and LinkedIn posts.
