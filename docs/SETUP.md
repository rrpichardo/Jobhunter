# JobHunter implementation setup

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

If the implementing chat cannot operate the Claude cloud configuration, prepare
the smallest necessary manual step and a self-contained routine prompt. First use
available local computer/browser controls to perform authorized setup on the user's
behalf; avoid delegating all setup clicks when the agent can perform them.
Keep deployment verification open until actual run evidence is obtained. Do not
claim that a local Codex automation is the requested Claude cloud routine.
