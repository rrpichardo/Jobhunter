# START HERE: what you answer, what you do, what you approve, what Codex does, what Claude does

Updated October 21, 2026. Plain language. This is the short version of `docs/PENDING.md` section 0 (same IDs, kept in step with it).
Your answer sheet is `docs/DECISIONS_FORM.md`; you can also just answer in chat.

## Where we are, in five lines

1. The program collects jobs and writes them to your Google Sheet. It ran for real once (October 19): 505 jobs. LinkedIn was refused; X, the newsletter and the job boards worked.
2. You told us what you actually want: **only jobs meant for MBA graduates of 2027.** That rule is built and tested, but today's sources hold almost none (2 of 6,812 postings), so the next step is finding better sources (your answer to item 2 below).
3. Your **blank salary** problem (California, Anthropic) was our fault and is fixed for new jobs. A checker (`scripts.field_audit`) now catches this kind of gap.
4. Eleven pull requests (PRs, proposed code changes) are waiting for **Codex** to review them. Codex reviewed them once, found ten problems, and **Claude has now fixed all ten** on the PRs themselves. The new Codex reviews were requested today.
5. Nothing has been merged into the real program (`main`). Nothing in your Sheet was changed today.

## 1. What YOU need to answer (most important first)

Say "take your recommendations on the small ones" to accept every suggestion in the second table at once.

| # | ID | Question in plain words | My suggestion |
| --- | --- | --- | --- |
| 1 | A22 | **Erase the old rows that are not for MBA 2027?** You said yes. The list is in `docs/MBA_CLEANUP_DRYRUN.md`: 1 row is clearly MBA 2027, 3 are new-grad roles with no MBA mention, 164 were read in full and are not, and 542 cannot be judged (only 300 characters were saved). | Say "go". I back up the whole tab, copy the rows to an archive tab, then remove them from the main tab. Nothing is lost. Or choose "only the 164". |
| 2 | A25 + B11 | **Where should MBA 2027 jobs come from?** The company job boards have almost none. Name the companies with MBA programs (General Motors first), school or MBA job sites, and any web addresses you know. | I build a reader for each program you name. |
| 3 | A24 | Sierra has "Strategist, Agent Development (MBA Grad 2027)". It is for MBA 2027 but is not a product-manager title, so we drop it. **Accept any business role that clearly says it is for MBA 2027?** | Yes. |
| 4 | A23 | **New-grad 2027 roles that do not mention an MBA** (Databricks and Figma associate product manager). They ask for a bachelor's or master's in computer science. Include them? | No. We show the count of dropped ones in every run. |
| 5 | A18 | **LinkedIn** refused our login. What now? | Read your LinkedIn job-alert emails through Gmail (needs your task B1) and rely on JSearch and Jooble; keep the LinkedIn code on hold; remove the LinkedIn cookie setting so the daily run does not knock with a bad cookie. |
| 6 | A3 | **Create the daily routine** (06:07 New York, 3-day window)? | Yes, but only after items 1 and 2, so it runs with the right rules and sources. |

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
| Now | **A22**: erasing the old rows (item 1 above). I will not touch the Sheet without it. |
| When Codex has credits | **Codex review of my own new pull request #52** (the MBA 2027 rule, the pay fix, the checker). Claude wrote it, so Codex must review it. Tell me Codex is back and I post the request. |
| After items 1 and 2 | A **real run** (writes new rows to the Sheet and uses that day's single X attempt). It also proves the run report copies the `trace:` lines, the last unproven piece. |
| After the real run | **A3**: creating the daily routine. |
| Later | The **first merge into `main`**, only when Codex has reviewed the exact version and the automatic checks are green. I will ask before the first one. |
| Later | Closing **PR #51** (Codex's repair PR). Its fixes are now on the real PRs, so it is no longer needed once Codex finishes. |

## 4. What CODEX does now (and nothing else)

**October 21: Codex has no credits right now.** So no Codex review will happen until credits return. The requests already posted below will wait (or get a "usage limit" reply, which is not a review and does not count). The request for my new PR #52 has **not** been posted; you said to hold it. When you tell me Codex has credits again, I check each request, re-post any that got only a usage-limit reply, and post the #52 request. Nothing can be merged into `main` meanwhile.

Codex only reviews; it does not write code in this round. Requests are already posted:

- **Group 1, the X collector stack, one review:** request on PR #40 covering #40, #41, #43, #47 and #48 at the exact versions listed in `docs/CODEX_REVIEW_QUEUE.md`.
- **Group 2, one review each:** PRs #44, #45, #46, #49 and #50.
- PR #42 needs nothing (Codex already found it clean and it has not changed).
- Next, after your "go": review my new pull request, #52 (see section 6).

If Codex finds problems, Claude fixes them in new commits and asks for a fresh review.

## 5. What CLAUDE does next

- Watches for Codex's answers, fixes findings in new commits, checks the automatic tests, keeps these documents current.
- As soon as you answer: erases the old rows (A22), builds readers for the MBA programs you name (A25), applies A23 and A24, creates the daily routine (A3), and does the small changes for A13, A16, A17, A19, A20.
- Never touches your Sheet, a cookie, or a real run without your go.

## 6. Where everything is (branches and pull requests)

| What | Where | State |
| --- | --- | --- |
| The real program | `main` | Unchanged. Nothing merged. |
| Eleven original PRs (#40 to #50) | their own branches | All ten Codex findings are fixed on them (today). Fresh Codex reviews requested. |
| Codex's repair PR | #51 | Its fixes are now on the branches above. Claude reviewed it. Close it later. |
| **My new work** (MBA 2027 rule, pay fix, blank-cell checker, tests, these documents) | branch `claude/jobhunter-continuation-d35nmm`, draft **PR #52** (review vehicle, never merged as is) | Not yet reviewed by Codex. It sits on top of the unreviewed stack, so it can only be merged after those PRs, or re-cut onto `main`. |
| The run branch (only for real runs before review) | `claude/combined-live-run` | Always the same as my branch above. **Never merged.** |

## Words used

- **PR / pull request:** a proposed change that others review before it joins the program.
- **Head / exact version:** the newest saved version of a PR. A review only counts for the exact version it looked at.
- **Codex:** the second AI reviewer. **Claude:** me. Rule: whoever writes code, the other one reviews it.
- **Checks / CI:** the automatic test run on GitHub. It must be green before a merge.
- **Sheet:** your Google Sheet (the Jobs tab is the list of jobs).
