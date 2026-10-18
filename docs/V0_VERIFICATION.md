

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

