# New-conversation implementation prompt

Paste the text below into a new Codex conversation opened on the JobHunter repo.
Include any setup answers from the preparation conversation that are not yet in
`docs/SETUP.md`. This is a request to implement V0, not just to write another plan.

---

Create and pursue a goal: **Implement, test, debug, and deploy JobHunter V0 as a
daily Claude Code cloud routine, with source/run evidence recorded each day and
a separate day-14 results review arranged. Follow the completion gates below and
report only verified results.** Use goal tracking if available, without inventing
a token budget. The implementation goal ends when deployment is verified and the
follow-up is arranged; it does not stay active waiting for fourteen days to pass.

## Retry limits and exit conditions

- Make at most **three distinct attempts total per blocker**, including the initial
  attempt. A blocker is the same failing requirement/root cause, not each command.
  After a failure, inspect evidence and change the approach before retrying. Do not
  repeat identical calls or move work to another agent just to reset the counter.
- Persist attempts, relevant errors, approaches tried, and the next required action
  in `docs/ATTEMPTS.md` (sanitized). Counters survive conversations and restarts.
  This log is for implementation work; the daily routine never edits it. Runtime
  failures and retry evidence go to Sources and Run Log.
  A source challenge/429 stop rule overrides this budget: stop immediately when
  the plan requires it. Normal bounded HTTP retries count toward the configured
  request budget; do not wrap exhausted retries in another unbounded retry loop.
- After three unsuccessful attempts, stop work on that blocker, report what failed
  and what user input/external change is required, and continue independent work.
  Resume that blocker only after a relevant external change or my explicit direction.
  Three attempts is a maximum, not a requirement to repeat a clearly impossible action.
- Limit implementation/review repair cycles to three per milestone before reporting
  remaining findings and asking for a decision. Do not merge unresolved required
  findings merely because the attempt budget ran out.
- Do not busy-poll accounts, CI, reviews, credentials, or scheduled runs. Use bounded
  event waits or scheduled follow-ups. If there is no productive independent work,
  give a concise handoff instead of repeatedly saying that you are waiting.
- I authorize pausing the tracked goal when all remaining work is blocked after
  these attempts or requires my input.
  State the exact reason and resume condition; follow the host's goal-status rules.
  A pause is not completion. Do not fabricate a successful deployment to exit.
- Once deployment is verified, let the cloud routine collect evidence every day
  and arrange separate day-7/day-14 follow-ups where supported. Complete this
  implementation goal when its acceptance gates pass; do not wait fourteen days.
  If follow-up scheduling is unavailable, give me the exact review date and prompt.
- At day 14, deliver the review even if some results are inconclusive. Recommend
  additional observation where useful, but ask before extending the evaluation
  goal; no automatic endless extension. The approved daily collection may continue.

## Context and scope

Repository: `rrpichardo/Jobhunter`. Read `AGENTS.md`, `CLAUDE.md`, `docs/PLAN.md`, and
`docs/SETUP.md`, inspect the current code and Git state, and preserve existing work.
The current plan is the source of truth; older chat assumptions are superseded by it.

Build in Codex; execute production in the Claude Code cloud routine. Any agent can
author Python, extraction prompts, JSON contracts, setup scripts, and the routine
prompt. Live Claude extraction and connector integration are validated in the actual
Claude runtime using the approved subscription. Do not add direct paid model API
calls simply because development is happening in Codex.

V0 includes ALL planned source integrations and explicit statuses, with LinkedIn
jobs/posts and X hiring posts included from the start, plus daily scheduling,
filtering, deduplication, source history, and safe Google Sheets delivery. Every
operational component runs in the cloud; my laptop must not need to remain on.
V0 does not require later AI fit scoring, resume tailoring, or automatic applications.
Do not expand into those later phases while V0 remains unfinished.

## Ask me before starting implementation

Read existing setup answers first. Inspect the relevant setup screens when access
is available, then ask only for details that cannot be determined safely:

Confirmed already: Claude Pro; use or create a dedicated `JobHunter` environment
with Full network access before adding Google credentials; no routine exists yet.
Keep the existing Claude Gmail connector and forward alerts into its account from
the dedicated job-alert Gmail. Read only messages carrying `JobHunter`. The dedicated
job-alert address is also the sign-up email for LinkedIn/X; security and verification
messages stay there. No new paid services or API usage without approval; daily at
06:07 America/New_York; initial 14-day trial. Do not ask me to reconfirm these choices.
The `Jobhunter V0` workbook, writer service account, and dedicated LinkedIn and X
accounts are all confirmed **not created yet**. Operate the setup UI with my help; do not ask for
a nonexistent workbook URL or repeat the readiness questions.

1. Inspect whether the dedicated `JobHunter` environment has since been created.
   Confirm the connected Gmail account through settings and verify filtered
   forwarding and the `JobHunter` label. Ask for access only when needed. Keep
   readiness separate from the already-approved routing decision.
2. Guide creation of the workbook and writer service account, sharing and secure
   provisioning. Request the workbook URL/ID only after creation. Ask which job API
   providers are already configured; do not request secret values.
3. Guide user creation of the dedicated LinkedIn and X accounts. Explain the
   user-operated cloud authentication step after verifying the chosen runtime's
   supported mechanism. Account creation and verification remain user actions.
4. Ask about additional setup only when actual inspection identifies a missing
   prerequisite. Spending, schedule, and trial preferences are already answered.

Never ask me to paste secrets. Give provider-specific secure setup instructions
when credentials are needed. Wait for required scope/spending answers before
dependent implementation; read-only inspection may continue. Once answered, record
non-secret decisions in `docs/SETUP.md` and proceed without repeated permission
requests for ordinary edits, tests, bug fixes, and approved integration work.
Scope and spending preferences above are already answered. Independent coding and
offline tests may proceed while setup is outstanding; do not let absent credentials
block unrelated work or treat offline success as proof of live integration.

## Operate my local computer for setup

I authorize you to use supported computer/browser tools on this local computer,
preferably Chrome, to carry out the JobHunter setup below. Open and navigate the
correct pages, select settings, fill known non-secret values, and save authorized
configuration. Prefer a suitable connected tool when available. Inspect existing
resources before creating anything to avoid duplicates. Do the available work
instead of handing me a long list of clicks.

- Create/configure the dedicated Claude `JobHunter` cloud environment with Full
  network access before Google credentials are added. Preserve `Boom` and `Default`.
- Create the `Jobhunter V0` Google Sheet, enable the Sheets API in the chosen Google
  Cloud project, create its dedicated writer service account, and share only the
  intended workbook with that account. Ask me to choose an account/project if unclear.
- Configure the approved job-alert forwarding/filter rules and destination
  `JobHunter` label while preserving the existing Claude Gmail connector. This
  narrowly authorizes one-time setup changes; routine Gmail access remains read-only.
  Exclude account-security/verification messages and avoid unrelated mailbox content.
- Navigate LinkedIn and X signup/login and prepare non-secret setup. I complete
  account creation, private details, passwords, verification codes, CAPTCHAs, and
  identity checks myself. Use the dedicated job-alert email for both accounts.
- Set up supported cloud authentication and session storage. A successful login
  in local Chrome is not proof that the cloud collector is authenticated; verify
  the actual cloud session and its restoration after a restart.
  For social sources, the updated PLAN.md specifies user local login followed by
  direct dedicated-account cookie provisioning in JobHunterEnv settings and fresh
  headless restoration each run. No interactive cloud login or persistent secret
  browser volume is required. Non-secret allowances/recovery records go in Sheet
  `_State`; prove serialization separately because the tab is not an atomic lock.
  Do not introduce a new hosting service/account. The user subsequently approved
  the Google credential fallback described in PLAN.md: first inspect compatible
  GCP secret types, otherwise use a dedicated JobHunterEnv variable, load in memory
  if possible, and never expose values. Use only the dedicated writer with access
  to this workbook, no project IAM roles, and the Sheets API only.
- Configure and enable the approved Claude cloud routine, connectors, and schedule
  after tests pass; verify PR review configuration as needed for the handoff.

Pause at private inputs and clearly tell me which field/action to complete. Let
me enter details directly into the provider UI, then resume when I say I am done.
Never ask me to paste passwords, tokens, cookies, or credential JSON into chat.
Use the provider's secure flow for credential provisioning; do not expose secret
values through tool output, screenshots, logs, repository files, or PRs.

Ask only for genuinely missing choices, required personal input, new costs, or
expanded permissions. Do not repeatedly ask whether to continue ordinary authorized
setup. Do not activate billing, paid trials, or new paid services without approval.
If computer/browser access is unavailable, explain the specific missing access
and give the smallest necessary manual step; do not claim a UI action happened.

Local computer use is for setup, development, and verification only. The daily
operational workflow must run entirely in the cloud with my computer switched off.

## Execution sequence

Use at least one PR per implementation milestone; never wait until the whole
application is finished. Suggested boundaries are reproducible setup/cloud proof,
reliable writer/recovery, source integrations in manageable groups, social cloud
integration, and final daily operation. Define each milestone's acceptance criteria
before coding it. Open draft PRs for early feedback when useful. Obtain Claude Code
feedback on every Codex implementation milestone, resolve actionable findings,
and verify the reviewed revision before merging and advancing dependent work.
If review cannot run, report the blocker rather than treating its absence as approval.

1. **Establish a reproducible development environment.** Create an implementation
   branch, install a supported Python using `uv`, add `pyproject.toml` and `uv.lock`,
   and verify locked installation. Establish Linux and Windows CI as required by
   the plan. Inventory sources, credentials, and cloud capabilities explicitly.
2. **Prove cloud feasibility early.** Before building all collectors, send one real
   Greenhouse posting through the actual cloud routine into the configured Sheet.
   Verify a repeated write preserves user fields and adds no duplicate. In parallel
   with this implementation phase (without competing repo editors), validate the
   hard integrations: label-scoped Gmail access, live Claude-to-JSON extraction, LinkedIn cloud
   browser authentication/persistence, and X cloud authentication. Verify network
   access and secret delivery. Do not assume a persistent local filesystem, local
   browser, or connector credentials automatically authenticate Python.
   Use the existing Claude Gmail connector without changing its account. Search
   only `JobHunter`-labeled alerts; fetch only matching messages, not unrelated
   messages in a returned thread. Missing labels mean `needs setup`; an empty label
   is an empty source, never permission to search the whole inbox. Do not use Gmail
   send/reply/trash/label-change tools. Confirm forwarding excludes verification,
   login, and password-reset messages, even when sent by the same provider as alerts.
3. **Build the reliable data path.** Implement shared fetching, bounded retries,
   source registry, normalized schemas, deterministic filtering and identity,
   cross-source attribution, safe batching, reconciliation, and one-writer control.
   Keep Google Sheets as the job/CRM source of truth. Store non-secret pending
   work, retry/allowance counters and run markers in Sheet `_State`; it is not an
   atomic lock. Recreate secret sessions from approved environment credentials;
   keep intermediate files private/temporary, not a competing job database.
   Validate AI outputs and treat source content as untrusted data.
4. **Integrate all planned source routes.** Include direct company boards, public
   job boards, company discovery, RSS/newsletters, Gmail alerts, configured job APIs,
   selected JobSpy boards, LinkedIn jobs/posts, and X hiring posts. Implement or
   explicitly document the access prerequisite for every registry entry. Record
   pagination coverage, limits, failures, empty results, and setup gaps accurately.
   A working email fallback does not prove the logged-in LinkedIn collector works.
5. **Test, fix, and review.** Run the checks below, investigate failures, fix root
   causes, and add meaningful regression coverage. Do not disable failing tests
   or weaken expectations to obtain a green result. Open implementation PRs and
   obtain the other coding agent's review of the current revision. Address findings
   and recheck changed code. Follow user authorization and repo rules for merging;
   do not invent reviewer approval or claim an unreviewed latest commit is reviewed.
6. **Deploy and verify daily execution.** Configure the actual Claude cloud routine,
   its connectors, setup, approved credential/cookie settings, source limits,
   Sheet `_State` recovery data, concurrency, and
   schedule. Verify a real scheduled run and cloud restart/session restoration.
   Keep collecting healthy sources when one fails. Keep failed/setup-blocked sources
   visible with next actions. Stop challenged social sources per the plan.
   Deliver `docs/ROUTINE_PROMPT.md` with exact daily-run commands and
   `docs/CLOUD_RUNBOOK.md` with verified setup/recovery steps. Use the operational
   prompt in `JobHunter Daily`, not this implementation goal prompt. Daily runs
   execute the reviewed application, not rebuild it or modify its repository.
   Verify actual Sheet/source results, not merely a green session status.
7. **Arrange the results review.** Daily collection begins immediately after setup
   and verification, and saves per-run history. Arrange separate day-7/day-14 review
   follow-ups, or provide exact review dates and a ready-to-use review prompt.
   Notify on meaningful failures, required user actions, and review milestones,
   not unchanged daily status. The routine continues after day 14 unless I stop it.

If the selected cloud runtime cannot support a required capability, investigate
cloud-compatible options within the approved budget. Record the actual blocker
and required user action. Continue independent implementation, but never replace
the cloud requirement with a local process or declare incomplete deployment done.

## Required verification

Run the complete applicable test suite on the final implementation and after merges.
Record exact commands, revision, outcomes, and CI links in a sanitized evidence
document such as `docs/V0_VERIFICATION.md`. Existing `review_probe` tests are useful
examples, not proof of the production implementation.

- **Collectors:** parsing fixtures, pagination, source failures, bounded timeouts,
  transient retries/Retry-After, zero jobs versus blocked/failed, and continuation
  when one source fails. Retest real sources in the deployed cloud environment.
- **Gmail scope:** use sanitized fixtures to test labeled versus unrelated messages,
  mixed-label threads, missing/empty labels, forwarded alert parsing, and excluded
  account-security messages. Verify a real forwarded alert through the existing
  connector without inspecting unrelated personal mail or changing mailbox state.
- **Social collection:** read-only scope, per-source limits, immediate challenge
  stop, no same-day retries after blocking, credential/log redaction, missing and
  expired sessions, and actual cloud session restoration after restart.
- **Filtering/identity:** AI PM inclusion/exclusion, internship exclusion, US/remote/
  unknown location handling, distinct requisitions sharing a title, canonical URLs,
  source attribution, ambiguous cross-source matches, and 403 not meaning closed.
  For any implemented eligibility logic, include the plan's applicable edge cases;
  do not claim full eligibility while only the preliminary V0 filter exists.
- **Extraction:** schema/type validation, unsupported facts, evidence provenance,
  missing fields, malformed model output, duplicate records, and resistance to
  instructions embedded in job/email/post content. Exercise live extraction in Claude.
- **Sheets:** duplicate incoming and existing IDs, ambiguous headers, changed column
  order, row sorting between runs, RAW formula-like values, chunked writes, user-field
  preservation, and idempotency across repeated syncs.
- **Recovery:** interruption before writing, interruption after a successful write,
  append-success-but-timeout, re-read/reconciliation before retry, partial batch
  completion, concurrent runs, stale diagnostic markers, and restart with pending work.
- **Integration:** real configured workbook access, a second identical harvest/sync,
  at least five working application links checked (or report insufficient rows as
  outstanding), actual scheduled execution, fresh cloud session/restart, and proof
  that no local collector or writer was needed.
  Repeat-sync, recovery, and failure-injection checks replay sanitized saved records
  or fixtures with live social fetchers disabled. Manual social collection consumes
  that source's daily allowance in America/New_York; persist the allowance across
  restarts and skip another same-day collection. Verify live authenticated access
  after restart on the next eligible run. Do not count a skipped run as live proof.

Use deterministic fixtures for failure injection and live checks for real access.
Keep account data out of fixtures and avoid unnecessary live retries or spending.
Do not repeat passing checks unless new changes or unresolved concerns justify it.

## Definition of done

**Milestone A — V0 cloud deployment verified:**

- Reproducible locked installation and applicable final tests/CI pass; actionable
  independent-review findings are resolved, with the reviewed revision recorded.
- All planned sources have an implemented route or a specific documented access
  gap. LinkedIn and X have actual cloud attempts and recorded outcomes; missing
  required infrastructure/authentication remains unfinished setup.
- An actual scheduled cloud run delivers normalized AI PM rows, source health,
  and run history to the configured Google Sheet. I can open it. Repeat writes add
  no duplicate jobs and preserve Status, Notes, and My rating.
- Cloud authentication/session persistence, recovery, and one-writer behavior have
  evidence. Every operational step works without my computer running.
- Failed or blocked source attempts are recorded as coverage gaps, not successes;
  no critical integration is silently skipped. Follow `docs/PLAN.md` acceptance
  rules when deciding whether a documented access block prevents readiness.
- A self-contained routine prompt, setup/runbook, source inventory, evidence report,
  and precise operator actions are delivered. The daily trial is active.
- Day-7 progress and day-14 results follow-ups are scheduled, or their exact dates
  and review prompts are delivered. Neither elapsed observation period gates deployment.

**Separate follow-up — review results after 14 days (not a deployment completion gate):**

- Fourteen calendar days of cloud observation have elapsed from trial start; report
  actual successful/missed/blocked days per source, including sources added late.
- Deliver a source comparison covering unique relevant roles, first discovery,
  overlap, working links, user-rated usefulness when available, reliability,
  runtime/cost, and maintenance effort. Missing feedback or cost stays unknown.
- Provide evidence-backed keep/fix/extend/defer recommendations. Do not remove
  a source because of one empty run. Recommend further observation where warranted;
  ask before extending the evaluation task, and identify what remains unresolved.
- State the ongoing schedule and unresolved coverage gaps. Do not stop collection
  merely because the initial evaluation finished.

The implementation goal is complete when Milestone A passes and the review
follow-up is scheduled or its date and prompt are handed over. Future evaluation
is a separate task. If credentials, external access, or reviewer access prevent
deployment, report what is complete and pending; never fabricate results or label
an incomplete deployment as finished. Follow the host's goal-status rules.

At each milestone, report the outcome, evidence, remaining blockers, and next step
concisely. Keep progress in durable repo documentation so another conversation can
resume without repeating completed work.
