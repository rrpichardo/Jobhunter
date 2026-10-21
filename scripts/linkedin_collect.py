"""Read-only LinkedIn hiring-post search for the cloud routine. Needs the user's A2 go-ahead before any live run.

  uv run --locked --extra social python -m scripts.linkedin_collect --run-id <run> --output <new file outside checkout>
      [--lookback-days 28] [--queries sources/social_queries.yaml]

Order (docs/PLAN.md): check the output path, check the cookie variable exists (name only, never the value), check the
browser library is installed, reserve today's allowance in `_State` BEFORE any request, search, write the candidate
file, then close the allowance. Exit 0 = candidate file written (it may carry a fixed error word that the Sources tab
shows); 3 = today's allowance is already spent (collect nothing); 4 = not set up; 2 = anything else (collect nothing).
It opens a headless browser with the saved `li_at` session and only reads the search results page: it never types,
likes, follows, connects, messages or posts. The cookie is only read from the environment, only given to the
browser context in memory, and never printed, logged, written to the candidate file or kept after the run.
"""

import argparse
from datetime import datetime, timedelta, timezone
import importlib.util
import os
import random
import re
import sys
import time
from urllib.parse import quote, urlsplit

from jobhunter.allowance import AllowanceSpent, finish, reserve
from jobhunter.artifacts import new_artifact_path, safe_error_code, write_artifact
from jobhunter.linkedin_cards import extract_post_cards
from jobhunter.social_collect import (COLLECTOR_ERROR, FetchBlocked, FetchRateLimited, LIMITS, allowance_outcome,
                                      candidate_artifact, collect_posts, load_queries, since_date)
from scripts.allowance import ALLOWANCE_ERRORS
from scripts.sheets_sync import SAFE_ERRORS

SOURCE = 'linkedin-login'
COOKIE_VARIABLES = ('LINKEDIN_LI_AT', 'LI_AT')  # either name; the first one that is set is used
EXIT_SPENT, EXIT_NEEDS_SETUP = 3, 4
SEARCH_URL = 'https://www.linkedin.com/search/results/content/?keywords={keywords}&datePosted=%22{recent}%22&sortBy=%22date_posted%22&origin=FACETED_SEARCH'
WALL_PATHS = ('/login', '/authwall', '/checkpoint', '/uas/', '/signup')  # LinkedIn sends logged-out visitors here
SCROLLS = 4
READY_SECONDS = 25
READY_SELECTOR = 'a[href*="urn:li:activity"], a[href*="urn:li:ugcPost"], a[href*="urn:li:share"], a[href*="/posts/"], [data-urn*="urn:li:"]'
NO_RESULTS_TEXT = 'no results found'
MAX_EXPANDS = 40
MORE_BUTTON = r'^(?:…|\.\.\.)\s*(?:see\s+)?more$'  # the "…more" that opens a cut-off post; nothing else is clicked


class Page:
    def __init__(self, url, status, html, ready=True):
        self.url, self.status, self.html, self.ready = url, status, html, ready


class BrowserSession:
    """A headless Chromium with the saved session; the cookie goes straight into the browser context in memory."""

    def __init__(self, li_at, rng=random.random):
        from playwright.sync_api import sync_playwright  # late: the offline tests and the rest of the repo never need it
        self._rng = rng
        self._playwright = sync_playwright().start()
        try:
            self._browser = self._playwright.chromium.launch(headless=True)
            # The browser identifies itself as it is (no user-agent override: a disguise that disagrees with the
            # browser's other signals only adds a mismatch). If LinkedIn refuses it, that is a decision for the user.
            self._context = self._browser.new_context(locale='en-US', viewport={'width': 1366, 'height': 900})
            self._context.add_cookies([{'name': 'li_at', 'value': li_at, 'domain': '.linkedin.com', 'path': '/',
                                        'secure': True, 'httpOnly': True}])
        except BaseException:
            self.close()
            raise

    def get(self, url, ready=READY_SELECTOR):
        page = self._context.new_page()
        try:
            response = page.goto(url, wait_until='domcontentloaded', timeout=45000)
            status = response.status if response is not None else 0
            found = False
            if status == 200 and not urlsplit(page.url).path.startswith(WALL_PATHS):
                try:  # LinkedIn fills results in after the page loads: wait for a result or the "no results" notice
                    page.wait_for_function(
                        '([selector, empty]) => !!document.querySelector(selector) || new RegExp(empty, "i").test(document.body.innerText)',
                        arg=[ready, NO_RESULTS_TEXT], timeout=READY_SECONDS * 1000)
                    found = True
                except Exception:  # noqa: BLE001 - read what is there; the numbers say whether anything was
                    pass
            if status == 200 and not urlsplit(page.url).path.startswith(WALL_PATHS):
                for _ in range(SCROLLS):  # results load as the page scrolls
                    page.mouse.wheel(0, 3500)
                    page.wait_for_timeout(int(1200 + 1500 * self._rng()))
                buttons = page.get_by_role('button', name=re.compile(MORE_BUTTON, re.I))
                for index in range(min(buttons.count(), MAX_EXPANDS)):
                    try:
                        buttons.nth(index).click(timeout=1500)  # opens the full text of a cut-off post
                    except Exception:  # noqa: BLE001 - a button that vanished is not a failure
                        pass
                page.wait_for_timeout(800)
            return Page(page.url, status, page.content(), found)
        finally:
            page.close()

    def close(self):
        for name in ('_context', '_browser'):
            try:
                getattr(self, name).close()
            except Exception:  # noqa: BLE001
                pass
        try:
            self._playwright.stop()
        except Exception:  # noqa: BLE001
            pass


class LinkedInFetcher:
    """Search -> posts, over any session object with `get(url) -> Page` and `close()`."""

    def __init__(self, session, *, since_day, recent='past-month'):
        self.session, self.since_day, self.recent = session, since_day, recent
        self.diagnostics = []  # one fixed-shape record per search: no page text, no cookie, no query text

    def _load(self, url, **options):
        """The page, checked for walls. Always leaves one numbers-only record, even when the browser itself fails."""
        record = {'status': 0, 'wall': False, 'path': ''}
        self.diagnostics.append(record)
        try:
            page = self.session.get(url, **options)
        except Exception as exc:  # noqa: BLE001 - keep a fixed word, never the message (it can carry a URL)
            text = str(exc)
            record['error'] = ('redirect_loop' if 'ERR_TOO_MANY_REDIRECTS' in text
                               else 'timeout' if type(exc).__name__ == 'TimeoutError' else 'browser_error')
            if record['error'] == 'redirect_loop':
                raise FetchBlocked from None  # LinkedIn bouncing the session around: the saved login is stale
            raise RuntimeError('browser_error') from None
        path = urlsplit(page.url).path
        record.update({'status': page.status, 'wall': path.startswith(WALL_PATHS), 'ready': page.ready,
                       'path': ('/' + path.split('/')[1])[:30] if path.count('/') else ''})  # first segment only
        if page.status == 429:
            raise FetchRateLimited
        if record['wall'] or page.status in (401, 403, 999):
            raise FetchBlocked  # logged out, restricted or sent to a check
        if page.status != 200:
            raise RuntimeError('unexpected_status')
        return page, record

    def _unreadable(self, cards, stats):
        """Raise when the page is not one we can read, instead of reporting a healthy empty result."""
        if stats['login_form']:
            raise FetchBlocked  # a sign-in form on the results page
        if not cards and not stats['no_results']:
            raise RuntimeError('layout_not_recognised')  # ids seen but unreadable, or nothing recognisable at all
        if cards and stats['short_cards'] == len(cards):
            raise RuntimeError('layout_not_recognised')  # every "card" is a stub: the card boundary was misread

    def search(self, query, limit):
        page, record = self._load(SEARCH_URL.format(keywords=quote(query, safe=''), recent=self.recent))
        record['kind'] = 'posts'
        cards, stats = extract_post_cards(page.html)
        record.update(stats)
        fresh = [card for card in cards if card['created_at'].date().isoformat() >= self.since_day]
        record['outside_window'] = len(cards) - len(fresh)
        self._unreadable(cards, stats)
        return [{'url': card['url'], 'created_at': card['created_at'].isoformat(), 'text': card['text'],
                 'links': card['links'], 'author': card['author']} for card in fresh[:limit]]

    def close(self):
        self.session.close()


def recent_filter(lookback_days):
    """LinkedIn's own date filter nearest above the window; the exact cut-off is applied from the post date."""
    return 'past-24h' if lookback_days <= 1 else 'past-week' if lookback_days <= 7 else 'past-month'


def main(argv=None, *, store=None, fetcher=None, environ=None, now=None, sleep=time.sleep, rng=random.random):
    parser = argparse.ArgumentParser(description='Read-only LinkedIn hiring-post search; writes a candidate file only.')
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
        # A pasted value often carries a trailing newline, spaces or quotes; a clean value is what the browser needs.
        cookie_name = next((name for name in COOKIE_VARIABLES if environ.get(name, '').strip().strip('"\'').strip()), None)
        if cookie_name is None:
            print(f"linkedin_needs_setup: set {COOKIE_VARIABLES[0]} in the environment settings (name only; the value "
                  'is never printed). Nothing was collected and no allowance was spent.')
            return EXIT_NEEDS_SETUP
        if fetcher is None and 'playwright' not in sys.modules and importlib.util.find_spec('playwright') is None:
            print('linkedin_needs_setup: the social extra is not installed (run uv sync --locked --extra social). '
                  'Nothing was collected and no allowance was spent.')
            return EXIT_NEEDS_SETUP
        captured = now()
        if fetcher is None:
            # Start the browser and hand it the cookie BEFORE the allowance is reserved: neither is a LinkedIn request,
            # and a launch failure or a malformed cookie must not use up the day.
            try:
                fetcher = LinkedInFetcher(BrowserSession(environ[cookie_name].strip().strip('"\'').strip(), rng=rng),
                                          since_day=since_date(captured, args.lookback_days),
                                          recent=recent_filter(args.lookback_days))
            except Exception:  # noqa: BLE001 - the message could carry the cookie; keep only a fixed word
                print('linkedin_needs_setup: the browser could not start with that cookie value (check that Chromium is '
                      'installed and that the cookie was pasted without quotes or spaces). Nothing was collected and '
                      'no allowance was spent.')
                return EXIT_NEEDS_SETUP
        try:
            if store is None:
                from jobhunter.google_auth import open_workbook
                from jobhunter.sheet_io import GspreadStore
                store = GspreadStore(open_workbook())
            try:
                day = reserve(store, SOURCE, args.run_id, now=now)
            except AllowanceSpent:
                print('allowance_spent: linkedin-login already used today (America/New_York); collect nothing')
                return EXIT_SPENT
            outcome, items, ran, error, diagnostics = 'failed', [], 0, COLLECTOR_ERROR, []
            try:
                try:
                    items, ran, error = collect_posts(
                        fetcher.search, queries, max_posts=LIMITS[SOURCE]['posts'], per_query=LIMITS[SOURCE]['per_query'],
                        sleep=sleep, rng=rng)
                except Exception:  # noqa: BLE001 - e.g. the browser could not start; keep only a fixed word
                    items, ran, error = [], 0, COLLECTOR_ERROR
                diagnostics = list(getattr(fetcher, 'diagnostics', []))
                artifact = candidate_artifact(SOURCE, items, captured, queries_run=ran, error=error)
                artifact['stats']['searches'] = diagnostics  # fixed-shape numbers only, to tune the reader after a live run
                digest = write_artifact(args.output, artifact)
                outcome = allowance_outcome(items, error)
            finally:
                try:
                    finish(store, SOURCE, args.run_id, outcome, day=day)
                except Exception:  # noqa: BLE001 - the day stays spent either way; say so without hiding the result
                    print('allowance_close_failed: the day stays spent')
            print(f'linkedin_collected: queries_run={ran} posts={len(items)} error={error or "none"} allowance_day={day}')
            for number, record in enumerate(diagnostics, 1):
                print('search_%d: %s' % (number, ' '.join(f'{key}={value}' for key, value in record.items())))
            print(f'linkedin_candidates_sha256={digest}')
            return 0
        finally:
            close = getattr(fetcher, 'close', None)
            if close:
                close()
    except Exception as exc:  # noqa: BLE001
        code = str(exc)
        if code not in SAFE_ERRORS | ALLOWANCE_ERRORS | {'invalid_social_queries', 'invalid_lookback_days'}:
            code = safe_error_code(exc)
        print(f'linkedin_failed: {code}; collect nothing')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
