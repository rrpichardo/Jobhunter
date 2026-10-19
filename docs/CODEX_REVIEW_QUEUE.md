# Codex review queue: the PRs waiting for a review when credits return

Written October 19, 2026. These are the open PRs that still need a **Codex review of their exact current head** before they
may be merged (the project rule in `docs/REVIEW_WORKFLOW.md`: Claude builds, Codex reviews; only a completed review of
the exact head, plus green CI, counts; a usage-limit reply or "no findings" without a review never does). Claude's own
interim reviews on the PRs are useful but are **not** a substitute.

Codex reviews work from the GitHub app (`@codex review`). It answered a request on October 19 at 20:11 UTC, after a usage-limit
stretch from about 16:30. Check or raise the limit at https://chatgpt.com/codex/cloud/settings/usage.

## How to request a review (one PR at a time)

1. **Re-read the live head**: heads move whenever a fix or merge is pushed. List them with the GitHub tool
   (`list_pull_requests`, fields `number` and `head`) or `gh pr view <n> --json headRefOid`. The SHAs below are a snapshot.
2. Start the watcher first (so an immediate usage-limit reply is seen):
   `scripts/wait_codex_review.sh <pr> <full-head-sha> [minutes]` (exit 0 clean, 1 findings, 2 usage limit, 3 timeout or changed head).
3. Post the request comment on the PR: `@codex review <full head SHA>`, the criteria from the block for that PR below, and
   "Review only: do not implement fixes." End the comment with the Claude Code footer.
4. If Codex reports findings, fix them in NEW commits (never rewrite history), reply on each thread with the commit,
   resolve the thread, push, and request a fresh review of the new head.
5. Merge only when the review covers the exact current head and CI is green. Then follow the merge order and conflict
   recipes in `docs/CLAUDE_HANDOFF.md` ("Merge plan").

## Order and dependencies

`#42` then `#44` then `#45` then `#46` then `#49` then `#40`; after `#40` merges, retarget `#41`, `#43`, `#47` to `main`
(merge `main` into each first); `#48` last (it carries `#43`). Small PRs first so credits are not spent on a stack that
is still moving. Do not spam: one request per PR, then wait.

## Snapshot (heads as of October 19, 2026, about 22:15 UTC)

| PR | What it is | Base | Head (full SHA) | Codex so far |
| --- | --- | --- | --- | --- |
| #42 | Collect Forward-Deployed AI Strategist roles and name variants | main | `b90c1d2befc12095f04b2b7340d745a88a88f27d` | Reviewed `62fc1be`: 1 finding (engineer titles with "strategy" matched), fixed in `afedfb2`; an independent review then tightened it in `b90c1d2`. **Needs review of the current head.** |
| #44 | Work at a Startup: public product and operations pages | main | `209efbc7ca2b0cd253dcca26e1720b5e55b8cd67` | none yet (limit hit before) |
| #45 | a16z portfolio jobs: four searches and each job's page | main | `e9d29ecea4384c96e2eb14071c9468caff9296f4` | none yet |
| #46 | Status, handoff, parameters guide, this queue (docs only) | main | re-read from GitHub (changes with every docs update) | none yet |
| #49 | Haiku-vs-Sonnet eval tool, fix, first result, run record | main | `82bd0d499405429842b87295fd7eccec0ca4b66a` | none yet |
| #40 | X (Twitter) hiring-post collector | main | `5ceb6ccf739485d60b173be2da35d783951f2490` | Seven rounds on earlier heads, all findings fixed; the final heads were never reviewed (limit). **Needs review of the current head.** |
| #41 | Run modes: 28 days by hand, 3 days daily, refuse after a gap | #40 | `4c0fe90d8bfb47b3f24114b494206c24a9ef1bab` | Three rounds on earlier heads, findings fixed; current head not reviewed. Interim review covers the current code (the last commit is documentation). |
| #43 | LinkedIn hiring-post collector (read-only headless browser) | #40 | `352309dfa68139631dc32ac8ea8c40b06fcb1e76` | none yet |
| #47 | Ali Rohde Jobs weekly newsletter | #40 | `9400d18c7d7a65f7030708c45d82c46b7eea342e` | none yet |
| #48 | LinkedIn job listings (same session and allowance as the posts) | #43 | `9a866685663136f21560a30f9202d330fc5c9779` | none yet |

(PRs #19 to #30, the old stack, were closed on October 19 at your request; their content is in `main`.)

## Ready-to-paste requests (replace `<SHA>` with the live full head SHA)

All of them end with: `Review only: do not implement fixes. Read AGENTS.md and docs/PLAN.md first.`

**#42**
> @codex review <SHA>. Check: (1) the "Forward-deployed strategy" family in `jobhunter/postings.py` matches Forward-Deployed AI Strategist and its variants (AI Deployment Strategist, AI Implementation Strategist, Deployment Strategist, FDE Strategist) and nothing else; (2) no title naming an engineer or developer (Engineer, Eng., Engr, Dev, SDE, SWE, Software Development) can be delivered through this family, whatever the separator or word order; bare "FDE ... strategy" without the noun "strategist" does not match; (3) the patterns cannot be slow on long titles; (4) the other role families and their order are unchanged. Earlier Codex finding on 62fc1be was fixed in afedfb2; b90c1d2 tightened it after an independent review.

**#44**
> @codex review <SHA>. Check: (1) only the two public Work at a Startup role pages are read, with no login and no cookie; the request says it accepts HTML (the site answers 406 otherwise); (2) the embedded page data is parsed defensively, with no value guessed, and job IDs stay inside the allowed characters; (3) the detail-page cap and polite delay apply; (4) jobs already in the Sheet are skipped and nothing is delivered twice; (5) eligibility is left to the shared filter; (6) no wording claims it ran against the real workbook.

**#45**
> @codex review <SHA>. Check: (1) the four a16z searches (product manager, chief of staff, strategy, founder in residence) read only the first page of each and then each shortlisted job's own page; (2) company, place, pay and posting date are parsed from the page, with the links validated; (3) caps and delays apply; (4) known Job IDs are skipped; (5) it merges with #44 once both sides of the `DETAIL_SOURCES` and registry lists are kept.

**#46**
> @codex review <SHA>. Docs only. Check that `docs/PENDING.md`, `docs/CLAUDE_HANDOFF.md`, `docs/PARAMETERS.md` and `docs/CODEX_REVIEW_QUEUE.md` match the code and the PR list: every number in PARAMETERS against the constants it names, every head SHA in the handoff against GitHub, and that no secret, cookie value or personal data is included.

**#49**
> @codex review <SHA>. Check: (1) `scripts/eval_reading.py` judges two models only through the pipeline's own checker (`post_facts.build_result`), the sample is deterministic for a seed, and the empty-apply-link fallback is chosen by id field; (2) `docs/evals/results/haiku_reading_2026-10-19.md` and its inputs match each other (100 posts, 15 jobs each, the four field differences, 14 of 15 role posts delivering a job) and make no claim the saved files cannot support; (3) the saved sample has third-party emails replaced; (4) the "How to repeat" steps work as written.

**#40**
> @codex review <SHA>. Acceptance criteria used in every earlier round: (1) read-only: no login, post, like, follow or message; (2) the daily allowance is reserved in `_State` before any request, a spent day or any ambiguous failure collects nothing, and the day stays spent whatever the outcome; (3) cookies come only from `X_AUTH_TOKEN` and `X_CT0`, go only into a private temporary database that is deleted, and never appear in output, the candidate file, exceptions or logs (check the error paths); (4) twscrape telemetry is off before import; (5) the adapter's calls match twscrape 0.20.1 and nothing claims it ran against X; (6) the candidate file is cleaned by the shared code and flows through `ai_queue pull` and `social_posts validate`; (7) limits (10 searches, 200 posts, 40 per search) and randomized pauses are enforced. Latest fixes since the last Codex round: posts dated before the window are dropped; the library and cookie import start before the allowance is reserved; cookie values are cleaned.

**#41**
> @codex review <SHA> (base `claude/social-collectors`, or `main` after #40 merges). Check: (1) `--mode daily` never prints a window when the last complete run started more than 2 days 6 hours ago, or when there never was one, and exits 3; (2) it is read-only (no write, no lock) and `--mode manual` needs no Sheet; (3) only runs with a complete status and a completed time count, a batched run counts only when every batch is delivered, and a corrupt Run Log fails closed; (4) the Run Log header and status names match what the writer really writes; (5) `docs/ROUTINE_PROMPT.md` uses the guard correctly and the window reaches both `hn_hiring candidates` and `source_probe`; (6) no wording claims it ran against the real workbook.

**#43**
> @codex review <SHA> (base `claude/social-collectors`, or `main` after #40 merges). Check: (1) read-only headless browser, no typing, clicking posts, liking or messaging (only "see more" expanders); (2) the allowance is reserved before the first request, but the browser and the cookie are loaded BEFORE it, so a local failure spends nothing; (3) the `li_at` cookie goes only into the browser context in memory and never appears in output, files, exceptions or logs; no user-agent override; (4) the card reader cannot feed page furniture to the AI (card boundaries, short cards, ready wait), and a login wall, 999/403 or a sign-in form is recorded as `social_login_failed` while an unrecognised layout is a collector error, not a healthy zero; (5) limits (5 post searches, 100 posts, 30 per search) and 3 to 9 second pauses apply; (6) the candidate file flows through `ai_queue pull` and `social_posts validate`; (7) `docs/FIRST_LIVE_TEST.md` matches the commands and output lines.

**#47**
> @codex review <SHA> (base `claude/social-collectors`, or `main` after #40 merges). Check: (1) only the fixed Ali Rohde feed host is read, with the standard-library client (the site blocks httpx); (2) at most 12 recent editions, inside the window; each edition is read like a post and its jobs are keyed by their application link; (3) every value must be word for word in the edition, and Job IDs stay inside the allowed characters; (4) nothing is delivered twice.

**#48**
> @codex review <SHA> (base `claude/linkedin-posts`, or `main` after #43 merges). Check: (1) job cards are read in the same browser session and under the same single allowance as the posts; if the post searches are refused the job searches are not attempted and the same error word is recorded for both; (2) the job date is the capture day minus the card's age ("3 days ago"), and a card with no readable age takes the capture day; (3) the card text goes to the AI read step so no markup guessing decides a field; (4) the two output files must differ and a doomed jobs path spends nothing; (5) limits (5 job searches, 125 cards, 30 per search) apply; (6) the runbook's job lines match the collector's real output.

## Not a Codex task

A **combined run branch** (`claude/combined-live-run`, all ten PRs merged with the documented conflict fixes, 1,056 tests passing) exists
only so the live test and first manual run can happen before these reviews. It is never merged to `main`; the individual PRs
above are what get reviewed and merged. Running unreviewed code against real accounts was your decision on October 19.
