# First live test: X and LinkedIn hiring posts (runbook)

Written October 19, 2026. Nothing below has been run. It needs the user's go-ahead (A2) because each live source
spends that day's allowance (one live collection per source per America/New_York day, reserved in `_State` before
the first request, and kept even if the run fails). Run it by hand in a JobHunterEnv session, never from the daily
routine, and never twice in a day.

## Before you start (names only; never print values)

1. The environment settings hold `X_AUTH_TOKEN` and `X_CT0` (X) and `LINKEDIN_LI_AT` (LinkedIn; `LI_AT` also works).
2. Copy the spreadsheet first (File > Make a copy), so a surprise can be undone.
3. `uv sync --locked --extra social` (installs twscrape 0.20.1 and playwright 1.56.0; Chromium 1194 is preinstalled).
4. `uv run --locked python -m scripts.run_window --mode manual` prints `window_days=28`. This tool is added by PR #41, so it
   only exists once #41 is merged (without it the command stops with `No module named scripts.run_window`). The live test
   therefore waits for #40, #41 and #43 to be merged. If you must run before #41, skip this check: step 1 passes
   `--lookback-days 28` explicitly.
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
| `linkedin_jobs_collected: queries_run=5 jobs=N error=none` (printed after the post lines; the job searches run in the same session and use the same allowance) | jobs above 0 | same words; if the post searches were refused (`social_login_failed` or `social_rate_limited`) the job searches are not attempted and this line repeats that word |
| `search_N: kind=posts status=200 wall=False ready=True post_ids=A cards=B short_cards=0 median_chars=N ...` | `cards` close to `post_ids`, `short_cards` 0 and `median_chars` in the hundreds (a card of a few characters means the card boundary was misread; the run then fails with `social_collector_error` instead of feeding Claude page furniture); `ready=False` means no result appeared within 25 s | `wall=True` or status 999/403: LinkedIn sent the session to a login or check page (log in yourself, refresh `li_at`); `post_ids=0` with `no_results=False`: the page layout was not recognised (the day is spent, report the `search_N` lines so the reader can be adjusted); `undated` above 0: ids without a believable date |

The five job searches also print `search_N: kind=jobs status=200 wall=False path=/jobs ready=True job_ids=A cards=B empty=0 no_results=False script_ids=C login_form=False short_cards=0 median_chars=N outside_window=D undated=E` lines after the post searches. Healthy: `cards` close to `job_ids`, `short_cards` 0, `median_chars` in the hundreds, `login_form=False`. `undated` counts cards with no readable age ("3 days ago"); those take the capture day, so a few are normal. `wall=True`, status 999/403 or `login_form=True` means the same as for posts: stop and tell the user. `job_ids=0` with `no_results=False` means the job page layout was not recognised (the day is spent; report the lines).

Exit codes: 0 candidates written, 3 allowance already spent today (nothing collected), 4 cookies, library or browser
not set up (including a browser that cannot start with that cookie value; nothing spent), 2 anything else (nothing collected). Do NOT retry a spent day.

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

- Sources tab: `x-twscrape`, `linkedin-login` and `linkedin-jobs` show OK, OK-zero-jobs, blocked (account refused) or failed. Once a result is
  delivered they replace the "needs setup" placeholders `x-hiring-posts` and `linkedin-logged-in`, so those two names are NOT
  what to look for (they stay visible only for a source whose result was not delivered). Checked on October 19 by driving the
  collect, queue, validate, probe and Sheet-writer steps offline with stand-in pages and an in-memory sheet.
- Jobs tab: rows whose Job ID starts with `x:`, `linkedin-post:` or `linkedin-job:` are leads (the post or job-card link); check three by hand.
- `_State` tab: `allowance/x-twscrape/<date>` and `allowance/linkedin-login/<date>` hold ok, zero, blocked or failed.

## Stop conditions

Any `wall=True`, `social_login_failed` or `social_rate_limited`: stop, do not retry, tell the user. The accounts are
dedicated test accounts and the plan allows one live session per source per day.
