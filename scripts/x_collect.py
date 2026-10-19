"""Read-only X hiring-post search for the cloud routine. Needs the user's A2 go-ahead before any live run.

  uv run --locked --extra social python -m scripts.x_collect --run-id <run> --output <new file outside checkout>
      [--lookback-days 28] [--queries sources/social_queries.yaml]

Order (docs/PLAN.md): check the output path, check the cookie variables exist (names only, never values), reserve
today's allowance in `_State` BEFORE any request, search, write the candidate file, then close the allowance.
Exit 0 = candidate file written (it may carry a fixed error word that the Sources tab will show); 3 = today's
allowance is already spent (collect nothing); 4 = cookies not set up; 2 = anything else (collect nothing).
The cookies are only read from the environment, only given to a private temporary account database, and never
printed, logged, written to the candidate file or kept after the run.
"""

import argparse
import asyncio
from datetime import datetime, timezone
import os
from pathlib import Path
import random
import shutil
import stat
import tempfile
import time

from jobhunter.allowance import AllowanceSpent, finish, reserve
from jobhunter.artifacts import new_artifact_path, safe_error_code, write_artifact
from scripts.allowance import ALLOWANCE_ERRORS
from scripts.sheets_sync import SAFE_ERRORS
from jobhunter.social_collect import (FetchBlocked, FetchRateLimited, LIMITS, allowance_outcome, build_query,
                                      candidate_artifact, collect_posts, load_queries, since_date)

SOURCE = 'x-twscrape'
COOKIE_VARIABLES = ('X_AUTH_TOKEN', 'X_CT0')
EXIT_SPENT, EXIT_NEEDS_SETUP = 3, 4
ACCOUNT = 'jobhunter-x'  # a label for twscrape's private account table; not a real account name


class TwscrapeFetcher:
    """Thin adapter over twscrape 0.20.1 (pinned in the `social` extra). Cookies go straight into a private
    temporary SQLite file and are deleted with it. Verified against the library source, not yet against X."""

    def __init__(self, auth_token, ct0):
        # twscrape can send anonymous usage counts to PostHog from its command line; turn that off for certain.
        os.environ['TWS_TELEMETRY'] = '0'
        os.environ['DO_NOT_TRACK'] = '1'
        import twscrape  # imported late so the offline tests and the rest of the repo never need it
        self._twscrape = twscrape
        twscrape.set_log_level('ERROR')
        self._dir = Path(tempfile.mkdtemp(prefix='.jobhunter-x-'))
        self._dir.chmod(stat.S_IRWXU)
        self._loop = asyncio.new_event_loop()
        self._api = twscrape.API(str(self._dir / 'accounts.db'), raise_when_no_account=True)
        self._loop.run_until_complete(
            self._api.pool.add_account_cookies(ACCOUNT, f'auth_token={auth_token}; ct0={ct0}'))

    def search(self, query, limit):
        try:
            return self._loop.run_until_complete(self._search(query, limit))
        except self._twscrape.NoAccountError:
            raise FetchBlocked from None  # the saved session was rejected or is cooling down
        except self._twscrape.HttpStatusError as exc:
            code = getattr(getattr(exc, 'response', None), 'status_code', None)
            if code in (401, 403):
                raise FetchBlocked from None
            if code == 429:
                raise FetchRateLimited from None
            raise

    async def _search(self, query, limit):
        found = []
        async for tweet in self._api.search(query, limit=limit):
            if tweet.retweetedTweet is not None:
                continue  # a repost repeats someone else's post
            found.append({'url': tweet.url, 'created_at': tweet.date.isoformat(), 'text': tweet.rawContent,
                          'links': [link.url for link in tweet.links]})
        return found

    def close(self):
        self._loop.close()
        shutil.rmtree(self._dir, ignore_errors=True)


def main(argv=None, *, store=None, fetcher=None, environ=None, now=None, sleep=time.sleep, rng=random.random):
    parser = argparse.ArgumentParser(description='Read-only X hiring-post search; writes a candidate file only.')
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--lookback-days', type=int, default=28)
    parser.add_argument('--queries', default='sources/social_queries.yaml')
    args = parser.parse_args(argv)
    environ = os.environ if environ is None else environ
    now = now or (lambda: datetime.now(timezone.utc).isoformat())
    try:
        if not 1 <= args.lookback_days <= 365:
            raise ValueError('invalid_lookback_days')
        new_artifact_path(args.output)  # a doomed output path must not spend the day's allowance
        queries = load_queries(args.queries, SOURCE)
        missing = [name for name in COOKIE_VARIABLES if not environ.get(name)]
        if missing:
            print(f"x_needs_setup: set {' and '.join(missing)} in the environment settings (names only; "
                  'values are never printed). Nothing was collected and no allowance was spent.')
            return EXIT_NEEDS_SETUP
        if store is None:
            from jobhunter.google_auth import open_workbook
            from jobhunter.sheet_io import GspreadStore
            store = GspreadStore(open_workbook())
        try:
            day = reserve(store, SOURCE, args.run_id)
        except AllowanceSpent:
            print('allowance_spent: x-twscrape already used today (America/New_York); collect nothing')
            return EXIT_SPENT
        outcome, items, error = 'failed', [], 'social_collector_error'
        try:
            captured = now()
            if fetcher is None:
                fetcher = TwscrapeFetcher(environ['X_AUTH_TOKEN'], environ['X_CT0'])
            since = since_date(captured, args.lookback_days)
            items, ran, error = collect_posts(
                fetcher.search, [build_query(q, since) for q in queries],
                max_posts=LIMITS[SOURCE]['posts'], sleep=sleep, rng=rng)
            digest = write_artifact(args.output, candidate_artifact(SOURCE, items, captured,
                                                                    queries_run=ran, error=error))
            outcome = allowance_outcome(items, error)
        finally:
            close = getattr(fetcher, 'close', None)
            if close:
                close()
            try:
                finish(store, SOURCE, args.run_id, outcome, day=day)
            except Exception:  # noqa: BLE001 - the day stays spent either way; say so without hiding the result
                print('allowance_close_failed: the day stays spent')
        print(f'x_collected: queries_run={ran} posts={len(items)} error={error or "none"} allowance_day={day}')
        print(f'x_candidates_sha256={digest}')
        return 0
    except Exception as exc:  # noqa: BLE001
        code = str(exc)
        if code not in SAFE_ERRORS | ALLOWANCE_ERRORS | {'invalid_social_queries', 'invalid_lookback_days'}:
            code = safe_error_code(exc)
        print(f'x_failed: {code}; collect nothing')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
