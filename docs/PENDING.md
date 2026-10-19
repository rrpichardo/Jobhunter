# Pending items: what only the user can do, what is blocked, what Claude continues

Created October 18, 2026 from the working session; review status updated October 19. When something is
done, change its status here and in the PR that did it. Nothing below is a claim that the work exists;
`Status` says what is true.

## 0. At a glance (the one place to look; Claude updates it in every change)

Last updated October 19, 2026, 22:45 UTC (the first live run is done, LinkedIn failed at login, see A2 and B5; you decided: Haiku reads, old PRs closed, run the live test now from a combined branch, keep today's limits for the first run; see A2, A7, A10, A11). When the user asks "what is pending", "what do you need from me" or
"where are we", Claude reads THIS section first, checks it against GitHub, answers in plain language, and fixes
this section if it is out of date.

**A. Waiting for your approval or answer**

| What | Where it stands |
| --- | --- |
| A2 First live X and LinkedIn test, then the first manual run | **DONE October 19 (about 22:17 to 22:36 UTC), with one source failed.** Run from `claude/combined-live-run` (commit `846f3be`), 1,056 tests passed, window 28 days, Haiku read the text, every command exited 0. **X worked:** 10 of 10 searches, 178 posts collected, 175 readable; Haiku wrote 156 facts; the checker accepted 117 and printed `rejected=42`, 94 were delivered as leads (23 accepted facts were dropped by the collection filter: role, region or pay), 34 posts were held for the next run. Reading the code (not the run's files): the printed `rejected` also counts posts that could not be read, so it is most likely 39 rejected facts plus 3 unreadable posts (178 collected minus 175 readable), which matches 156 minus 117; a rejected fact holds the post it names, so 34 held posts is just the posts that had at least one rejected fact (nothing was held wholesale). The checker rejects a fact if a quoted value is not word for word in the post, a value is too long or empty, or the apply link is not one of the post's own saved links; which of these happened is UNKNOWN (the run's first report guessed 'wording', which nothing confirms; one candidate is X's shortened `t.co` links versus the saved full links). **Ali Rohde newsletter worked:** 4 editions, 45 facts delivered (44 Sheet rows). **Hacker News:** 15 comments, all already read, nothing new. **a16z:** 26 jobs from 3 of its 4 searches (the Product page returned a temporary 503). **Sheet:** written on the first try in 4 batches; the readback verified 505 unique jobs from 51 sources. **LinkedIn did NOT work:** it refused the login on the first search (`social_login_failed`, a redirect loop), so the post and job-card lanes collected nothing and today's LinkedIn allowance is spent. The tool still exited 0, so only the printed words show the failure. **You must refresh the LinkedIn cookie (B5); the next LinkedIn attempt is tomorrow (New York date).** **Checked in the Sheet itself by Claude (read-only, October 19, about 22:50 UTC):** the Run Log has the live run as four batches of 150, 150, 150 and 55 (= 505, status `complete-with-source-failure`), the Jobs tab now holds 710 job rows (205 from before plus these 505), X rows are leads (a link to the post plus the quoted evidence, pay unresolved), and a sampled newsletter row has company, title, place and a direct apply link but no pay (pay unresolved), so newsletter rows sit between a lead and a full row. One thing is still open and only the run session's private folder can answer it: the reason counts for the rejected X facts (about a quarter; the eval showed none). Claude asked the run session (`session_015VLCYtHCKyG9e468TSVkUg`) for counts only, and that session correctly declined, because a message from another session is not your approval. **To get the answers, open that session in the Claude app and reply "Yes, answer the six questions to me only"** (it offers that as a suggested reply), or tell Claude to drop the question; the next real run will show the same numbers again. That session's temporary folder is lost if its container is recycled. |
| A15 DONE: backup copy | You said "copied" on October 19. The run wrote to the ORIGINAL Sheet; the copy is your undo. |
| A3 Create the daily routine | Only after a manual run is checked. |
| A4 Merging | You said (October 19) to merge what Codex approves and to use the `engineering:code-review` check in the meantime. |
| A10 DONE: old stack PRs #19 to #30 closed | Closed on October 19 at your request. All twelve heads were already inside `main` (checked), so nothing was lost. **Codex review chain, verified on GitHub October 19:** each of the twelve had its own Codex review (five had findings: #19, #21, #24, #25, #26, seven problems in all; the other seven had none of their own but depended on those five); the seven problems were fixed in #32 to #37, each with a Codex "Didn't find any major issues" on its exact final head (`d2b961e`, `6ce257f`, `dd7a0ac`, `e40aba2`, `042dedc`, `b63a9f5`); then all of it was landed as one combined PR, #39, which Codex reviewed in four rounds (findings in the first three, fixed) and cleared on its exact merged head `c6e5f30` at 15:35 UTC, merged at 16:07 UTC. The twelve PRs never got a separate clean approval on their own final heads; the combined review of #39 covers them. |
| A7 Search limits | **Decided October 19: keep today's numbers for the first live run** (X 10 searches; LinkedIn 5 post + 5 job searches; one session per source per day), then revise from its results. Every limit and setting is explained in plain language in `docs/PARAMETERS.md`. One editable file that the program reads for all numbers is planned as a separate PR after the first run (E3; section 13 of that file). |
| A11 DECIDED: Haiku does the reading | You said "haiku is good to go" (October 19). Evidence: `docs/evals/results/haiku_reading_2026-10-19.md` (100 of 100 posts agreed; on the 15 role posts both found the same 15 jobs; the location differences on posts 3 and 12 favour different models). The live test and manual run read with Haiku. To do when the routine is created (A3): name Haiku for the reading step in `docs/ROUTINE_PROMPT.md`. |
| A14 DECIDED: leave the old commits as they are | October 19: no history rewrite. Two cosmetic leftovers stay: (a) the first commit of #49's branch (`6cbc3ec`) still holds 29 third-party email addresses copied from public posts (removed from the current files; the repo is private); (b) six commits pushed after Claude's temporary git identity leaked into the shared settings show the author "trial merge (never pushed)" instead of Claude (`b90c1d2` on #42, `c5535dc` on #49, `c6abe19` `1fd2384` `793c515` on #46, `1c732a2` on #43; the settings are fixed and later commits are correct). If you ever want either fixed, say "rewrite"; it would change those commit IDs and void any Codex review tied to them. |
| A13 NEW: plural job titles | The title filter drops a post titled "Product Managers" (plural; the singular "Product Manager" is collected). The Haiku test found it: PlantingSpace's "Product Managers and Business Development" opening was proposed by both models and dropped by the filter. Should plural titles count? It changes what every source delivers, so Claude has not touched it. |
| A12 NEW: Codex is answering again | Claude sent ONE request (#42, 20:09 UTC) before you said not to try. Codex reviewed the exact head at 20:11 UTC and found one real problem (an engineer title that mentions "strategy" matched the new role family). Claude fixed it in `afedfb2`, replied and resolved the thread; a second independent review then tightened it further in `b90c1d2`. #42 now needs a Codex review of that new head. Claude has NOT sent it, because you asked it not to try Codex. Say "go" and Claude re-requests exact-head reviews one PR at a time, #42 first. |

**B. Your tasks** (only you can do them; details in section B below)

1. B9 NEW: tell Claude the address (web link) of the Next Play newsletter you actually read. The link Claude found, `nextplay.substack.com`, is a 2021 publication and is not it.
2. B1 Gmail forwarding filter (the Gmail alerts reader waits on it).
3. B2 Turn on alerts from Indeed, Glassdoor, Lenny's/TrueUp.
4. B3 School/MBA job sites and the correct Cosign link.
5. B4 Gmail connector permissions to "Needs approval".
6. B8 Optional: rotate the Google service-account key.
7. Before the live test: copy the spreadsheet (File > Make a copy).
8. B10 NEW (optional, only for the logged-in Work at a Startup lists): the saved `WAAS_SESSION_COOKIE` is a bare value with no cookie name, so Claude cannot tell which cookie it is. Re-save it as `name=value` (the browser's cookie name, an equals sign, then the value) or tell Claude the cookie's name. Never paste the value in chat.

**C. Waiting on Codex (usage limit reached about 16:31 UTC on October 19; one request at 20:09 UTC was answered at 20:11 UTC)**

Check or raise the limit at https://chatgpt.com/codex/cloud/settings/usage. The full list of what to review, each PR's exact head, what Codex has already done on it and a ready-to-paste request for each is in `docs/CODEX_REVIEW_QUEUE.md`. No scheduled sweep exists any more, so Claude re-requests
reviews by hand (one PR at a time) once you say "go" (A12), and fixes what Codex finds. Until then each open PR carries an interim review in the style of the
`engineering:code-review` skill (done by independent reviewers, October 19; their findings were fixed), posted as a PR
comment that says Codex still has to review it.

| PR | Plain name | Needs |
| --- | --- | --- |
| #40 | X (Twitter) hiring-post collector | Codex review of the current head (Codex answered seven rounds on earlier heads before its limit; all findings were fixed; the interim review on the PR names the current head `5ceb6cc`); base of #41, #43, #47 |
| #41 | Run modes: 28 days by hand, 3 days daily, refuses after a gap | Codex review of the current head (three earlier Codex rounds were fixed; its interim review covers the current code, because the only later change is six documentation lines); after #40 |
| #42 | Forward-Deployed / AI Deployment / AI Implementation Strategist roles | Codex reviewed `62fc1be` and found 1 issue (fixed in `afedfb2`, thread resolved); an independent review of that fix found bare `FDE` titles still passing (fixed in `b90c1d2`); needs Codex review of `b90c1d2` |
| #43 | LinkedIn hiring-post collector | Codex review (after #40) |
| #44 | Work at a Startup public pages | Codex review |
| #45 | a16z portfolio jobs | Codex review |
| #46 | This status document | Codex review |
| #47 | Ali Rohde Jobs weekly newsletter | Codex review (after #40) |
| #49 | Haiku-vs-Sonnet eval harness, a bug fix, the first result and the fixes from an independent review (head `82bd0d4`; it now also holds a run record of what the two helper agents did) | Codex review |
| #48 | LinkedIn job listings (same session as the posts) | Codex review (after #43) |

**Haiku vs Sonnet eval: RUN once on October 19, 2026 (Hacker News only). Verdict: not yet (your rule 3 is open, A11).**
On 100 real posts (15 name a collected role, 85 do not) both models gave the same answer on all 100 and found the same 15 jobs; neither
had a value rejected for not being in the post. The score looks only at title and company, so four facts that differ in location, salary or
company wording are listed separately. The run also exposed a bug in the test tool (fixed, with tests, in PR #49) and the plural-title gap
(A13). An independent review corrected the first write-up: 14 of the 15 role posts delivered a job, all 100 posts came from one thread, and
the two location differences favour different models. Not yet tested: X, LinkedIn and newsletter posts. Details: `docs/evals/results/haiku_reading_2026-10-19.md`; the plan is `docs/evals/HAIKU_READING_EVAL.md`.
Until you answer A11 the reading stays on Sonnet.

**E. Possible later add-on (Work at a Startup logged-in lists).** A read-only probe on October 19 found that the public product page shows 24 of 241 jobs and has no paging. It could not test the logged-in lists, because the saved `WAAS_SESSION_COOKIE` has no cookie name (B10). Once that is fixed, Claude retests and, if the logged-in lists show more, builds them (A1 is approved, read-only).

**D. Claude's next steps:** the merge order and the exact conflict fixes were checked by a trial replay (all ten PRs combined pass 1,056 tests; see the "Merge plan" table in `docs/CLAUDE_HANDOFF.md`). When Codex is back: review, fix, merge in order (#42, #44, #45, #46, then #40 and the PRs
stacked on it). Then the live X and LinkedIn test, then a first manual run, then A3.

**Decisions already made (do not ask again):** A1 build LinkedIn, X and Work at a Startup (read-only); A3 create the daily
routine only after a checked manual run; A5 keep 28 days; A6 no extra JSearch pages; A7 keep today's search limits for the first
live run and revise afterwards; A8 BizOps stays out, and the Forward-Deployed / AI Deployment / AI Implementation Strategist
titles are in; A10 the old PRs #19 to #30 are closed; A11 Haiku does the reading step (a bigger Haiku test was offered and
declined: "with 100 we are good"); first manual run 28 days, daily routine 3 days; **the first live test and manual run happen
now from the combined run branch without waiting for Codex (October 19), but nothing is merged to `main` without a Codex review
of its exact head and green CI**; old commits keep their "Claude-Session" line (see below).

**About the old "Claude-Session" lines.** Some of Claude's older commits end with a line linking to the chat session
that wrote them. They were left in on purpose: removing them would mean re-creating those commits, which voids every
Codex approval tied to them and forces all reviews again. The link only opens for the account owner and carries no
secret. Newer commits omit it. This note is the explanation; nothing is hidden.
A slip on October 19: 21 of Claude's commits that day (the haiku eval, docs and run-branch work) also carry the line
(`session_01BLQ4Yve4ZCKG4cPmidzTSc`), against that convention. They are treated like the older ones: left as they are, and
new commits omit it from now on. Codex flagged the same thing on #39 (its thread is the one left open on purpose); when
asking Codex to review, tell it this is known and decided so it is not raised again. If you ever want these lines scrubbed
too, say "rewrite" (same cost as A14: new commit IDs, reviews tied to them void).

**Codex reviews work** (history of the earlier round) (GitHub app, `@codex review` on a PR; it sometimes answers "unknown error", which
is a failed run and not a verdict, so the request is simply repeated). On October 19 Codex reviewed every
Claude-written PR and found seven real problems in five of them. Each fix is its own PR on the exact head
Codex reviewed, and Codex has approved all six at the heads below:

| Original PR | Codex finding (short) | Fix PR | Approved head |
| --- | --- | --- | --- |
| #19 | Large first pull rejected by the 5 MiB input limit | #32 | `d2b961e` |
| #21 | A misread Hacker News comment was marked read and lost; run labels could collide | #33 | `6ce257f` |
| #24 | A broken Jobicy item aborted the run; later-page failures were not recorded | #34 | `dd7a0ac` |
| #25 | Pages opened but not delivered starved the rest of a big source | #35 | `e40aba2` |
| #26 | The daily social allowance could not be closed after midnight (New York) | #36 | `042dedc` |
| #27 | Same lost-post bug in the X/LinkedIn validator | #37 | `b63a9f5` |

The earlier "Codex at its usage limit" note no longer applies. Merge order is still the stack order, each
fix PR first into the PR it repairs. #22, #23, #28, #29 and #30 had no findings of their own, but Codex said
their review does not cover the fixes beneath them, so each still needs a fresh exact-head Codex review after
the fixes are merged into the stack.

| PR | What | Tests at its head (before the fix PRs) |
| --- | --- | --- |
| #18 | Docs handoff (Codex wrote it, Claude reviewed `4177f4e`; Claude's two commits need Codex) | docs only |
| #19 | Keep every match, writer batches, 4-week window, `posted_at` | 615 |
| #20 | Hacker News comments with code-validated facts | 636 |
| #21 | AI read-queue in `_State` and the draft routine prompt | 661 |
| #22 | This register, LIMITS.md, README and front-end plan items | docs only |
| #23 | Safety-stop flags for the first manual pull | 670 |
| #24 | Paging for The Muse and Jobicy (fixes The Muse skipping page one) | 679 |
| #25 | Skip job pages for jobs already in the Sheet | 689 |
| #26 | Daily social allowance guard | 722 |
| #27 | Shared validator for X and LinkedIn posts | 760 |
| #28 | Wait out Sheets quota errors, pace batches 45 s, retry lock reads (found by the first real pull) | 768 |
| #29 | A source whose good jobs are all already delivered is not marked failed (found by the rerun) | 770 |
| #30 | Docs: how each source is read | 770 |

## First manual pull: status (October 19, 2026)

An earlier cloud session recorded one manual pull of the public sources in JobHunterEnv (details and its
limits in V0_VERIFICATION.md): 322 jobs from 46 sources in three paced batches, 478 job rows with no duplicate
IDs, the writer lock released, and the 28 Hacker News comments marked read. The first attempt hit Google's
quota and left a lock; the fix is PR #28 and the lock was removed with the user's approval. This is
historical evidence recorded by that session. It was not re-run or independently verified during the Codex
reviews, and it is not proof that the current code or environment works. Still true:
`getro-accel` shows `failed` until its fix (#29) runs; LinkedIn, X, Gmail, Work at a Startup, school sites and
the scheduled routine have NOT been run; nothing is merged. The next gate is the next-morning check of the
routine's first scheduled run, which needs A3 and the code on `main` (A4: your go-ahead to merge; Codex has reviewed the fix PRs).

## How the first run and the daily runs work (user direction, October 18)

1. **First pull is a one-off manual run, not the scheduled routine.** It looks back
   four weeks. Safety limits are relaxed or ignored for it where we can (see
   LIMITS.md; some sources still return only what their own API allows, and those are
   listed as gaps in BACKFILL_WINDOWS.md). Some sources will have limits and some
   will not; that is to be discussed source by source.
2. **Then wait until the next morning and check** the Sheet and Run Log.
3. **After that the scheduled routine runs daily** at 06:07 America/New_York with the
   normal limits, and only new jobs are read by the AI.

## A. Needs the user's approval (yes or no)

| ID | Decision | Why it is blocked | Status |
| --- | --- | --- | --- |
| A1 | Cloud collection method for Work at a Startup (headless browser, saved cookies, visible job cards only), LinkedIn (headless browser, `li_at`) and X (`twscrape`, `auth_token`/`ct0`). All read-only with random pauses. | The plan says to settle this in plain language first. Reading private requests from the logged-in tab was blocked earlier and must not be retried. | open |
| A2 | Go-ahead for the first real social test (LinkedIn posts, then X). It spends that day's allowance for each source. | Live access to accounts that can be restricted. | GIVEN October 19: run after Codex approves and #40 and #43 merge |
| A3 | Create the `JobHunter Daily` routine (06:07 New York, repository `rrpichardo/Jobhunter`, environment `JobHunterEnv`). Claude can do the clicking. | Creating a standing scheduled job. `docs/ROUTINE_PROMPT.md` is a draft and is not installed. | open |
| A4 | Codex reviews: answered. They work through the GitHub app (see the top of this file). What is still open is your go-ahead to merge, in stack order. | Claude-written PRs merge only on your explicit direction. | go-ahead needed |
| A5 | Whether company boards should get a window wider than 28 days. Greenhouse dates can be years old for a role that is still open, so old-but-open roles are currently dropped. | Follows the "last 4 weeks" decision; widening is a user choice. | decided: keep 28 days |
| A8 | DECIDED October 19: keep BizOps out; add Forward-Deployed AI Strategist (#42). Original question: should "business operations" / BizOps become a collected role family? Today it is not one: the delivery filter has no such family, so Hacker News no longer sends those comments to Claude and the routine does not ask for them. Adding it changes what every source delivers. | Scope change for all sources. | decided (keep out) |
| A6 | JSearch paging. The free plan allows about 200 requests a month and one page holds about 10 jobs. More pages for the first pull need approval. No new spending. | Quota, possible cost. | open |
| A7 | Which limits to tune and to what (LIMITS.md), for example "50 a day". | Includes the LinkedIn account-restriction risk. 50 searches a day was declined for now. | open |

## B. Only the user can do these

| ID | Task | Status |
| --- | --- | --- |
| B1 | Gmail forwarding filter. In the dedicated job-alert Gmail, make a filter from a real alert that forwards to the Claude-connected Gmail and excludes security, login, verification and reset mail. In the connected Gmail, add a filter that applies the `JobHunter` label. Confirm one fresh alert arrives at both ends. Claude hit an unexpected screen three times and stopped. | open |
| B2 | Turn on job alerts from the other providers: Indeed, Glassdoor, Lenny's/TrueUp, Next Play newsletter. | open |
| B3 | Send the names and URLs of the school/MBA job sites you want, and the correct Cosign URL (`cosign.com` is a parked domain). If a site needs a login, log in yourself and put the cookie in JobHunterEnv settings. | open |
| B4 | In the Claude Gmail connector settings, change Delete label, Mark spam, Trash and Remove labels from "Always allow" to "Needs approval". | open |
| B5 | **NEEDED NOW for LinkedIn:** the first live run (October 19) was refused at login (`social_login_failed`). In JobHunterEnv, re-copy a fresh `li_at` cookie from the dedicated LinkedIn account (log in normally in a browser first, check the account has no warning or verification prompt), save it as `LINKEDIN_LI_AT`, and tell Claude. LinkedIn can next be tried tomorrow (New York date). Never paste a cookie in chat. For other sources: re-copy only if a source later reports it is logged out. | open (LinkedIn) |
| B6 | After the routine is live: rate leads in the Sheet and join the day-7 and day-14 reviews. | later |
| B7 | Later, when you ask: clean up old alert subscriptions in your main mailbox. Not authorized now. | deferred |
| B8 | Optional: rotate the Google service-account key. Recommended, not required. | optional |
| B9 | Tell Claude the web address of the Next Play newsletter you read (the `nextplay.substack.com` feed is a 2021 publication, not it). Claude then builds its reader like the Ali Rohde one (#47). | open |
| B10 | Only for the logged-in Work at a Startup lists: the saved `WAAS_SESSION_COOKIE` has no cookie name. Re-save it as `name=value` or tell Claude the name. Never paste the value in chat. | optional |

## C. Work Claude cannot finish until A or B is done

| What | Blocked by | What unblocks it |
| --- | --- | --- |
| Gmail alert collection from real mail | B1, B2 | A real forwarded alert with the `JobHunter` label, then the live connector adapter can be tested. |
| Next Play and Ali Rohde feeds | B2 and feed URLs | Verified feed URLs. Claude will try to find them; if it cannot verify, it asks. |
| LinkedIn jobs and hiring posts collector (live part) | A1, A2 | Approval; then a real run within the day's allowance. Code and offline tests can proceed before. |
| X hiring posts collector (live part) | A1, A2 | Same. |
| Work at a Startup (logged in) | A1 | Approval of the browser route. |
| School/MBA sites, Cosign | B3 | URLs and any logins. |
| Installing and running the daily routine | A3 and a proven first pull | Approval, then a first manual pull and a next-morning check. |
| Merging #18 and the stack | A4 (your go-ahead) | Codex has approved the fix PRs #32 to #37; #18 and #20 to #30 still need a fresh exact-head review after the fixes land. |
| Hacker News and the AI queue running in the cloud | A3 | The routine prompt installed; nothing has run in JobHunterEnv yet. |

## D. Claude continues without waiting

- DONE on branch `claude/limit-flags`: per-run flags so the first manual pull can
  raise the safety stops (`--detail-safety-stop`, `--candidate-safety-stop`,
  `--batch-pause`, `ai_queue pull --limit`), recorded in LIMITS.md.
- DONE on branch `claude/paging`: The Muse (was skipping its first page) and Jobicy now
  page; Remotive and Remote OK checked and already complete for 28 days. Himalayas
  cannot be fixed by paging (20 per page, dates look refreshed daily). Jooble paging
  and JSearch paging still wait on A6 and a quota decision.
- DONE on branch `claude/known-ids`: `scripts.known_ids` + `source_probe --known-ids` skip
  job pages for jobs already in the Sheet, so a big source is not reopened daily and
  its detail-page stop no longer starves the tail. Delivered IDs alone did not fix this for
  pages inspected but not delivered; a date-based rotation of the detail window now does
  (half the stop stays in priority order; see BACKFILL_WINDOWS.md).
- A Run Log column for the AI queue counts (a Sheet schema change, done carefully).
- DONE on branch `claude/social-allowance`: the daily allowance reservation in `_State`
  (`scripts.allowance reserve/finish/status`; exit 3 means spent, any other failure
  means collect nothing).
- DONE on branch `claude/social-post-facts`: the validation half of X and LinkedIn
  hiring posts (`jobhunter/post_facts.py`, `scripts.social_posts validate`,
  `source_probe --social-result`): canonical post URLs, verbatim facts, code-derived
  Job IDs, the post URL as the lead link. Hacker News now shares that validator.
- STILL TO BUILD, one PR each: the LinkedIn collector and the X collector that fetch
  the posts (they need the approved method A1 and the pinned library or browser
  setup, and a live run needs A2). No live access before then.
- Keep requesting a Codex review of every new exact head and fix real findings. Merging is NOT part of
  this list: it stays blocked on A4 (the user's explicit go-ahead), however many reviews are clean.

## E. Pending deliverables the user asked for (not built)

| ID | Deliverable | What it should do | Status |
| --- | --- | --- | --- |
| E1 | **README** that explains every command | One page: what each command does, its inputs and outputs, the order of a run, how to do the first manual pull, and how to read the result. Written after the commands settle so it does not go stale. | pending |
| E2 | **A basic front end ("control page")** | See the Run Log and source health without the terminal, understand what happened, and change parameters such as searches per day and the top amount per tool, with a plain explanation of each. Options to decide together: a Sheet-based control tab, or a small local web page reading the Sheet. It must not become a local production dependency or add a hosting service, and the daily run stays cloud-only. | pending, design to discuss |
| E3 | A single place for every tunable limit | One config file the front end can edit. Today the limits are constants in code (see LIMITS.md). | pending |
| E4 | Show why facts are rejected | `social_posts validate` and `hn_hiring validate` print only a total (`rejected=N`), and it mixes unreadable posts with rejected facts. A small change would print counts by reason (quote not found, link not allowed, empty or too long, unknown post) so the next run explains itself. Proposed after the first live run (X rejected about a quarter of its facts, cause unknown); needs a PR and a Codex review like any code change, so it waits for your go. | proposed |
