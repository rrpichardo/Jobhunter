# Every limit that exists today

As of October 18, 2026 on branch `claude/pending-and-limits-docs` (the stack of PRs
#18 to #21). Values come from the code, not from memory. "Kind": **target** means we
aim at it; **safety stop** means a guard that is reported when hit; **external**
means set by another service. Today every number below is a constant in code or in
`sources/v0_sources.yaml`; a single editable config is pending (PENDING.md E3).

## Collection volume

| Limit | Value | Kind | Where |
| --- | --- | --- | --- |
| Jobs per source per run | no cap | removed in #19 | `scripts/source_probe.py` |
| Jobs per run overall | no cap | removed in #19 | `scripts/source_probe.py` |
| Lookback window | 28 days (`--lookback-days`, 1 to 365) | target | `scripts/source_probe.py`, `scripts/hn_hiring.py` |
| Detail pages opened per detail source per run | 300 (`source_probe --detail-safety-stop`, 1 to 100000) | safety stop (`details_skipped`) | `DETAIL_SAFETY_STOP` |
| Polite delay between requests | 1.0 s (`--delay`) | target | `scripts/source_probe.py` |
| Largest response accepted | 40 MB | safety stop | `MAX_BYTES` |
| Remotive page | 50 jobs, product category | external, registry URL | `sources/v0_sources.yaml` |
| Himalayas page | 50 jobs, all categories | external, registry URL | `sources/v0_sources.yaml` |
| Jobicy page | 50 jobs, product tag | external, registry URL | `sources/v0_sources.yaml` |
| The Muse | page 1 only (about 20 jobs) | gap | `sources/v0_sources.yaml` |
| JSearch | 1 request, 1 page (about 10 jobs); free plan about 200 requests a month | external, no new spending | registry |
| Jooble | 1 request, page 1 | gap | registry |

## AI reading

| Limit | Value | Kind | Where |
| --- | --- | --- | --- |
| Items handed to the AI per run | 1000 (`ai_queue pull --limit`) | safety stop | `WORK_SAFETY_STOP` |
| Hacker News candidate comments per run | 1500 (`hn_hiring candidates --candidate-safety-stop`, 1 to 100000) | safety stop | `CANDIDATE_SAFETY_STOP` |
| Hacker News comment length | 20,000 characters | safety stop | `MAX_COMMENT_CHARS` |
| Gmail AI extractions per run | 1000 | safety stop | `EXTRACTION_SAFETY_STOP` |
| Gmail messages read per run | 50 (one page) | gap until the live adapter | `jobhunter/gmail_alerts.py` |
| Gmail results per extractor reply | 150 | sanity bound | `jobhunter/gmail_alerts.py` |
| Description quote length | 300 characters | rule | validators |

## Writing to the Sheet

| Limit | Value | Kind | Where |
| --- | --- | --- | --- |
| Jobs per writer batch | 150 | batch size, not a delivery limit | `JOB_BATCH_SIZE` |
| Pause between batches | 2 s (`sheets_sync --batch-pause`, 0 to 60) | target | `BATCH_PAUSE_SECONDS` |
| Writes per Sheets request | up to 100 (`--chunk-size`, 1 to 100), also capped near 1 MB | batch size | `scripts/sheets_sync.py` |
| Recovery journal | 1 MB per batch | safety stop | `jobhunter/sheet_journal.py` |
| Retries on a transient Sheets error | 3 attempts, wait at most 60 s | safety stop | `jobhunter/sheets.py` |

## Social sources (planned; collectors not built)

| Limit | Value | Kind |
| --- | --- | --- |
| LinkedIn job searches per run | 5 | user-confirmed October 18 |
| LinkedIn hiring-post searches per run | 5 (separate) | user-confirmed October 18 |
| LinkedIn detail views per run | 50 or fewer | plan |
| X queries per run | 10 | plan |
| X posts per run | 200 | plan |
| Live collections per social source per America/New_York day | 1, reserved in `_State` first | plan; allowance code not built |
| Searches per day, LinkedIn | 50 was declined for now | user decision |

LinkedIn does not publish an official safe number. The 30 to 50 searches a day
figure comes from third-party guides and is not a guarantee against restriction.

## First pull versus daily runs

The first pull is a one-off manual four-week backfill where these safety stops are
meant to be raised or ignored. The flags named in the tables above do that without
editing code, and each run prints the limits it used (`limits: ...`). The Gmail
extraction stop (1000) and the Gmail page (50) have no flag yet; Gmail is not live. Limits set by a source's
own API (the "external" and "gap" rows) cannot be ignored from our side.
