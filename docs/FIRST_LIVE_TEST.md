# First live test: X and LinkedIn hiring posts (runbook)

Written October 19, 2026. Nothing below has been run. It needs the user's go-ahead (A2) because each live source
spends that day's allowance (one live collection per source per America/New_York day, reserved in `_State` before
the first request, and kept even if the run fails). Run it by hand in a JobHunterEnv session, never from the daily
routine, and never twice in a day.

## Before you start (names only; never print values)

1. The environment settings hold `X_AUTH_TOKEN` and `X_CT0` (X) and `LINKEDIN_LI_AT` (LinkedIn; `LI_AT` also works).
2. Copy the spreadsheet first (File > Make a copy), so a surprise can be undone.
3. `uv sync --locked --extra social` (installs twscrape 0.20.1 and playwright 1.56.0; Chromium 1194 is preinstalled).
4. `uv run --locked python -m scripts.run_window --mode manual` prints `window_days=28`.
5. A private run folder outside the checkout: `DIR=$(mktemp -d)`; `RUN=live-$(TZ=America/New_York date +%Y%m%d-%H%M%S)-$(openssl rand -hex 3)`.

## Step 1: collect only (writes `_State` allowance rows, nothing else in the Sheet)

```
uv run --locked --extra social python -m scripts.x_collect --run-id $RUN-x --output $DIR/x_cand.json --lookback-days 28
uv run --locked --extra social python -m scripts.linkedin_collect --run-id $RUN-li --output $DIR/li_cand.json \
    --jobs-output $DIR/li_jobs.json --lookback-days 28
```

Read the printed lines (they hold numbers and fixed words only):

| Line | Healthy | If not |
| --- | --- | --- |
| `x_collected: queries_run=10 posts=N error=none` | posts above 0 | `social_login_failed`: the X cookies are wrong or expired; `social_rate_limited`: stop for the day; `social_collector_error`: a defect, report it |
| `linkedin_collected: queries_run=5 posts=N error=none` | posts above 0 | same words |
| `search_N: status=200 wall=False kind=posts post_ids=A cards=B undated=0 ...` (and `kind=jobs job_ids=A cards=B ...` for job searches) | `cards` close to `post_ids` | `wall=True` or status 999/403: LinkedIn sent the session to a login or check page (log in yourself, refresh `li_at`); `post_ids=0` with `no_results=False`: the page layout was not recognised (the day is spent, report the `search_N` lines so the reader can be adjusted); `undated` above 0: ids without a believable date |

Exit codes: 0 candidates written, 3 allowance already spent today (nothing collected), 4 cookies or library missing
(nothing spent), 2 anything else (nothing collected). Do NOT retry a spent day.

## Step 2: read and deliver (only if step 1 gave posts)

For each source (`x-twscrape` with `$DIR/x_cand.json`, `linkedin-login` with `$DIR/li_cand.json`, `linkedin-jobs` with
`$DIR/li_jobs.json`; the last two come from ONE LinkedIn session and ONE allowance):

```
uv run --locked python -m scripts.ai_queue pull --source <source> --candidates <file> --candidates-sha256 <digest> \
    --id-field item_id --output $DIR/<name>_work.json
(Claude reads each post and writes $DIR/<name>_facts.json as in docs/ROUTINE_PROMPT.md section 1)
uv run --locked python -m scripts.social_posts validate --source <source> --candidates $DIR/<name>_work.json \
    --candidates-sha256 <work digest> --extractions $DIR/<name>_facts.json --output $DIR/<name>_result.json
```

Then `source_probe --social-result $DIR/x_result.json --social-result-sha256 <digest> --social-result ... ` together with
the usual options, `sheets_sync --input-sha256 <probe digest> --run-id $RUN`, and only after it exits 0,
`ai_queue commit --source <source> --result <validated file> --result-sha256 <digest>`.

## What to look at afterwards

- Sources tab: `x-hiring-posts` and `linkedin-logged-in` show OK, OK-zero-jobs, blocked (account refused) or failed.
- Jobs tab: rows whose Job ID starts with `x:` or `linkedin-post:` are leads with the post URL; check three by hand.
- `_State` tab: `allowance/x-twscrape/<date>` and `allowance/linkedin-login/<date>` hold ok, zero, blocked or failed.

## Stop conditions

Any `wall=True`, `social_login_failed` or `social_rate_limited`: stop, do not retry, tell the user. The accounts are
dedicated test accounts and the plan allows one live session per source per day.
