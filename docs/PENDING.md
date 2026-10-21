# Pending items: your decisions, your tasks, Codex, and what Claude does next

Created October 18, 2026; review/repair status updated October 19, 2026 (New York). Sheet counts below remain the
historical October 19 live-run readback; this repair task has not accessed the Sheet.
When the user asks "what is pending", "what do you need from me" or "where are we", Claude reads section 0 first,
checks it against GitHub, answers in plain language, and fixes this file if it is out of date. Nothing here is a claim
that work exists unless its status says so.

## 0. At a glance

**Short plain version for the user: `docs/START_HERE.md` (what you answer, do and approve; what Codex and Claude do). It is this section at a smaller size; update both together.**

**Fill-out form:** every question in 0.1 and every task in 0.2 is also in `docs/DECISIONS_FORM.md`, with an empty "Your answer"
column. Fill it in (or answer in chat); Claude copies each answer back here. The IDs are the same.

### 0.1 Decisions only you can make

| ID | Question | Claude's recommendation | Status |
| --- | --- | --- | --- |
| A18 | **LinkedIn: what now?** The first live run was refused at login on its first search (`social_login_failed`, a redirect loop). A fresh cookie fixes only one possible cause, so nothing guarantees it works next time. Options: (a) read your LinkedIn job-alert emails through Gmail (needs B1); (b) rely on JSearch and Jooble, which already bring LinkedIn listings into the Sheet; (c) one diagnostic try: Claude first makes the collector say what page it was sent to, then you refresh the cookie; (d) run the LinkedIn collector on your own computer (your home internet and browser) instead of the cloud; (e) drop the LinkedIn collectors (close #43 and #48); (f) your own proposal. | (a) plus (b) now; keep #43 and #48 open but on hold; remove `LINKEDIN_LI_AT` from JobHunterEnv until you decide, so the daily routine does not knock with a bad cookie. | open |
| A3 | **Create the daily routine?** First look at the new rows the first run added to the Sheet (505 jobs, 94 of them X leads) and say whether they are useful. Then Claude creates `JobHunter Daily` (06:07 New York, 3-day window, Haiku reads, LinkedIn off unless A18 says otherwise). | Yes, after you look at the Sheet. | open (needs your look at the Sheet) |
| A12 | **Codex "go".** All eleven open PRs need a Codex review of their exact head before anything merges. Say "go" when you have Codex credits; Claude requests one PR at a time in the order in `docs/CODEX_REVIEW_QUEUE.md`. | Go when credits are available. | answered: go; all eleven exact-head Codex reviews completed in this chat |
| A16 | **X posts that name no company** (E8). 39 facts from 34 X posts were rejected only because the company was empty (a person posting "we are hiring a Chief of Staff, DM me"). | Fill the company with the poster's `@handle` in code (not by the AI) and show the row as a lead; needs a PR and Codex. | open |
| A17 | **Pay written like `$190k-$220k`** (E7). The pay filter reads `USD 50,000 per year` but not plain `$Nk-$Mk`, so those jobs are kept as "pay unresolved" and the floors ($140k US, $70k Latin America) rarely act on X and Hacker News posts. | Count `$Nk-$Mk` as annual USD when no hourly or monthly word or other currency is next to it; anything else stays "unresolved". | open |
| A13 | **Plural titles** ("Product Managers"). Today the plural is dropped and the singular collected; it also keeps such posts from being read at all on Hacker News. | Yes, accept plurals. | open |
| A19 | **X replies** (E9). The searches do not drop replies (the query file wrongly says they do). One thread of replies gave 25 of the 94 X rows, and they were real roles. | Keep replies; fix the wrong comment. | open |
| A7 | **X search wording after the first run.** The 10 searches gave 178 posts; some results are off-target listings from aggregator accounts (for example Ugandan, Kenyan and Indian job pages). | Keep the wording for a week of daily runs, then revise with numbers; first record which search found each post (E10). | open |
| A20 | **More tracing** (E5, E6, E10): keep the rejection reasons in the Sheet (E5), print why job boards drop jobs (E6), record which search found each social post (E10). | Yes to E10 and E5; E6 later. | open |
| A21 | **Order of the bigger deliverables** (E1 README, E2 control page, E3 one editable settings file). | E3 first, then E1, then E2. | open |
| A22 | **Erase the existing rows that are not for MBA graduates of 2027?** You said yes. The dry run (`docs/MBA_CLEANUP_DRYRUN.md`): 1 row is clearly for MBA 2027, 3 are 2027 new-grad roles without an MBA, 164 were read in full and are not, and 542 cannot be judged because only 300 characters were stored. Nothing was changed yet. | Say "go": back up the Jobs tab, copy the rows to an archive tab, then remove them from Jobs (reversible). Or erase only the 164 and leave the 542. | open (needs your "go" on the list) |
| A23 | **2027 new-grad roles that do not mention an MBA** (for example Databricks "Associate Product Manager, New Grad (2027 Start)", which asks for a bachelor's or master's in computer science). 38 of 6,812 board postings. | Keep them out (they are dropped with the reason `class_2027_without_mba`, so you can see the count in every run). | open |
| A24 | **Roles outside the title list that are explicitly for MBA 2027**, for example Sierra "Strategist, Agent Development (MBA Grad 2027)". Today the title list decides first, so this one is dropped. | Accept any full-time business (non-engineering) role whose text says it is for MBA graduates of 2027. | open |
| A25 | **Where do MBA 2027 roles come from?** The 24 company boards hold almost none (2 of 6,812, one an internship). Candidates: company MBA programs such as General Motors (your offer), school and MBA job sites (B3), Gmail alerts (B1, B2), LinkedIn (A18). | Name the companies and programs you want; Claude finds each program's public page and builds a reader. | open |

Decisions already made are listed in section 2 so they are not asked again.

### 0.2 Your tasks (only you can do them)

| ID | Task | Status |
| --- | --- | --- |
| B1 | Gmail forwarding filter: in the dedicated job-alert Gmail, make a filter from a real alert that forwards to the Claude-connected Gmail and excludes security, login, verification and reset mail; in the connected Gmail, add a filter that applies the `JobHunter` label; confirm one fresh alert arrives at both ends. This also unlocks LinkedIn alerts (A18 a). | open |
| B2 | Turn on job alerts from Indeed, Glassdoor and Lenny's/TrueUp. | open |
| B3 | Send the names and web addresses of the school/MBA job sites you want, and the correct Cosign address (`cosign.com` is a parked domain). If a site needs a login, log in yourself and put the cookie in JobHunterEnv. | open |
| B4 | In the Claude Gmail connector settings, change Delete label, Mark spam, Trash and Remove labels from "Always allow" to "Needs approval". | open |
| B9 | Tell Claude the web address of the Next Play newsletter you read (`nextplay.substack.com` is a 2021 publication, not it). Claude then builds its reader like the Ali Rohde one. | open |
| B11 | Send the names of the company MBA programs you want watched (General Motors first) and, if you know them, the web addresses of their MBA recruiting pages (A25). | open |
| B10 | Optional, only for the logged-in Work at a Startup lists: tell Claude the NAME of the cookie saved as `WAAS_SESSION_COOKIE` (or re-save it as `name=value`). Never paste the value in chat. | optional |
| B8 | Optional: rotate the Google service-account key. | optional |
| B5 | Re-copy a cookie into JobHunterEnv only if a source reports it is logged out (for LinkedIn see A18). Never paste a cookie in chat. | as needed |
| B6 | After the routine is live: rate leads in the Sheet and join the day-7 and day-14 reviews. | later |
| B7 | Later, when you ask: clean up old alert subscriptions in your main mailbox. Not authorized now. | deferred |

### 0.3 Review repairs: Codex implementing; Claude reviews the repair PR

**How the next Codex round is grouped (your decision, October 21: split grouping).** Group 1, reviewed together in one request: the X collector
stack #40, #41, #43, #47 and #48. Group 2, each reviewed separately: #42, #44, #45, #46, #49 and #50. #51 needs Claude's review, not Codex's. The
request comments are posted only after your "go" for that round. Details and order: `docs/CODEX_REVIEW_QUEUE.md`.
**Codex ran out of credits again right after its one review of #52 (October 21): the retries and the fresh #52 review all got "usage limit" replies, which are not reviews. They are posted and wait for credits.** Retries posted: the October 21 requests on #40, #44, #45, #46, #49 and #50 first hit the usage limit (#46 shows "We couldn't complete this review"), so each was re-posted on the unchanged head. History: **Codex had no credits (told by the user, October 21):** the requests below wait for credits; a usage-limit reply is not a review. The request for #52 was held at the user's instruction and is not posted. When credits return, Claude checks each request, re-posts any that got only a usage-limit reply, and posts the #52 request.
**Codex requests posted (October 21, after your "go").** Claude backported the ten repairs plus the clock fix onto the original PR branches as new commits (no history rewritten), tested each branch on its own, and then posted the requests. Group 1, one request for the X stack on #40 (pointer comments on #41, #43, #47, #48): `e2ce21d` (#40), `40fda94` (#41), `45aa52f` (#43), `716f3fc` (#47), `b79585a` (#48). Group 2, one request each: #44 `7e4088a`, #45 `aa9ee55`, #46 `148eec6`, #49 `96f14eb`, #50 `3214479`. #42 is unchanged (`b90c1d2`, Codex clean), so no request. Next: wait for Codex; fix findings in new commits; merge only with an exact-head review and green CI. PR #51's fixes are now on the branches it was meant for.

All eleven original PRs received exact-head Codex reviews; two were clean and nine have ten findings. The user then
authorized Codex to implement the fixes and submit a PR for Claude review while Claude is unavailable. Codex is the sole
implementation owner on `codex/repair-review-findings`, based on the combined run branch. All ten fixes are implemented with regressions. **Claude's review of repair head `76e7788` was posted on PR #51 on October 21:** the ten repairs read as correct, with one finding (the 14 X and LinkedIn collector tests only pass on October 19, because `reserve()` is not given the collector's clock; one-line fix, already written as `144859f` on the session branch) and one behavior to confirm (a generic-link newsletter role relisted in a later edition gets a new row). No fix is approved or merged to main. Original PR heads remain unchanged. Repair [PR #51](https://github.com/rrpichardo/Jobhunter/pull/51) is open for Claude review and contains only the fix delta against
`codex/review-findings-base` at e3eef3fa9a98bc804befc16e2e840486c4820c46, never the entire combined branch against main.
The combined run branch is kept in sync with these unreviewed repairs for future authorized runs only; this is not deployment.
See `docs/REVIEW_REPAIRS.md` for the reviewer instructions and integration boundaries. Claude must review its final SHA, then the original
feature branches must receive the appropriate commits and fresh reviews before merging. Other decisions remain open.

| PR | What | Note |
| --- | --- | --- |
| #42 | Forward-Deployed / AI Deployment / AI Implementation Strategist roles | Codex clean on b90c1d2; unchanged |
| #44 | Work at a Startup public pages | 1 finding: retain secondary discovery times; implemented on repair branch; Claude review pending |
| #45 | a16z portfolio jobs | 1 finding: same discovery-time issue; implemented on repair branch; Claude review pending |
| #46 | This status and handoff documentation | 1 finding: pinned uv in run prompt; implemented on repair branch; Claude review pending |
| #49 | Haiku-vs-Sonnet reading test (ran: 100 of 100 agree) | 1 finding: do not score unread items as agreement; implemented on repair branch; Claude review pending |
| #50 | E4: a reason for every rejected fact and every filter drop | 1 finding: do not echo unknown item text in traces; implemented on repair branch; Claude review pending |
| #52 | Claude-written, draft: MBA 2027 rule, pay fix, blank-cell checker, START_HERE (review vehicle on top of #51's branch; never merged as is) | Three Codex review rounds on this PR: round 1 (`781741a`, five P2) fixed in `63727b2`; round 2 (`8943862`, four P2) fixed in `bb9fb9a`; round 3 (`590131a`, four P2: negation, noun-first eligibility, unrelated years, prefix currency) fixed in the commit after `590131a` (the third and final authorized cycle, recorded in `docs/ATTEMPTS.md`). Waits for a final Codex review; a fourth cycle needs a new authorization |
| #51 | Codex-written repair PR: the ten review fixes (head `76e7788`, also in the run branch) | Claude review posted October 21 on `76e7788`: one finding (date-dependent tests) and one question; waits for Codex to fix and backport |
| #40 | X collector | 1 finding: dispose of cookie session after startup failures; implemented on repair branch; Claude review pending |
| #41 | Run modes: 28 days by hand, 3 days daily, refuses after a gap | No new findings on 4c0fe90; depends on #40 repairs |
| #43 | LinkedIn post collector | 1 finding: dispose of browser after startup failures; implemented on repair branch; Claude review pending; live collection held for A18 |
| #47 | Ali Rohde newsletter | 2 findings: tracking-link duplicates and generic-link role loss; implemented on repair branch; Claude review pending |
| #48 | LinkedIn job listings | 1 finding: reject aliased output paths before spending the day; implemented on repair branch; Claude review pending; live collection held for A18 |

### 0.4 What Claude does as soon as you answer

- A18: builds or closes what you choose; (a) waits on B1. A3: creates the routine with the agreed sources and Haiku reading.
- A12 answered: initial Codex reviews complete. Codex implements the authorized repairs in new commits, opens a fix-only
  PR for Claude review, and records its full head SHA. No merge or fresh cloud run is part of this repair request.
- A16, A17, A13, A19, A20, A21: one small PR each, with tests, then Codex.
- B9, B3, B10, B11: builds or retests the source with the address or name you give.
- A22: backs up the Jobs tab, archives, then removes the rows you approve. A23, A24: one small change each, with tests.

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
- A5: company boards keep the 28-day window. A6: no extra JSearch pages (free plan). A7 (first run): keep today's limits; revisit
  now (0.1).
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
| E4 | A reason for every rejected fact and every filter drop, printed by each run (`trace:` lines) and mapped in `docs/TRACEABILITY.md` | **built, PR #50**, Codex reviewed; privacy repair awaits Claude in the repair PR |
| E5 | Keep the reason counts in the Sheet so they outlive the session | proposed (A20) |
| E6 | Print why job boards drop jobs (role, place, pay) | proposed (A20) |
| E7 | Read pay written like `$190k-$220k` | your call (A17) |
| E8 | Fill the company of no-company posts with the poster's `@handle` | your call (A16) |
| E9 | X replies: keep them and fix the wrong comment, or filter them | your call (A19) |
| E10 | Record which search found each social post, so search wording can be tuned with numbers | proposed (A20) |
| E11 | A Run Log column for the AI queue counts | proposed (part of E5) |
| E12 | Only roles for MBA graduates of 2027 (`mba_class_evidence`), with drop reasons printed per source (`dropped=` in the probe table) | **built on the session branch** (not yet a PR); tests moved onto MBA 2027 wording |
| E13 | Pay read from Greenhouse, Ashby and posting text; found by your California/Anthropic observation: 134 of 170 blank pay cells on job-board rows were pay the employer had published | **built on the session branch** (not yet a PR); old rows are not back-filled (your answer: new rows only) |
| E14 | `scripts.field_audit`: flags a source that leaves a column blank far more than it publishes it, and `--cross-check` asks the live boards whether the blank cell was a gap in the source or in our reader | **built on the session branch** (not yet a PR); run it after every run, see PARAMETERS |
| E15 | Date bug in the X and LinkedIn tests (14 tests only passed on October 19) | **fixed on the session branch** (commit `144859f`); PRs #40, #41, #43, #47, #48 still carry the bug: their CI was green on October 19 and will turn red on any re-run |

## 4. Work that waits on a decision or task

| What | Waits on |
| --- | --- |
| Gmail alert collection (including LinkedIn alerts) | B1, B2 |
| Next Play newsletter reader | B9 |
| School/MBA sites and Cosign | B3 |
| Work at a Startup logged-in lists (the public page shows only 24 of 241 jobs) | B10 |
| LinkedIn collectors (#43, #48) | A18 |
| The daily routine | A3 |
| Merging anything | Resolve findings; current opposite-agent reviews and green CI; follow merge authorization |
| The small rule fixes | A13, A16, A17, A19 |

## 5. How runs work (your direction, October 18)

1. The first pull is a one-off manual run that looks back four weeks (done October 19).
2. Then you check the Sheet (A3).
3. Then the scheduled routine runs daily at 06:07 New York with a 3-day window; only new posts are read by the AI.

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

## 8. October 21, 2026 work log (what was checked and what is still unproven)

**Checked from the run's own record (not just its summary).** The run session's transcript shows the tools printed `valid=117
delivered=94 rejected=42 held_for_retry=34` (X) and `valid=66 delivered=45 rejected=0` (newsletter), and the probe table with 505 jobs
from 51 sources and `sync_verified ... unique_jobs=505`. These match section 1. The validator printed **no reason**, which is why the
empty-company cause rests on the run session's own reply ("all 39 failed for the same reason, the company field was empty; my brief told
the reader to leave it blank when the post names none, but the code requires a company") plus an offline test that reproduces the
rejection exactly. The saved fact files lived in a temporary folder that is gone, so they cannot be re-read. **Closed: no further re-check is
needed or possible.**

**The run session's declined re-check** (October 19, 23:02 UTC): the run session refused to send a second round of numbers to another
session, because you had told it to answer you only. That is the right behavior and nothing is outstanding from it.

**Offline proof that the report will copy the trace lines:** `tests/test_trace_prompts.py` runs the same commands as the live run
(`ai_queue pull`, `social_posts validate`) on a post with no company and checks that `trace:` and `trace_rejected:` lines are printed with
`empty:company`, that both prompts name those two line prefixes and say "unchanged", and that every reason code is explained in
`docs/TRACEABILITY.md`. **Still unproven until a real run:** that the run session actually copies the lines into its final report.

**Blank cells (your observation).** California rows from Greenhouse and Ashby had a blank Salary: those systems publish pay in a separate
field the program never requested. A live cross-check of the 170 blank job-board rows: 134 had pay published (our loss), 33 had none, 3 were
gone. 0 of 115 Greenhouse and 0 of 50 Ashby rows had pay; The Muse (179) and Lever (5) also 0. Fixed for new rows (E13). `scripts.field_audit`
(E14) is the standing check.

**Also found:** the X and LinkedIn collector tests only passed on October 19 (E15). `Rank (prelim)` is 3 on 600 of 710 rows and Fit, Next step
are blank on all rows; that is by design today (the ranking and fit scoring of the plan are not built), not a fault.
