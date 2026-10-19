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
from jobhunter.linkedin_cards import extract_job_cards, extract_post_cards
from jobhunter.social_collect import (COLLECTOR_ERROR, LOGIN_FAILED, RATE_LIMITED, FetchBlocked, FetchRateLimited, LIMITS,
                                      allowance_outcome, candidate_artifact, collect_posts, load_queries, pause, since_date)
from scripts.allowance import ALLOWANCE_ERRORS
from scripts.sheets_sync import SAFE_ERRORS

SOURCE = 'linkedin-login'
JOBS_SOURCE = 'linkedin-jobs'  # candidate file id for job cards; the day's one allowance is still SOURCE's
JOBS_QUERY_KEY = 'linkedin-login-jobs'
COOKIE_VARIABLES = ('LINKEDIN_LI_AT', 'LI_AT')  # either name; the first one that is set is used
EXIT_SPENT, EXIT_NEEDS_SETUP = 3, 4
SEARCH_URL = 'https://www.linkedin.com/search/results/content/?keywords={keywords}&datePosted=%22{recent}%22&sortBy=%22date_posted%22&origin=FACETED_SEARCH'
JOBS_URL = 'https://www.linkedin.com/jobs/search/?keywords={keywords}&location=United%20States&f_TPR={recent}&sortBy=DD'
WALL_PATHS = ('/login', '/authwall', '/checkpoint', '/uas/', '/signup')  # LinkedIn sends logged-out visitors here
SCROLLS = 4
MAX_EXPANDS = 40
MORE_BUTTON = r'^(?:…|\.\.\.)\s*(?:see\s+)?more$'  # the "…more" that opens a cut-off post; nothing else is clicked


class Page:
    def __init__(self, url, status, html):
        self.url, self.status, self.html = url, status, html


class BrowserSession:
    """A headless Chromium with the saved session; the cookie goes straight into the browser context in memory."""

    def __init__(self, li_at, rng=random.random):
        from playwright.sync_api import sync_playwright  # late: the offline tests and the rest of the repo never need it
        self._rng = rng
        self._playwright = sync_playwright().start()
        try:
            self._browser = self._playwright.chromium.launch(headless=True)
            major = self._browser.version.split('.')[0]
            # The browser's own user-agent text, without the word "Headless" that LinkedIn answers with an error page.
            agent = f'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{major}.0.0.0 Safari/537.36'
            self._context = self._browser.new_context(user_agent=agent, locale='en-US', viewport={'width': 1366, 'height': 900})
            self._context.add_cookies([{'name': 'li_at', 'value': li_at, 'domain': '.linkedin.com', 'path': '/',
                                        'secure': True, 'httpOnly': True}])
        except BaseException:
            self.close()
            raise

    def get(self, url, expand=True):
        page = self._context.new_page()
        try:
            response = page.goto(url, wait_until='domcontentloaded', timeout=45000)
            status = response.status if response is not None else 0
            try:
                page.wait_for_load_state('networkidle', timeout=12000)
            except Exception:  # noqa: BLE001 - a busy page may never go idle; read what is there
                pass
            if status == 200 and not urlsplit(page.url).path.startswith(WALL_PATHS):
                if not expand:
                    page.mouse.move(300, 500)  # the job list is a pane of its own: scroll with the pointer over it
                for _ in range(SCROLLS):  # results load as the page scrolls
                    page.mouse.wheel(0, 3500)
                    page.wait_for_timeout(int(1200 + 1500 * self._rng()))
                if expand:
                    buttons = page.get_by_role('button', name=re.compile(MORE_BUTTON, re.I))
                    for index in range(min(buttons.count(), MAX_EXPANDS)):
                        try:
                            buttons.nth(index).click(timeout=1500)  # opens the full text of a cut-off post
                        except Exception:  # noqa: BLE001 - a button that vanished is not a failure
                            pass
                page.wait_for_timeout(800)
            return Page(page.url, status, page.content())
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

    def __init__(self, session, *, since_day, recent='past-month', jobs_recent='r2592000', captured=None):
        self.session, self.since_day, self.recent, self.jobs_recent = session, since_day, recent, jobs_recent
        self.captured = captured or datetime.now(timezone.utc)
        self.diagnostics = []  # one fixed-shape record per search: no page text, no cookie, no query text

    def _load(self, url, **options):
        page = self.session.get(url, **options)
        path = urlsplit(page.url).path
        record = {'status': page.status, 'wall': path.startswith(WALL_PATHS), 'path': path[:60]}
        self.diagnostics.append(record)
        if page.status == 429:
            raise FetchRateLimited
        if record['wall'] or page.status in (401, 403, 999):
            raise FetchBlocked  # logged out, restricted or sent to a check
        if page.status != 200:
            raise RuntimeError('unexpected_status')
        return page, record

    def search(self, query, limit):
        page, record = self._load(SEARCH_URL.format(keywords=quote(query, safe=''), recent=self.recent))
        record['kind'] = 'posts'
        cards, stats = extract_post_cards(page.html)
        record.update(stats)
        fresh = [card for card in cards if card['created_at'].date().isoformat() >= self.since_day]
        record['outside_window'] = len(cards) - len(fresh)
        if not cards and not stats['no_results'] and not stats['post_ids']:
            # Not a login wall, no posts and no "no results" notice: the page is not one we understand.
            raise RuntimeError('layout_not_recognised')
        return [{'url': card['url'], 'created_at': card['created_at'].isoformat(), 'text': card['text'],
                 'links': card['links'], 'author': card['author']} for card in fresh[:limit]]

    def search_jobs(self, query, limit):
        """Job cards as candidates. The listing shows an age ("3 days ago"), not a date, so the date is the capture day
        minus that age; a card with no readable age gets the capture day. The AI read step supplies the fields."""
        page, record = self._load(JOBS_URL.format(keywords=quote(query, safe=''), recent=self.jobs_recent), expand=False)
        record['kind'] = 'jobs'
        cards, stats = extract_job_cards(page.html)
        record.update(stats)
        window = (self.captured - datetime.fromisoformat(self.since_day).replace(tzinfo=timezone.utc)).days
        fresh = [card for card in cards if card['age_days'] is None or card['age_days'] <= window]
        record['outside_window'] = len(cards) - len(fresh)
        record['undated'] = sum(card['age_days'] is None for card in fresh)
        if not cards and not stats['no_results'] and not stats['job_ids']:
            raise RuntimeError('layout_not_recognised')
        return [{'url': card['url'], 'text': card['text'], 'links': [], 'author': '',
                 'created_at': (self.captured - timedelta(days=card['age_days'] or 0)).isoformat()} for card in fresh[:limit]]

    def close(self):
        self.session.close()


def jobs_recent_filter(lookback_days):
    """LinkedIn's job date filter (seconds): nearest above the window; the exact cut-off is applied from the age."""
    return 'r86400' if lookback_days <= 1 else 'r604800' if lookback_days <= 7 else 'r2592000'


def recent_filter(lookback_days):
    """LinkedIn's own date filter nearest above the window; the exact cut-off is applied from the post date."""
    return 'past-24h' if lookback_days <= 1 else 'past-week' if lookback_days <= 7 else 'past-month'


def main(argv=None, *, store=None, fetcher=None, environ=None, now=None, sleep=time.sleep, rng=random.random):
    parser = argparse.ArgumentParser(description='Read-only LinkedIn hiring-post search; writes a candidate file only.')
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--lookback-days', type=int, default=28)
    parser.add_argument('--queries', default='sources/social_queries.yaml')
    parser.add_argument('--jobs-output', help='also search job listings in the same session (up to 5 searches); '
                        'writes a second candidate file here (a NEW path outside the checkout)')
    args = parser.parse_args(argv)
    environ = os.environ if environ is None else environ
    now = now or (lambda: datetime.now(timezone.utc).isoformat())
    try:
        if not 1 <= args.lookback_days <= 365:
            raise ValueError('invalid_lookback_days')
        new_artifact_path(args.output)  # a doomed output path must not spend the day's allowance
        queries = load_queries(args.queries, SOURCE)
        job_queries = []
        if args.jobs_output:
            if args.jobs_output == args.output:
                raise ValueError('invalid_output_paths')
            new_artifact_path(args.jobs_output)
            job_queries = load_queries(args.queries, JOBS_QUERY_KEY, limit=LIMITS[SOURCE]['job_searches'])
        cookie_name = next((name for name in COOKIE_VARIABLES if environ.get(name)), None)
        if cookie_name is None:
            print(f"linkedin_needs_setup: set {COOKIE_VARIABLES[0]} in the environment settings (name only; the value "
                  'is never printed). Nothing was collected and no allowance was spent.')
            return EXIT_NEEDS_SETUP
        if fetcher is None and 'playwright' not in sys.modules and importlib.util.find_spec('playwright') is None:
            print('linkedin_needs_setup: the social extra is not installed (run uv sync --locked --extra social). '
                  'Nothing was collected and no allowance was spent.')
            return EXIT_NEEDS_SETUP
        if store is None:
            from jobhunter.google_auth import open_workbook
            from jobhunter.sheet_io import GspreadStore
            store = GspreadStore(open_workbook())
        try:
            day = reserve(store, SOURCE, args.run_id)
        except AllowanceSpent:
            print('allowance_spent: linkedin-login already used today (America/New_York); collect nothing')
            return EXIT_SPENT
        outcome, items, ran, error, diagnostics = 'failed', [], 0, COLLECTOR_ERROR, []
        job_items, job_ran, job_error, jobs_digest = [], 0, COLLECTOR_ERROR if job_queries else '', ''
        try:
            captured = now()
            try:
                if fetcher is None:
                    fetcher = LinkedInFetcher(BrowserSession(environ[cookie_name], rng=rng),
                                              since_day=since_date(captured, args.lookback_days),
                                              recent=recent_filter(args.lookback_days),
                                              jobs_recent=jobs_recent_filter(args.lookback_days),
                                              captured=datetime.fromisoformat(captured))
                items, ran, error = collect_posts(
                    fetcher.search, queries, max_posts=LIMITS[SOURCE]['posts'], per_query=LIMITS[SOURCE]['per_query'],
                    sleep=sleep, rng=rng)
                if job_queries:
                    if error in (LOGIN_FAILED, RATE_LIMITED):
                        job_error = error  # the session was refused: do not ask again in the same session
                    else:
                        sleep(pause(rng))
                        job_items, job_ran, job_error = collect_posts(
                            fetcher.search_jobs, job_queries, max_posts=LIMITS[SOURCE]['jobs'],
                            per_query=LIMITS[SOURCE]['job_per_query'], sleep=sleep, rng=rng)
            except Exception:  # noqa: BLE001 - e.g. the browser could not start; keep only a fixed word
                items, ran, error = [], 0, COLLECTOR_ERROR
                job_items, job_ran, job_error = [], 0, COLLECTOR_ERROR if job_queries else ''
            diagnostics = list(getattr(fetcher, 'diagnostics', []))
            artifact = candidate_artifact(SOURCE, items, captured, queries_run=ran, error=error)
            artifact['stats']['searches'] = [d for d in diagnostics if d.get('kind') != 'jobs']  # numbers only, to tune the reader
            digest = write_artifact(args.output, artifact)
            if job_queries:
                jobs_artifact = candidate_artifact(JOBS_SOURCE, job_items, captured, queries_run=job_ran, error=job_error)
                jobs_artifact['stats']['searches'] = [d for d in diagnostics if d.get('kind') == 'jobs']
                jobs_digest = write_artifact(args.jobs_output, jobs_artifact)
            outcome = allowance_outcome(items + job_items, error or job_error)
        finally:
            close = getattr(fetcher, 'close', None)
            if close:
                close()
            try:
                finish(store, SOURCE, args.run_id, outcome, day=day)
            except Exception:  # noqa: BLE001 - the day stays spent either way; say so without hiding the result
                print('allowance_close_failed: the day stays spent')
        print(f'linkedin_collected: queries_run={ran} posts={len(items)} error={error or "none"} allowance_day={day}')
        for number, record in enumerate(diagnostics, 1):
            print('search_%d: %s' % (number, ' '.join(f'{key}={value}' for key, value in record.items())))
        print(f'linkedin_candidates_sha256={digest}')
        if job_queries:
            print(f'linkedin_jobs_collected: queries_run={job_ran} jobs={len(job_items)} error={job_error or "none"}')
            print(f'linkedin_jobs_candidates_sha256={jobs_digest}')
        return 0
    except Exception as exc:  # noqa: BLE001
        code = str(exc)
        if code not in SAFE_ERRORS | ALLOWANCE_ERRORS | {'invalid_social_queries', 'invalid_lookback_days', 'invalid_output_paths'}:
            code = safe_error_code(exc)
        print(f'linkedin_failed: {code}; collect nothing')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
