# JobHunter implementation setup

## October 18 collection preference update

The user permits remote South/Latin America roles regardless of salary. For
on-site/hybrid roles in that region, only Colombia and the Dominican Republic
qualify, with an annual USD salary range reaching at least 70,000. The numeric
answer is interpreted as annual USD, following the question presented to the user.
Retain the source's location and explicit remote evidence. Missing/ambiguous
currency or annual pay units do not prove that a salary matches; do not convert
COP/DOP amounts or hourly/monthly/total compensation without an approved rule.

The user directed finishing the PR repairs locally and making no further pushes.
Claude Code review remains required before any later integration; no merge or
deployment is authorized by these preference clarifications.

Record non-secret answers here before cloud integration. Never record passwords,
API keys, service-account JSON, cookies, browser profiles, or routine tokens.
Decisions below are user-confirmed; deployment/readiness remains unverified unless
explicitly stated. Do not confuse the selected approach with completed setup.

| Prerequisite | Current answer / next action |
| --- | --- |
| Claude subscription | Confirmed: Pro. |
| Cloud environment | User reports two existing environments: `Boom` (default) and `Default`. Neither is selected for JobHunter. Use or create a dedicated `JobHunter` environment and set Full network access before adding Google credentials. Creation/configuration and access are still to be verified. |
| Routine | Confirmed: no JobHunter routine exists yet. Create and verify the cloud routine during V0 implementation. |
| Setup assistance | User authorizes operating this local computer, preferably Chrome, for the specified setup. Agent navigates and configures non-secret settings; user enters private details and completes account creation/verification. Local setup does not change the cloud-only production requirement. See `docs/IMPLEMENTATION_PROMPT.md`. |
| Gmail connection | Keep the existing Claude Gmail connector. User reports it is connected but the account identity is unconfirmed. The dedicated job-alert Gmail is not connected directly. Confirm the connected account through account settings; do not inspect unrelated mail to discover it. |
| Alert routing | Confirmed approach: forward only job alerts from the dedicated job-alert Gmail into the connected Gmail; apply `JobHunter` there and read only that label. The pasted plan says forwarding/label setup is pending, so verify readiness rather than assuming it is complete. Do not replace the connector with the dedicated account. |
| Verification messages | The dedicated job-alert Gmail is the sign-up address for LinkedIn and X. Keep login, verification, and password-reset messages there; do not forward or process them. A provider's sender address alone does not distinguish alerts from account-security messages. |
| Destination Google Sheet | Confirmed: not created. Guide creation of `Jobhunter V0`, then record its URL/ID and share it with the dedicated writer service account. No workbook URL exists yet. |
| Google service-account authentication | Confirmed: not created. Guide creation, Sheets API setup, workbook access, and secure runtime provisioning after the dedicated cloud environment is configured. No credential contents in chat or Git. |
| LinkedIn test account | Confirmed: not created. User creates it with the dedicated job-alert Gmail, authenticates the cloud browser through a supported secure setup flow, and configures job-search alerts. |
| X test account | Confirmed: not created. User creates it with the dedicated job-alert Gmail; provision supported session authentication securely in the cloud. |
| Job API access | Inventory which of JSearch, Adzuna, and Jooble are configured; missing keys remain visible as needs setup. Ask only for readiness/provider names. |
| Spending | Confirmed: no new paid services or API usage without approval. Existing subscription usage still applies. |
| Daily schedule | Confirmed: 06:07 America/New_York. |
| Observation period | Confirmed: initial 14 calendar days, with a day-7 progress review and extensions for insufficient evidence. |
| Independent review | Verify Codex automatic PR review and Claude review access; select the reviewer opposite the implementer. |

The user answered the environment/Gmail, spending/schedule/trial, and
Sheet/service-account/social-account readiness questions in the preparation
conversation. Guide the outstanding setup rather than repeating those questions.
Job API provider readiness and independent-review access still need an inventory.
Independent coding and offline tests can proceed while credentials are being set
up; live integration and deployment remain gated on the relevant prerequisites.

The repository is not yet the deployed application: current files include the
plan, review guidance, isolated scraping probes, and a Sheets upsert review example.
Recheck repository state at implementation start; do not treat those probes as
production collectors or a complete writer.

## October 17, 2026 inspection

The user selected the **Richard** Chrome profile for setup assistance. The actual
Claude Code UI now contains **JobHunterEnv** with **Full** network access; its
setup script and environment-variable fields are empty. Preserve this dedicated
environment and the other environments. No settings or credentials were changed.
The Scheduled page shows no scheduled tasks. This updates the historical
environment inventory above; it does not establish runtime feasibility.

See [cloud capability and source inventory](CLOUD_CAPABILITIES.md) for the current
evidence and exact next checks. At initial inspection the editor warned that
environment variables are visible to environment users and not intended for
credentials. The explicit, bounded user approval below now permits that fallback;
actual Python workbook access still requires proof.

The approved empty **Jobhunter V0** workbook was created through the browser after
an exact-title search found no existing match. The UI confirmed **Saved to Drive**
and **Private to only me**. Its configured destination is
`JOBHUNTER_SPREADSHEET_ID=1kG1QeLhYmiImPW4pMtEDIHI6I-dK1Ztig_77B8mGrPw`;
[open workbook](https://docs.google.com/spreadsheets/d/1kG1QeLhYmiImPW4pMtEDIHI6I-dK1Ztig_77B8mGrPw/edit).
This supersedes the earlier not-created answer. No job data, tabs, service-account
sharing, credentials, or integration test was added. Create/provision the writer
only after a supported secure cloud credential mechanism is established.

## User-supplied session-bootstrap clarification

The user supplied Claude Code's cookie-bootstrap approach: local browser login is
initial setup only; every daily cloud run reconstructs the dedicated LinkedIn/X
session from cookies entered directly by the user into JobHunterEnv settings.
Do not require an interactive cloud login or persist secret browser profiles across
runs. Environment variables are permitted for these dedicated-account cookies,
with the visibility caveat described in PLAN.md. No cookie value may appear in
chat, screenshots, logs, Git or ordinary artifacts. Agents must not inspect values.

Persist only non-secret allowance/run/recovery data in Sheet `_State`. This does
not establish an atomic lock; one-writer serialization remains to be verified.
No new hosting service/account is authorized. No source is dropped, deferred, or
replaced by email. Dedicated source accounts are still the planned user-created
accounts; no account creation or cookie provisioning has happened yet.

Google service-account credential delivery was a separate unresolved prerequisite;
the subsequent user approval below defines its fallback. Current twscrape documentation
supports cookie-based account setup, but its default waits/rotation/retries need
adaptation to the plan's immediate challenge/429 stop rules before live use.
The proposed LinkedIn MCP package/configuration is not yet selected or verified.

## Explicit Google credential approval and UI check

The user authorizes the agent to operate all non-private setup steps. First check
whether Add secret offers a compatible GCP service-account-key type; prefer that
if available and it works with Python without placing the key in the session.
On re-inspection, **Add secret is disabled** in JobHunterEnv, so the dropdown and
its types could not be inspected. No value entered and no settings changed.
Do not claim that a GCP type was proven absent. If still unavailable at provisioning,
the user-approved fallback is a dedicated JobHunterEnv credential variable.

Conditions: dedicated service account with Editor on only Jobhunter V0, no project
IAM roles, only Sheets API enabled; load the credential in memory where possible.
If a file is required, make it 0600 in a private temporary directory and delete it
at run end. Never print/read back environment values or keys into model output,
chat, logs, screenshots or Git. User rotates the key if exposed. Provisioning and
workbook access are not yet verified; no service account/key has been created.

Google Cloud console access is unavailable in the initially selected Google
account. User chose to switch to another existing account; the chooser is open
and the exact account is awaiting user selection. No new account, project, API,
billing, service account or key was created. Keep setup gated on actual access.

If the implementing chat cannot operate the Claude cloud configuration, prepare
the smallest necessary manual step and a self-contained routine prompt. First use
available local computer/browser controls to perform authorized setup on the user's
behalf; avoid delegating all setup clicks when the agent can perform them.
Keep deployment verification open until actual run evidence is obtained. Do not
claim that a local Codex automation is the requested Claude cloud routine.

## Google setup update after PR #5

The user selected an existing account with working Cloud access. A dedicated
JobHunter project and Sheets-writer service account now exist. No project IAM
roles were selected; Sheets API was enabled. Following the user's explicit
confirmation, only the Jobhunter V0 workbook was shared as Editor (notifications
off), and a JSON key was downloaded to the user's computer. The agent did not
open or read it. No billing account was selected during project creation; billing
status itself has not yet been independently verified.

Add secret is now enabled in JobHunterEnv. The actual menu includes **GCP access
token (with Service Account Key)**, superseding the earlier disabled-control
inspection. Its form says the proxy mints access tokens and keeps the key outside
the VM. The prepared secret restricts its host to `sheets.googleapis.com`, its
path prefix to `/v4/spreadsheets/` followed by the configured workbook ID, its
scope to `https://www.googleapis.com/auth/spreadsheets`, and leaves Subject blank.
The user is entering the key directly and must finish saving/closing the form.
Do not inspect the form while its key is visible. Live gspread compatibility is
still outstanding; do not substitute the credential-variable fallback first.

The next connection attempt uses `gspread.Client` with google-auth
`AnonymousCredentials`, a 20-second timeout and `open_by_key` only. Authentication
must be injected by the proxy after requests leave the VM; no key or token is
loaded in Python. Explicit non-secret configuration is:
`JOBHUNTER_GOOGLE_AUTH_MODE=network-secret` and the existing
`JOBHUNTER_SPREADSHEET_ID`. Tests alone do not establish authenticated access.

### Latest user direction and saved state

The key was subsequently disclosed in chat. The user explicitly accepted this
and authorized using that dedicated key for the approved setup. Replacement was
recommended; it is not an additional mandatory gate under the user's direction.
Keep the value out of Git/logs/PRs/handoff. This is a specific exception for this
key, not general permission to publish credentials. See AGENTS.md and the current
[Claude handoff](CLAUDE_HANDOFF.md).

Agent transferred the complete JSON directly via native editor copy/paste into
the protected GCP secret field, without printing its contents. The Add action
succeeded: UI showed its restricted host/workbook path and Replace/Delete controls.
The editor was closed after saving the two non-secret variables described above.
The key is stored as a network secret, not an environment credential variable.
A bounded read-only Python connection test is running in the actual JobHunterEnv;
its result and harmless write/lock endpoint checks remain to be recorded.
The downloaded file stays under user control; no agent deletion is authorized.

Initial cloud read access now succeeded at `0260388`: gspread opened only the
configured workbook and counted one worksheet, exit 0, clean tree. Actual command
output inspected in the UI. No Sheet write, RAW write/readback or lock batch
endpoint proof yet. No key/token/file was supplied to Python; proxy secret used.


### Handoff checkpoint superseding earlier setup status

Google network secret and non-secret variables are saved; actual read access and
isolated RAW/structural endpoints succeeded (ATTEMPTS.md). Application writer,
recovery, overlap and schedule remain unproved. Google readback found JobHunter
linked automatically to the existing free trial. User explicitly chose to leave
that link unchanged; the disable dialog was canceled and linkage rechecked.
No billing setting or upgrade was made. Do not unlink or ask again.

Reciprocal Codex review setup is tracked in REVIEW_WORKFLOW.md. Do not equate
repository instructions with a verified automatic-review account setting.
