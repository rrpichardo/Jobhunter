# Pending items: what only the user can do, what is blocked, what Claude continues

Created October 18, 2026 from the working session. This is the list to come back to.
When something is done, change its status here and in the PR that did it. Nothing
below is a claim that the work exists; `Status` says what is true. Branch and PR
numbers: #18 docs, #19 keep-every-match and 4-week window, #20 Hacker News,
#21 AI read-queue and draft routine prompt (each stacked on the one before).

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
| A4 | How to get Codex reviews while Codex is at its usage limit: wait for the reset, or try the local Codex CLI. | Claude-written PRs cannot merge without an opposite-agent review of the exact head. | open |
| A5 | Whether company boards should get a window wider than 28 days. Greenhouse dates can be years old for a role that is still open, so old-but-open roles are currently dropped. | Follows the "last 4 weeks" decision; widening is a user choice. | open |
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
| Merging #18 to #21 | A4 | A Codex review of each exact head, in order. |
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
  its detail-page stop no longer starves the tail.
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
- Retry Codex reviews when the limit resets, fix real findings, then merge in order.

## E. Pending deliverables the user asked for (not built)

| ID | Deliverable | What it should do | Status |
| --- | --- | --- | --- |
| E1 | **README** that explains every command | One page: what each command does, its inputs and outputs, the order of a run, how to do the first manual pull, and how to read the result. Written after the commands settle so it does not go stale. | pending |
| E2 | **A basic front end ("control page")** | See the Run Log and source health without the terminal, understand what happened, and change parameters such as searches per day and the top amount per tool, with a plain explanation of each. Options to decide together: a Sheet-based control tab, or a small local web page reading the Sheet. It must not become a local production dependency or add a hosting service, and the daily run stays cloud-only. | pending, design to discuss |
| E3 | A single place for every tunable limit | One config file the front end can edit. Today the limits are constants in code (see LIMITS.md). | pending |
