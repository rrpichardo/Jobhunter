# Cloud feasibility inventory

Observed on October 17, 2026. This records readiness, not deployment success.

## Current evidence

- Richard Chrome profile opens the authenticated Claude Code website.
- Scheduled tasks page reports **No scheduled tasks yet**.
- The cloud environment editor shows **JobHunterEnv**, network access **Full**,
  empty setup script and empty environment variables. Reuse this dedicated
  environment instead of creating a duplicate. No settings or credentials changed.
- The editor says environment variables are visible to environment users and
  explicitly says not to add secrets. Network secrets are described as letting
  sessions call APIs without seeing values; Add secret is disabled in the observed
  Full-network configuration. Neither mechanism has been proven to deliver a
  Sheets service-account file to Python. Do not paste credential JSON there.
- Local Claude Code is installed and subscription authentication is available;
  this supports code review, not proof of cloud execution or cloud credentials.

## Required proof still outstanding

| Requirement | Status | Exact next action |
| --- | --- | --- |
| Cloud Python and network | Unverified | Run a bounded cloud session installing from the reviewed lock and fetching one public Greenhouse posting. |
| Python Google authentication | Needs setup | Establish a supported secure credential-file mechanism before creating/provisioning writer credentials. |
| Destination workbook | Created, writer access pending | Empty private `Jobhunter V0` created and saved; see SETUP.md for its ID/link. Share only with the dedicated writer after secure cloud credential provisioning is established. |
| Real Claude extraction | Unverified | Produce one evidence-backed structured record in the actual cloud runtime and validate in Python. |
| Gmail connector | Needs verification | Inspect connector settings only to confirm connection; verify `JobHunter` label and scoped forwarding without reading unrelated mail. |
| Protected recovery/session state | Unverified | Prove durable storage and restore across fresh cloud sessions, including daily social allowances. |
| Single writer | Unverified | Prove runtime concurrency control plus an execution lock; a Sheet marker cannot provide an atomic lock. |
| LinkedIn cloud browser | Needs setup | Verify a supported interactive cloud authentication mechanism, then let user create/login to dedicated account. |
| X cloud session | Needs setup | Verify protected twscrape session provisioning/storage, then let user create/login to dedicated account. |
| Daily schedule | Not configured | After M0 checks pass, configure 06:07 America/New_York and observe a real scheduled delivery. |

## Bounded live cloud probe

[Cloud session](https://claude.ai/code/session_015wZ8bZKVEjazvzsqciHokQ)
ran in **JobHunterEnv** with Sonnet on October 17, 2026. It was read-only with
respect to the repository and accounts: no Gmail calls, social fetches, writes,
commits, schedules, or account setup. The public-request tool output was inspected.

- Ubuntu 24.04.5 LTS, x86_64; Python 3.13.16; preinstalled uv 0.11.32. These differ
  from the reviewed application's Python 3.12 / uv 0.13.1 pins, so the future setup
  script must install the pinned versions. Locked installation was not tested in
  this cloud session.
- One Python stdlib request, timeout 20 seconds and no retries, to
  `https://boards-api.greenhouse.io/v1/boards/anthropic/jobs?content=true` returned
  HTTP 200 and 655 jobs, including 15 product-manager titles.
- One public posting was retrieved: [Product Manager, Billing](https://job-boards.greenhouse.io/anthropic/jobs/5434361008),
  public job ID `5434361008`, requisition `267748`, location San Francisco / New York.
  This is fetch/parse evidence only, not a validated normalized record or an
  eligibility decision. Company-tag filtering has not been implemented.
- Gmail `search_threads`, `get_message`, `get_thread`, and `list_labels` tool names
  are available in the cloud session; none were invoked. Connector presence does
  not establish label-scoped alert access or Python Google authentication.
- Chromium/Playwright are reported preinstalled; no LinkedIn MCP is registered.
  No supported user-operated cloud login or protected session restore was established.
- Secure credential-file delivery, protected state shared across new routine
  sessions, and an atomic cross-session lock remain unknown. No secret was inspected.

The [cloud environment documentation](https://code.claude.com/docs/en/cloud-environments)
describes proxy-injected network secret headers, not a Google private-key file.
The [routine documentation](https://code.claude.com/docs/en/routines) describes
new sessions per trigger. Neither establishes the plan's secure temporary-file
authentication or durable session/recovery storage. A compatible supported
mechanism must be proven; do not substitute plain environment variables or Git.

No cloud source-to-Sheet run, scheduled delivery, recovery, or authenticated social
collection has been verified. The trial has not started; day-7/day-14 dates must
be based on the first verified trial run, not this bootstrap date. The inventory
table above remains an overview of required gates; public network access is now
proven, while application installation and all delivery/authentication gates remain open.

## Source access inventory

Every route below is planned, not implemented by the bootstrap PR. Historical
HTTP results in the plan do not establish current cloud access. The future YAML
registry must split each configured company/board/query route for evidence.

| Source / route | Prerequisite and next action |
| --- | --- |
| Greenhouse, Lever, Ashby, SmartRecruiters, Workable company boards | Build seeded board registry and retest public endpoints in cloud; Greenhouse is the M0 route. |
| HN Who's Hiring | Implement API fetch and validated Claude extraction. |
| YC product jobs | Parse `ycombinator.com/jobs/role/*` data; do not use login-walled Work at a Startup as the public route. |
| a16z portfolio jobs | Server search with coverage limits plus company-board discovery. |
| Getro VC boards (Accel, Primary, others) | Configure each board and parse structured page data; verify pagination. |
| Breakout List, Ramp AI Index | Company discovery feeding board probes, not direct job delivery. |
| Founders You Should Know | `foundersysk.com` showcased-company discovery where accessible; Ali Rohde RSS is a distinct route. |
| Next Play, Ali Rohde Jobs | Verify feed URLs, fetch RSS, extract source-backed records. |
| Remotive, RemoteOK, Himalayas, Jobicy, The Muse, WWR | Implement and test each public API/feed separately. |
| Lenny's / TrueUp | Forwarded labeled alerts; historical HTML route is superseded. |
| Gmail alerts: LinkedIn, Indeed, Glassdoor, approved newsletters | Existing Claude Gmail connector only; forwarded alerts labeled `JobHunter`; exclude all verification/login/password-reset messages. Missing or empty label never broadens scope. |
| a16z Build | Membership emails only if user is a member; no assumption of access. |
| JSearch | Inventory free-key readiness; inject `JSEARCH_API_KEY` securely if configured. |
| Adzuna | Inventory readiness; inject `ADZUNA_APP_ID` / `ADZUNA_APP_KEY` securely if configured. |
| Jooble | Inventory readiness; inject `JOOBLE_API_KEY` securely if configured. |
| Selected JobSpy boards | Disabled by default; separate optional extra, enable/test each selected board. |
| LinkedIn JobSpy guest comparison | Separate evidence route; existing guest 429 is historical, not authorization to retry challenges. |
| LinkedIn logged-in jobs and hiring posts | Cloud-hosted MCP and browser; dedicated account, protected session, read-only tools, persisted daily allowance. |
| X hiring posts | Separate social extra with pinned/tested twscrape; dedicated cloud session and persisted daily allowance. |
| Public LinkedIn/X WebSearch scouts | Separate limited-coverage search routes; do not claim authenticated source coverage. |
| Manually forwarded LinkedIn/X posts | Labeled Gmail extraction, distinct from live social collection. |
| Cosign | Explicitly deferred per plan; account-gated beta, not silently treated as working. |

Social limits and stop rules remain exactly those in `PLAN.md`: LinkedIn at most
5 searches / 50 detail views; X at most 10 queries / 200 posts; one live attempt
per source per America/New_York day; stop immediately on challenge, 429, or warning.
