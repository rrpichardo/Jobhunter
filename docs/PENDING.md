# Pending items: what only the user can do, what is blocked, what Claude continues

Created October 18, 2026 from the working session; review status updated October 19. When something is
done, change its status here and in the PR that did it. Nothing below is a claim that the work exists;
`Status` says what is true.

## Status at the end of October 19, 2026 (read this first)

- **Landed:** the whole earlier stack (#18 to #30 plus the Codex fix PRs #32 to #38) is on `main` through PR #39
  (Codex-approved at `c6e5f30`, merged). Nothing has run against the real workbook since; the first manual run is
  still ahead.
- **Open, each waiting for a Codex review of its exact head:** #40 X collector (twscrape; startup fixed after an
  independent review found it crashed against the real library), #41 run modes (manual 28 days, daily 3 days, refuses
  after a gap), #42 Forward-Deployed AI Strategist roles, #43 LinkedIn hiring-post collector, #44 Work at a Startup
  public pages, #45 a16z portfolio jobs. #40 to #41 and #43 are stacked; #42, #44 and #45 are on `main`.
- **Codex has reached its usage limit** (October 19, about 16:31 UTC): every `@codex review` since answers "You have
  reached your Codex usage limits". Reviews must be re-requested when the limit resets or is raised
  (https://chatgpt.com/codex/cloud/settings/usage). Nothing Claude wrote is merged without that review.
- **Decisions recorded October 19:** A1 approved (LinkedIn, X, Work at a Startup); A3 only after a manual run is
  checked; A5 keep 28 days (the daily routine overlaps, see below); A6 no extra JSearch pages; A8 keep BizOps out but
  ADD "Forward-Deployed AI Strategist" and variants (#42). Run modes: first manual run 28 days, daily routine 3 days and
  it refuses (exit 3) when the last fully delivered run is more than about 2 days old.
- **Findings from today's reads (no login needed):** workatastartup.com answers 406 only when the request does not say
  it accepts HTML; the public role pages list the first ~25 jobs (the full lists need a logged-in session, optional).
  a16z lists ~25 jobs per search and each job page carries pay and date.
- **Next:** first live X and LinkedIn test from `docs/FIRST_LIVE_TEST.md` (needs A2); then LinkedIn job listings, whose
  page layout is learned from the post test's numbers-only diagnostics instead of guessed.

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
| A2 | Go-ahead for the first real social test (LinkedIn posts, then X). It spends that day's allowance for each source. | Live access to accounts that can be restricted. | open |
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
| B5 | Re-copy a cookie into JobHunterEnv only if a source later reports it is logged out. Never paste it in chat. | as needed |
| B6 | After the routine is live: rate leads in the Sheet and join the day-7 and day-14 reviews. | later |
| B7 | Later, when you ask: clean up old alert subscriptions in your main mailbox. Not authorized now. | deferred |
| B8 | Optional: rotate the Google service-account key. Recommended, not required. | optional |

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
