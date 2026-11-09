# START HERE: what you answer, what you do, what you approve, what Codex does, what Claude does

Updated November 8, 2026 (checked against GitHub that day). Plain language. This is the short version of `docs/PENDING.md` section 0 (same IDs, kept in step with it).
Your answer sheet is `docs/DECISIONS_FORM.md`, or the Excel version `docs/JobHunter_Questions.xlsx` (questions, tasks, approvals, yellow cells to fill in); you can also just answer in chat.

## Where we are, in five lines

1. The program collects jobs and writes them to your Google Sheet. It ran for real once (October 19): 505 jobs. LinkedIn was refused; X, the newsletter and the job boards worked.
2. **All eleven original pull requests (#40 to #50) are now in the real program (`main`)**, merged October 21.
3. You told us what you actually want: **only jobs meant for MBA graduates of 2027.** That rule, the **blank salary** fix (California, Anthropic) and a checker for blank columns are now in the real program too: **PR #53 merged on October 23** (merge commit `d28732b`). Codex reviewed it through nine repair rounds; its last review, of the exact final version `b41a214`, found nothing, and the automatic checks were green.
4. #52 (the older version of that work) was closed unmerged on October 23; #53 replaced it. Nothing else has merged since. **PR #54** (an offline search-coverage audit, draft, opened October 27) is open and has had no review yet.
5. Nothing in your Sheet was changed by this update. As far as the repository shows, no new real run has happened since October 19 (the Sheet itself was not re-checked on November 8).

## 1. What YOU need to answer (most important first)

Say "take your recommendations on the small ones" to accept every suggestion in the second table at once.

| # | ID | Question in plain words | My suggestion |
| --- | --- | --- | --- |
| 1 | A22 | **Erase the old rows that are not for MBA 2027?** You said yes. A first count (`docs/MBA_CLEANUP_DRYRUN.md`, October 21): 1 row is clearly MBA 2027, 3 are new-grad roles with no MBA mention, 164 were read in full and are not, and 542 cannot be judged (only 300 characters were saved). The rule changed a little since, so that count is old. | The MBA rule is merged now (October 23), so I can recount (read only) and show you the list. Then say "go": I back up the whole tab, copy the rows to an archive tab, then remove them from the main tab. Nothing is lost. Or choose "only the rows read in full". |
| 2 | A25 + B11 | **Where should MBA 2027 jobs come from?** The company job boards have almost none (2 of 6,812). Name the companies with MBA programs (General Motors first), school or MBA job sites, and any web addresses you know. | I build a reader for each program you name. |
| 3 | A24 | Sierra has "Strategist, Agent Development (MBA Grad 2027)". It is for MBA 2027 but is not a product-manager title, so we drop it. **Accept any business role that clearly says it is for MBA 2027?** | Yes. |
| 4 | A23 | **New-grad 2027 roles that do not mention an MBA** (Databricks and Figma associate product manager). They ask for a bachelor's or master's in computer science. Include them? | No. We show the count of dropped ones in every run. |
| 5 | A18 | **LinkedIn** refused our login. What now? | Read your LinkedIn job-alert emails through Gmail (needs your task B1) and rely on JSearch and Jooble; keep the LinkedIn code on hold; remove the LinkedIn cookie setting so the daily run does not knock with a bad cookie. |
| 6 | A3 | **Create the daily routine** (06:07 New York, 3-day window)? | Yes, after you look at the Sheet; better after items 1 and 2 too, so it runs with the right rules and sources. |

Small ones (each has a default if you say "take your recommendations"):

| ID | Question | My suggestion |
| --- | --- | --- |
| A16 | X posts that name no company ("we are hiring, DM me"): show them under the poster's `@handle`? | Yes |
| A17 | Read pay written like `$190k-$220k` in X and Hacker News posts as yearly dollars? | Yes |
| A13 | Accept plural titles ("Product Managers")? | Yes |
| A19 | Keep X replies (they were real jobs)? | Yes |
| A7 | Change the X search wording now? | No, keep it a week |
| A20 | More tracing: keep rejection reasons in the Sheet (E5), record which search found each post (E10)? | Yes to both |
| A21 | Order of the bigger pieces: settings file (E3), README (E1), control page (E2). | E3, then E1, then E2 |

## 2. What YOU need to DO (only you can)

| ID | Task |
| --- | --- |
| B11 | Send me the names (and web addresses if you know them) of company MBA programs to watch. General Motors first. |
| B3 | Send the school or MBA job sites you want, plus the correct Cosign address (`cosign.com` is a parked domain). If a site needs a login, log in yourself and put the cookie in the JobHunterEnv settings. Never paste a cookie in chat. |
| B1 | In the job-alert Gmail, set up a forwarding filter to the Claude-connected Gmail (excluding security and password mail), and a filter that adds the `JobHunter` label. Steps are in `docs/PENDING.md`. |
| B2 | Turn on job alerts from Indeed, Glassdoor and Lenny's/TrueUp. |
| B4 | In the Claude Gmail connector settings, change Delete label, Mark spam, Trash and Remove labels from "Always allow" to "Needs approval". |
| B9 | Tell me the web address of the Next Play newsletter you read. |
| optional | B8 rotate the Google service-account key; B10 the name (never the value) of the Work at a Startup cookie. |
| later | B6 rate leads in the Sheet once the daily routine is live. |

## 3. What you need to APPROVE (a clear "go" each time)

| When | What |
| --- | --- |
| Now possible (the MBA rule merged October 23) | **A22**: erasing the old rows, on a fresh list (item 1 above). I will not touch the Sheet without it. |
| After items 1 and 2 | A **real run** (writes new rows to the Sheet and uses that day's single X attempt). It also proves the run report copies the `trace:` lines, the last unproven piece. |
| After the real run | **A3**: creating the daily routine. |
| Later | Closing **PR #51** (Codex's repair PR). Its fixes reached `main` through #40 to #50. Nothing happens to it without your go. |

Merges need no new "go" from you: under your standing rule, Codex merges a Claude-written PR only after it has reviewed that exact version, every finding is fixed and the automatic checks are green.

## 4. What CODEX does now

- Nothing is waiting on Codex from the MBA work (#53 is merged). **PR #54** (search-coverage audit, draft, written by Codex) needs a Claude review of its exact head, not a Codex one.
- Any new Claude-written PR: Codex reviews the exact latest version; if it is clean and the checks are green, merge it. If it finds problems, Claude fixes them in new commits and Codex reviews again.
- #51 (Codex's own repair PR) is not part of this: Codex wrote it, so Codex does not review it.

## 5. What CLAUDE does next

- Reviews PR #54 when you ask, re-runs the tests, keeps these documents current.
- As soon as you answer: recounts and, on your "go", erases the old rows (A22); builds readers for the MBA programs you name (A25); applies A23 and A24; creates the daily routine (A3); and does the small changes for A13, A16, A17, A19, A20.
- Never touches your Sheet, a cookie, a real run or anything that costs money without your go.

## 6. Where everything is (branches and pull requests)

| What | Where | State |
| --- | --- | --- |
| The real program | `main` | Holds #40 to #50 (merged October 21) and #53 (merged October 23). |
| **The MBA 2027 work** (MBA rule, pay fix, blank-column checker, tests) | PR #53, branch `claude/mba-2027-main` | **Merged October 23** after an exact-head Codex review with no findings. |
| The original MBA PR | **#52** (branch `claude/jobhunter-continuation-d35nmm`) | Closed unmerged October 23; replaced by #53. Kept as the record of the earlier reviews. |
| Search-coverage audit | **#54** (branch `codex/coverage-audit-executor-20261027`) | Draft, Codex-authored, offline only, no new schedule. Checks pass; no review yet. |
| Codex's repair PR | #51 | Still open. Codex-authored; outside this review. Its fixes already reached `main` through #40 to #50. Closing it waits for your go. |
| The old run branch | `claude/combined-live-run` | History only (the October 19 run). Never merged; not used for new runs. |

## Words used

- **PR / pull request:** a proposed change that others review before it joins the program.
- **Head / exact version:** the newest saved version of a PR. A review only counts for the exact version it looked at.
- **Codex:** the second AI reviewer. **Claude:** me. Rule: whoever writes code, the other one reviews it.
- **Checks / CI:** the automatic test run on GitHub. It must be green before a merge.
- **Sheet:** your Google Sheet (the Jobs tab is the list of jobs).
