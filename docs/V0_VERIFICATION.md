# V0 verification evidence

## October 18 PR #16 closure and merged-code manual cloud smoke

PR #16 merged as `1df1e7ccbc7579b149085993ded07ca8f9829df7` after a clean
Claude cycle-9 review of `110ea30d7cc4f97ac78a76ea6a05ea405db11632` and passing
required checks. Review/cloud-test evidence:
https://github.com/rrpichardo/Jobhunter/pull/16#issuecomment-6255774750 .
Reviewed-head JobHunterEnv tests and post-merge local tests each passed
577 tests / 10 subtests. Earlier counts/checkpoints below are historical.

Actual JobHunterEnv session:
https://claude.ai/code/session_01Kydab84oh1GMjzuFahVswG . Codex expanded and
inspected command outputs, not just Claude's summary. The cloud checkout was
clean, detached at the exact merge SHA, and contained the reviewed ancestor;
`uv sync --locked` exited 0.

- One approved Stripe Greenhouse request returned HTTP 200: 731 fetched,
  731 valid, 0 rejected, 46 role-family candidates, 35 collection matches,
  17 collection matches excluded by the historical AI-PM filter.
- Python selected one real Product management role from that last set. It
  retained original location/source evidence and unresolved salary; no salary
  eligibility was inferred. This controlled subset used partial-response coverage,
  selected 1, attempts 1. It was not a full source harvest.
- Private artifact: `/root/pr16-smoke-run/smoke.json`, directory 0700/file 0600,
  SHA-256 `36313f8aec32ae8bd59ef173d99d02ea60a1c2719a2daf017959e3f0737a1288`.
  The digest stayed unchanged before/after both writer executions and readback.
  Artifacts are private cloud recovery data, not committed or guaranteed to
  survive cloud container reclamation.
- `scripts.sheets_sync`, run ID `pr16-broad-001`: first sync exit 0; identical
  artifact/run-ID repeat exit 0. Requests and readback were paced for Sheets quotas.
- Readback: Jobs 167 -> 168, zero duplicate Job IDs, all 167 prior IDs present
  exactly once, preexisting Status/Notes/My rating hashes unchanged. Selected
  job present once by ID and title/company/location; original location retained.
- Sources: 47 rows with unchanged source-ID set. Stripe row matched the artifact:
  OK, fetched/valid 731, rejected 0, candidates 46, selected 1, attempts 1,
  HTTP 200, partial-response, blank error. This intentionally replaced Stripe's
  earlier complete-response/selected-7 current summary; next full run refreshes it.
- Run Log: five -> six rows; exactly one `pr16-broad-001`, input/unique 1,
  status complete. Lock owner absent; no manual unlock/quarantine. Final cloud
  checkout remained clean at the merge SHA.

This proves one manual cloud public-source-to-Sheet smoke and safe completed-run
repeat only. It does not prove fresh Gmail delivery, connector message payload
binding, social session restoration, new recovery-fault injection or scheduling.
No Gmail/social reads, additional source requests, credential/settings changes,
applications or contacts occurred. No private note/credential values were printed.

## October 18 Gmail connector readiness and broader collection candidate

Latest local review repairs pass 486 tests and 10 subtests, with a clean diff
check. Actual JobHunterEnv locked tests passed 475/10 on `67ca7f8`, with exit 0,
full SHA confirmed and clean tree; this predates the latest cycle-2 repairs.
Exact-SHA evidence is in PR16 comments. Fresh current-head Claude review and CI
remain required; no production Gmail adapter or scheduled delivery is verified.

Actual Claude cloud session:
https://claude.ai/code/session_01Kydab84oh1GMjzuFahVswG . A bounded read-only
check used the existing Gmail connector. Codex expanded the actual
`mcp__Gmail__list_labels` result and confirmed `JobHunter` exists, type USER,
with messagesTotal=0 and threadsTotal=0. No message-content tools or inbox
fallback were used. This establishes label access only; it does not prove
forwarding, individual-message fetching, extraction or Sheet delivery.

Local verification of the broader-collection/Gmail-boundary candidate:
`.venv/bin/python -m pytest -q` passed 458 tests and 10 subtests;
`git diff --check` passed. These are offline tests. Synthetic Gmail integration
includes probe-to-writer delivery, repeated reconciliation and preservation of
Status, Notes and My rating. The real cloud connector adapter/CLI path is still
missing. Gmail routing remains uninstalled; a dedicated-account LinkedIn alert
metadata search returned no matches after alert setup. No full deployment claim.

LinkedIn Manage job alerts UI confirmed 18 daily email/notification alerts in
the dedicated account. This proves alert configuration, not delivered messages.

## Post-merge Codex review scope

The original automated writer cycle-3 request failed due a usage limit. A manual
Codex review later found defects at 6a61f35; it was not approval of the final head.
An independent app-based Codex review after the merges found three P2 defects at
36539f4. Its report is in reviews/2026-10-18-codex-postmerge-review.md. The follow-up
fixes have new regressions and need fresh exact-head review/CI. This chronology
must not be represented as a completed pre-merge Codex bot review.

## Current local repair scope — not new cloud evidence

The historical cloud runs below prove only the revisions they name. Review repairs
were developed under a local-only restriction. The user has now authorized their
push and integration; they have not been exercised against live sources/Google
Sheets. Integration does not extend the historical cloud evidence.
The current local full suite passes 330 tests and 10 subtests; this is offline
evidence, not a Claude reviewer test run or deployment proof.

Identity policy after review: merge verified ATS requisitions and matching explicit
Greenhouse `gh_jid` links; retain unknown shared application URLs as flagged
possible duplicates, including multiple-source and same-source repost cases.
The older second-run statement about identical employer links describes that
historical revision and does not assert that every custom URL is now mergeable.

The bounded probe still selects at most eight jobs per source and 150 globally.
Detail fetches prioritize explicit AI titles inside the existing eight-page
budget; skipped detail/global-cap counts are retained in probe notes and its
summary. Description-only AI matches beyond that budget remain unexamined.
These notes are artifact evidence; durable per-run source history is still open.

## Bootstrap prerequisite — October 17, 2026

Scope: reproducible installation and CI plus cloud readiness inventory. This is
an early prerequisite PR, **not completed M0** (thin source-to-Sheet + recovery),
and **not V0 deployment**.

Local macOS ARM64 checks used uv 0.13.1 and uv-managed Python 3.12.15:

```sh
uv lock
uv sync --locked
uv run --locked python -c "import bs4, feedparser, google.auth, gspread, httpx, yaml"
uv run --locked python -m pytest -q
```

Result: lock resolved; locked installation and all six runtime imports passed;
**6 tests and 10 subtests passed**. The tests are unchanged historical writer
examples, not production integration tests.

At implementation revision `e7c9c750e2f59f3e87e277fc0a39569337bcf873`:

- [Linux and Windows CI](https://github.com/rrpichardo/Jobhunter/actions/runs/39075258194)
  both passed locked installation, six runtime imports, and the complete suite.
- [Claude Code Sonnet review](https://github.com/rrpichardo/Jobhunter/pull/4#issuecomment-6242298543)
  found no actionable findings. It inspected the diff; it did not reproduce tests
  or cloud UI checks. This review does not cover subsequent documentation changes.

Live cloud evidence: the [bounded cloud session](https://claude.ai/code/session_015wZ8bZKVEjazvzsqciHokQ)
made one real Greenhouse request (HTTP 200, 655 jobs, one PM posting inspected).
The underlying command/output was expanded in the UI and verified. See
`CLOUD_CAPABILITIES.md` for the precise scope, runtime versions and unknowns.
This is a manual cloud probe, not a scheduled routine or application run.
No source-to-Sheet delivery, validated Claude extraction contract, Gmail read,
social collection, schedule, session restoration, or recovery evidence exists yet.
No trial start or day-7/day-14 review dates have been assigned.

Workbook setup: exact-title search found no existing workbook; the empty private
`Jobhunter V0` was created in the approved browser profile. Title, URL, Saved to
Drive, and private sharing status were read back from the UI. See `SETUP.md`.
Creation is setup evidence only; no application Sheet write has occurred.

## M0 source/extraction stage — local evidence

- `uv run --locked python -m pytest -q`: **43 passed, 10 subtests passed**.
- Tests first failed for missing modules, then passed after implementation.
- New synthetic-data tests cover deterministic public IDs, strict model excerpt
  validation, duplicate/unknown IDs, inert embedded instructions, explicit
  timeouts and bounded retries, Retry-After seconds/dates, source schema errors,
  empty vs failed source results, bounded sample/coverage metadata, and CLI
  roundtrip. Artifacts cannot overwrite files or be written inside the checkout.
- No new live source request, Claude extraction, Sheet write, or deployment is
  established by these tests. See the next PR for final revision/CI/review evidence.

### Actual cloud code-path test

Tested revision `f913601f36b329fcc81f3e84f31542277cfcffe6` in the existing
JobHunterEnv [cloud session](https://claude.ai/code/session_015wZ8bZKVEjazvzsqciHokQ).
This was a manual test of the proposed revision, not a deployed/scheduled run.

- Cloud installation used official uv 0.13.1 and Python 3.12.3. `uv sync --locked`
  passed; `uv run --locked python -m pytest -q` passed 43 tests and 10 subtests.
- One `python -m scripts.v0_harvest` run returned `OK: fetched=655 selected_for_m0=1`,
  exit 0. Saved metadata reports 15 PM candidates and complete-response coverage.
- Claude Sonnet selected a 23-word exact excerpt through the existing subscription
  and saved the extraction JSON. `python -m scripts.validate_extractions` returned
  `validated_records=1; Sheet delivery not attempted`, exit 0. Both application
  command outputs were expanded and inspected in the browser.
- Job ID: `greenhouse:anthropic:5434361008`; public
  [posting](https://job-boards.greenhouse.io/anthropic/jobs/5434361008).
- A tester-authored summary one-liner used `records` instead of `jobs` and failed
  after the validation CLI had succeeded. The corrected summary was read back;
  no application code/assertions were changed or live fetch repeated.
- Cloud working tree stayed clean. Artifacts were in a private ephemeral directory
  outside the checkout. This proves no cross-session persistence. No Sheet write,
  Gmail/social access, account setup, cookies, schedule or new service was involved.

### Review-fix verification

Fresh Claude review found actionable edge cases in the first revision. Regression
tests first reproduced the failures; the fixed full local suite passed **57 tests,
10 subtests**. Changes are listed in ATTEMPTS.md. The earlier live cloud check
above covers `f913601` only. Recheck the affected code using saved public payloads
and current cloud tests; do not imply the old cloud result covers new code.

Cloud recheck at `aaed72b23710873db4241fd6f8b048489b4a494c`: locked install and
57 tests/10 subtests passed in JobHunterEnv; one fresh harvest returned 655 valid,
0 rejected, 15 PM candidates, 1 selected, HTTP 200 after 1 attempt, complete-response.
Claude selected an exact excerpt; validation with the printed harvest digest
returned 1 complete record and exit 0. The actual command outputs were expanded
and inspected. No Sheet/Gmail/social/credential/scheduling actions were performed.

After review cycle 2, the full local suite passes **61 tests and 10 subtests**.
Binary artifact publication now makes digest bytes portable to Windows; server
schema/decode edge cases retain sanitized failure evidence. Final current-revision
review, Linux/Windows CI and cloud replay evidence will be linked from PR #5.

## M0 first-stage final integration and initial Google read access

PR #5 final head `0f7b43659a496c80a25079dd9107ccda1439e154` received fresh
Claude Code review with no unresolved actionable findings. Linux/Windows CI
passed; actual JobHunterEnv locked install and 65 tests/10 subtests passed.
Saved extraction validated against the original trusted digest: 1 record, exit 0.
No additional live source fetch. PR #5 merged as `d77842d`; main tests passed again.
See [final evidence](https://github.com/rrpichardo/Jobhunter/pull/5#issuecomment-6243315386).

The connection foundation at `02603884be0ba98b57094f100ba7eeb76d64b8a5` was
checked in the same actual JobHunterEnv cloud session after user-approved GCP
network-secret provisioning. Native copy/paste put the complete JSON directly
into that secret, without printing the key. The UI confirmed saved restricted
host/workbook path and non-secret configuration. No credential variable/file was
placed in the VM. Using gspread with AnonymousCredentials, `open_workbook(cfg)`
and `worksheets()` printed only `RESULT=success tab_count=1`, exit 0, exact HEAD,
and clean-tree status. Tool output was expanded and inspected. There was one
bounded connection attempt (two metadata reads), no write or retry.

This is initial cloud read-access proof, not successful write authorization,
write-path proxy compatibility, locking, recovery, a scheduled run, or deployment.
Writer tests and harmless write/readback/structural-endpoint checks remain required.
The user accepted continued use of the disclosed dedicated key; see SETUP.md.

## M0 writer live harness in JobHunterEnv — October 18, 2026

Scope: failure-injection and concurrency checks of the Sheet writer against Google,
using only fresh hidden `_M0Test_` fixture tabs and the shared lock tab. This is
**not** the real-posting write, not a scheduled run and not V0 deployment.

Actual Claude cloud session
https://claude.ai/code/session_01DsCkZnt2X9EtuQRVq6Gq5u (JobHunterEnv, branch
`claude/m0-sheet-sync`, HEAD `c5e2398`, clean tree). The container's uv was 0.11.32 and
the repo pins 0.13.1; with the user's approval uv 0.13.1 was installed with pip into a
scratch virtualenv outside the checkout. No tracked file or setting changed.

- `uv sync --locked` and `uv run --locked python -m pytest -q`: **154 passed,
  10 subtests passed** in the cloud.
- `uv run --locked python -m scripts.live_harness` (paced 1.5 s, eight clean scenarios,
  run in the background and read from the output file after it finished):
  **`summary: scenarios=8 failures=0`**, exit code 0, process not running afterwards.
  The expanded command output had 54 PASS lines and no FAIL line. Namespaces:
  `_M0Test_ea1312753eb7` (chunks), `d51081372f06` (repeat), `4bf8cc375569` (preserve),
  `d850038cd74a` (sorted), `dffa80a01b24` (timeout after apply), `7eb8b875924b`
  (timeout after structural apply), `48489e778b42` (interrupt after apply),
  `aa48b655cc1d` (overlap).
- Checked live: 40 jobs in 9 write requests with no duplicates and a complete Run Log
  row; same run ID rewrote nothing; a new run ID with unchanged data added no Jobs
  rows; changed data under an old run ID was refused (`run_id_payload_conflict`);
  user-edited Status/Notes/My rating/Date found survived a second sync and
  formula-looking text stayed literal; after rows were sorted by a user, a rerun
  updated each job by ID and notes stayed with their job; a timeout after Google had
  applied a cell write and after a structural change were both confirmed by the lock
  receipt and the sync completed; an interrupt after an applied write released the
  lock, kept the pending journal, and the rerun recovered it (`recovered=1`); two
  independent processes raced and exactly one won while the other reported
  `writer_locked`, with one Run Log row and no duplicate jobs. Every scenario ended
  with `no_writes_outside_namespace` and `lock_released` passing.
- **Not run on purpose:** `timeout_before_apply` and `interrupt_before_apply`, which
  deliberately leave the global lock in place. The harness never unlocks. Those cases
  remain covered only by unit tests. The eight fixture tabs were retained, hidden.
- **Not proven yet:** the real posting write and repeated-run readback in the real
  Jobs/Run Log, scheduled M0, per-run source history, and Codex review of the writer
  (cycle 3 / 3 requested for `99b1154`; Codex reported its usage limit, so no review
  of that revision has been delivered).

## M0 real posting write in JobHunterEnv — October 18, 2026

Scope: first application-level write to the real workbook tabs from the actual Claude
cloud environment, plus an identical repeat. **Not** a scheduled run, the full V0
source set, or a merge approval. Same cloud session as the harness run above
(https://claude.ai/code/session_01DsCkZnt2X9EtuQRVq6Gq5u, code `c5e2398`).

The earlier session's saved posting data was gone, so with the user's approval one new
bounded public harvest was run (single Greenhouse board request, no social source).
It is a **different posting** from the earlier validated one; the old trusted digest
`84423ba3...ff49a8e` does not apply to it. Independently retained digest for this
harvest (also saved to a separate file in the cloud run directory, outside the harvest
file and the checkout):

`harvest_sha256 = d7849a78f6e81b637ef35dfeff9275a0be9c6180ab79b912311f8bcda33c7019`

- Harvest: Greenhouse `anthropic` board, 655 items fetched, 15 PM candidates, 1 selected,
  coverage `complete-response`. Selected: "Product Manager, Billing", Anthropic, job ID
  `greenhouse:anthropic:5434361008`, source `greenhouse:anthropic`. The posting text was
  treated as untrusted data and held no embedded instructions.
- Extraction (job_id + description_quote only) validated by `scripts.validate_extractions`:
  1 record, exit 0, Status=New.
- `scripts.sheets_sync --input records.json --run-id m0-real-001`: **exit 0**,
  `sync_verified: run_id=m0-real-001 unique_jobs=1 recovered_runs=0`. The identical repeat
  command: **exit 0**, same line. Command/output copies were kept in the cloud run
  directory (`sync1_*`, `sync2_*`, `harvest_stdout.txt`, `validate_stdout.txt`); they may
  disappear with the container.
- Read-only readback (GET only): real Jobs tab has exactly one data row for that Job ID
  (Status New, Notes and My rating blank, rank 1); Run Log has exactly one row,
  `m0-real-001`, Status `complete`, Jobs input 1 / unique 1, and no second row after the
  repeat; Sources has one `greenhouse:anthropic` row (OK); hidden `_State` holds only the
  run's chunk and a manifest with a finished time (no pending work).
- Lock: afterwards `GspreadStore(open_workbook()).lock_owner() is None` printed
  `lock_owner_is_none= True`. Nothing was unlocked or deleted by hand. The workbook has
  38 tabs at that point: the real tabs plus `Sheet1`, `_M0AuthProbe` and 32 hidden
  `_M0Test_*` fixture tabs.
- **Not proven:** scheduled M0 (no routine exists), per-run source history, Gmail,
  LinkedIn/X, the exact daily runbook, and Codex review of the writer revision.
  This historical live write used `c5e2398`, before the quarantine-retirement fix
  at `e3536e4`; it is not current-head proof for #8. Recheck the real writer/repeat
  path and affected recovery behavior at the final reviewed writer revision.
  The ephemeral command/readback evidence above is an author's recorded report,
  not a durable raw-output archive that an offline reviewer can reproduce.

## M0 multi-source probe and real delivery in JobHunterEnv — October 18, 2026

Scope: one polite request to every non-login V0 source from the actual Claude cloud
environment, then delivery of the AI-PM matches and every source's status to the real
workbook. This is a **source feasibility and first delivery**, not the scheduled daily run,
not the 14-day trial, and not approval to merge. Same cloud session as above
(https://claude.ai/code/session_01DsCkZnt2X9EtuQRVq6Gq5u), code `473d7d0` on
`claude/m1-source-coverage`, tree clean, `uv sync --locked` and **188 tests passed**.

- `scripts.source_probe` (one GET each, no retries, no social, no login, no Google access):
  exit 0, **`sources=44 delivered_jobs=136 failed_or_blocked=0`**,
  `probe_sha256 = 812e0e538686382d188621cb79da18c9682ef653952d6f784e42f438ccd04962`
  (kept in a separate file in the cloud run directory). Expanded output was read.
- `scripts.sheets_sync --input probe.json --run-id m1-sources-001`: **exit 0**,
  `sync_verified: run_id=m1-sources-001 unique_jobs=136 sources=44 recovered_runs=0`,
  `source_problems_recorded=0`; the identical repeat exited 0 with identical output.
- Read-only readback: Jobs has 136 rows with no duplicate or blank Job ID, every row
  Status=New with blank Notes and My rating, and the earlier Anthropic "Product Manager,
  Billing" job (`greenhouse:anthropic:5434361008`) is still exactly one row. Sources has 44
  rows matching the probe table; Run Log has one row each for `m0-real-001` and
  `m1-sources-001`, with no extra row after the repeat. The lock was confirmed released
  afterwards (`lock_owner_is_none= True`); nothing was unlocked by hand.
- Delivering sources (jobs per source): eight each from ashby:harvey, ashby:openai,
  greenhouse:anthropic, cloudflare, coinbase, databricks, datadog, pinterest, reddit, scaleai,
  stripe and weworkremotely; ashby:perplexity 7; ashby:sierra, greenhouse:instacart 6;
  ashby:ramp, greenhouse:figma 4; greenhouse:airbnb, themuse 3; ashby:elevenlabs, jobicy 2;
  ashby:linear, ashby:notion, remoteok 1. The cap is 8 per source and 150 in total.
- Reachable but nothing delivered (`OK-zero-jobs`): lever:palantir (no PM titles),
  lever:spotify and ashby:cohere (PM titles, none passed the AI/US filter), lever:mistral
  (the endpoint answers HTTP 200 with an empty list, checked by hand), remotive and
  himalayas (small partial lists, no PM titles), and the listing-only sources yc-product
  (19 PM titles), a16z-ai-pm (24), getro-accel, getro-primary and hn-who-is-hiring (393
  comments). Delivering those needs a detail fetch or model extraction, not built yet.
- Recorded `needs setup` without any request: jsearch, adzuna, jooble (keys missing),
  linkedin-logged-in and x-hiring-posts (dedicated accounts and cookies are the user's
  step), gmail-job-alerts, nextplay-rss, alirohde-rss (feed URLs unverified), cosign.
  Gmail was checked with `list_labels` only (no message, thread or search): **no label named
  `JobHunter` exists** (an unrelated label does), so the forwarding/label setup is still open.
- **Known wart:** the Run Log status for `m1-sources-001` reads
  `complete-with-source-failure` because `needs setup` counts as a non-OK source in
  `jobhunter/sheets.py`, although no source failed or was blocked. It was left alone on
  purpose: changing the rule now would make a replay of this completed run ID report
  `completed_run_changed`. Treat that status as "some source was not OK".
- Not proven: scheduled M0, per-run source history, cross-source duplicate detection (the
  same role on a company board and an aggregator becomes two rows), eligibility decisions,
  Gmail alerts, LinkedIn, X, and Codex review of any of this code.

### Second multi-source run: detail pages and safe duplicate handling — October 18, 2026

Same cloud session, code `c6bcf8c` on `claude/m1-source-coverage`, tree clean, `uv sync --locked`,
**206 tests passed**. The probe now fetches individual job pages for Y Combinator, Built In and the
Getro boards (robots.txt checked; one polite GET each, at most 8 per source) and merges
duplicates only on identical employer links.

- `scripts.source_probe`: exit 0, **`sources=47 delivered_jobs=148 failed_or_blocked=0
  duplicates_merged=0`**; no detail page was refused. Run directory `/root/m2_sources_run_002`.
- `scripts.sheets_sync --run-id m2-sources-002`: **exit 0** (`unique_jobs=148 sources=47`); the
  identical repeat exited 0 with identical output.
- Readback (GET only): 148 Jobs rows, no duplicate or blank Job ID, all Status=New with blank
  Notes and My rating. The 136 rows from the first run are still present exactly once and
  unchanged (checked against that run's readback), including `greenhouse:anthropic:5434361008`.
  New rows: yc-product 5, getro-accel 4, getro-primary 2, builtin-product 1. Sources has 47 rows
  and Run Log has one row each for `m0-real-001`, `m1-sources-001` and `m2-sources-002`. The lock was
  released afterwards (`lock_owner_is_none= True`).
- Four "Possible duplicate ... needs review" notes (three Databricks pairs, one Harvey pair: same
  company and title, different requisition). These are for human review; both rows were kept.
- A development run found and fixed two bugs before this cloud run: some Greenhouse boards share one
  careers-page path and differ only by `gh_jid`, which a first canonicalizer wrongly merged; and
  `City, ST, CC` locations with a non-US country code (for example Bengaluru) passed the US filter.
  Both have regression tests.
- Still not delivered: a16z (count only), Hacker News "Who's Hiring" (needs model extraction),
  Work at a Startup's own site (HTTP 406 login wall; its jobs come through the YC pages),
  `cosign.com` (now a domain-parking redirect, correct URL needed), MBA/school sites (not named),
  and everything needing keys, accounts or the Gmail label.

### Documentation incident (October 18, 2026)

Two whitespace cleanups wrongly emptied `docs/ATTEMPTS.md` and `docs/V0_VERIFICATION.md` in commits
`696ac79` (PR #9) and `b68e572` (PR #10): the file was opened for writing before it was read. PR #8 and
all code were unaffected. Both files were restored from `6a61f35` with the later evidence re-added in
new commits (no history rewrite). Check with `git diff --stat` that docs changes have no unexpected
deletions before committing.

## JSearch and Jooble keyed sources in JobHunterEnv — October 18, 2026

Branch `claude/m2-jsearch-jooble` (PR #13) at `166304c`, fresh cloud session, uv 0.13.1 from a scratch
virtualenv, clean tree: **379 tests passed**. The first live probe showed JSearch answering HTTP 404 on
its retired `/search` path; `/search-v2` (jobs under `data.jobs`) fixed it. A second probe showed the
writer's 150-job ceiling filled by earlier registry sources, so the cap is now shared round-robin.
Final probe exit 0 with JSearch delivering 6 and Jooble 4 jobs; neither key value appeared in the
output, artifact or logs. `sheets_sync --run-id m4-sources-004` and its identical repeat exited 0.
Read-only readback: 167 Jobs rows, no duplicate Job IDs, earlier rows present once, the jsearch and
jooble Sources rows OK, one Run Log row for the run, lock released. Noted, not failures: one jsearch
row with a blank location and an odd company string; 47 Sources rows for 46 registry sources (likely
the old adzuna row); a transient Sheets read-quota 429 during readback.

## First manual non-social pull in JobHunterEnv — October 18 to 19, 2026 (PARTIAL, not a pass)

Cloud session `session_01KuVxYnAppMwqn66vKEgfS1`, detached at `4b9860e` (top of the PR #19 to #27 stack),
uv 0.13.1, clean tree: **760 tests passed, 10 subtests**. Four-week window, safety stops raised
(`--detail-safety-stop 1000 --page-safety-stop 200`).

- **Hacker News:** 2 threads, 266 comments in the window, 28 role candidates, all 28 read; 18 facts proposed,
  validate reported `valid=18 delivered=14 rejected=0` (the 4 not delivered were excluded by the collection
  filter; the tool does not say which). The AI-queue commit did NOT run (see below), so these 28 comments
  are still unread in the queue and will be read again.
- **Collect:** 344 jobs from 46 sources, none failed or blocked. The Muse delivered 177 jobs (paging works),
  Jooble 20, Jobicy 16, Getro Primary 15, Hacker News 14, JSearch 9. 8 sources stayed `needs setup`.
- **Delivery to the real Sheet FAILED partway.** `sheets_sync` exited 2 with `sheet_http_429` (Google's
  per-minute read quota; the 2-second pause between batches was far too short) and lock cleanup also
  failed, so the writer lock (`_JobHunterLock`) was left behind. The single allowed retry printed
  `writer_locked`. Batches `first-pull-20261018-b001` and `-b002` (150 jobs each) completed; the third
  (about 44 jobs) did not. Neither run printed `sync_verified`. The repeat-safety step did not run.
- **Read-only readback:** Jobs 420 rows, 0 duplicate Job IDs, 0 blank IDs; Sources 47 rows; Run Log 8 rows
  (6 earlier plus the two batch rows); the lock is still held. Nothing was unlocked by the session.

Not proven: a complete first pull, idempotent rerun of a batched run, the AI queue commit, lock release after a
quota error. Fix on branch `claude/writer-quota-pacing`: 45 s between batches, a 429 now waits 20 s then 40 s, and
lock reads retry through a quota error (creates and deletes still never repeat). The stuck lock needs an explicit
operator decision before removal (runbook rule); see PENDING.md.

## First manual non-social pull, rerun with the quota fix — October 19, 2026 (PASSED for the sources it covered)

Same cloud session, detached at `b03dcd4` (PR #28, CI green on Linux and Windows): **768 tests passed, 10
subtests**. The user approved removing the leftover lock. The session first read the lock owner, started
time and the Jobs/Sources/Run Log/_State row counts twice, 90 seconds apart; they matched exactly, so no writer
was active. It then made one `drop_lock()` call and confirmed the lock was gone. A new run ID,
`first-pull-20261019-r2`, was used because the old payload no longer existed and a changed payload under an old
run ID is refused by design (`run_id_payload_conflict`).

- Hacker News: the same 28 candidate comments, all read, 18 facts, `valid=18 delivered=14 rejected=0`;
  `ai_queue commit` printed `marked_read=28`.
- Collect: 322 jobs from 46 sources; one source failed (`getro-accel`, see below); 8 sources `needs setup`.
- Sync: `sync_verified: run_id=first-pull-20261019-r2 batches=3 unique_jobs=322 sources=46 recovered_runs=1`
  (exit 0). The recovered run was the earlier `first-pull-20261018` third batch (44 jobs), now `-b003`.
  The identical repeat printed `recovered_runs=0` and exit 0.
- Readback (read-only): Jobs 478 rows, 0 duplicate IDs, 0 blank IDs (themuse 178, jooble 29, jsearch 24,
  getro-primary 17, stripe 16, jobicy 16, hacker news 14); Sources 47 rows (36 OK, 1 failed, 10 needs setup);
  Run Log 12 rows, all complete or complete-with-source-failure; writer lock released; `_State` 118 data rows.
- Not captured: the Jobs count immediately before the repeat sync, so "the repeat added nothing" rests on the
  Run Log and the idempotent design, not a before/after count.

**Defect found by this run, fixed on branch `claude/known-ids-all-delivered`:** `getro-accel` was recorded as
failed (`invalid_items_quarantined`) because every good job was already in the Sheet (so none were fetched) and
one malformed stub remained. A listing whose good jobs are all already delivered is now `OK-zero-jobs`.
The Sources row stays `failed` in the workbook until the next run corrects it.

Scope: this proves collection, paced batched delivery, recovery of an interrupted batch, the AI queue commit and
the lock handling for the public sources. It does NOT prove LinkedIn, X, Gmail, Work at a Startup, school sites,
the scheduled routine, or a second day's run that finds mostly known jobs.
