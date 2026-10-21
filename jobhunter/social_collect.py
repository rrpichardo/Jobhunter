"""Shared pieces of the X and LinkedIn collectors: limits, queries, delays and the candidate artifact.

Nothing here touches a network, a Sheet or a cookie. A collector (scripts/x_collect.py) passes in a fetcher that
does the live reading, so everything below is tested offline. The artifact it produces is what
`scripts.social_posts validate` reads; Claude never sees a cookie and the artifact never contains one.
"""

from datetime import datetime, timedelta
import re

import yaml

from jobhunter.post_facts import clean_social_candidates

# Starting limits from docs/PLAN.md (user-confirmed October 18); tune after the first live run.
LIMITS = {
    'x-twscrape': {'queries': 10, 'posts': 200, 'per_query': 40},  # one busy search cannot starve the other nine
    'linkedin-login': {'job_searches': 5, 'post_searches': 5, 'detail_views': 50, 'posts': 100, 'per_query': 30},
}
DELAY_SECONDS = (3.0, 9.0)  # randomized pause between live requests

# Fixed error words. They are also the only text a failed collection records, so no site message, URL or cookie
# can reach the Sheet.
LOGIN_FAILED = 'social_login_failed'
RATE_LIMITED = 'social_rate_limited'
COLLECTOR_ERROR = 'social_collector_error'

QUERY = re.compile(r'[A-Za-z0-9 "\'.,:()&/+#@-]{3,200}')


class FetchBlocked(Exception):
    """The site refused the saved session (logged out, restricted or checkpointed). `found` holds any posts read
    from this search before the refusal."""

    def __init__(self, found=()):
        super().__init__()
        self.found = list(found)


class FetchRateLimited(Exception):
    """The site asked us to slow down. `found` holds any posts read from this search before it did."""

    def __init__(self, found=()):
        super().__init__()
        self.found = list(found)


def load_queries(path, source_id):
    """The query list for one source from a YAML file, checked and cut to the source's query limit."""
    data = yaml.safe_load(open(path, encoding='utf-8').read())
    queries = data.get(source_id) if isinstance(data, dict) else None
    limit = LIMITS[source_id].get('queries', LIMITS[source_id].get('post_searches'))
    if (not isinstance(queries, list) or not queries
            or any(not isinstance(q, str) or not QUERY.fullmatch(q) for q in queries)):
        raise ValueError('invalid_social_queries')
    return list(dict.fromkeys(queries))[:limit]


def since_date(captured_at, lookback_days):
    """YYYY-MM-DD of the first day inside the look-back window (UTC)."""
    return (datetime.fromisoformat(captured_at) - timedelta(days=lookback_days)).date().isoformat()


def build_query(base, since):
    # X search syntax: only posts since the date, and no replies (they are rarely the job post itself).
    return f'{base} since:{since} -filter:replies'


def pause(rng, low=DELAY_SECONDS[0], high=DELAY_SECONDS[1]):
    return low + (high - low) * rng()


def collect_posts(search, queries, *, max_posts, sleep, rng, per_query=None):
    """(items, queries_run, error word). `search(query, limit)` returns dicts with url, created_at, text, links.

    Stops at max_posts or the first failure; what was read before a failure is kept. `per_query` caps one search. A failure records only a
    fixed word, never the exception text.
    """
    items, seen, ran, error = [], set(), 0, ''
    for query in queries:
        remaining = max_posts - len(items)
        if remaining <= 0:
            break
        if per_query:
            remaining = min(remaining, per_query)
        if ran:
            sleep(pause(rng))
        failure = ''
        try:
            found = search(query, remaining)
        except (FetchBlocked, FetchRateLimited) as exc:
            found = exc.found  # what was read before the refusal is kept
            failure = LOGIN_FAILED if isinstance(exc, FetchBlocked) else RATE_LIMITED
        except Exception as exc:  # noqa: BLE001 - the message could carry a URL or token; keep only a fixed word
            found, failure = getattr(exc, 'found', []), COLLECTOR_ERROR
        ran += 0 if failure else 1
        for item in found:
            url = item.get('url') if isinstance(item, dict) else None
            if url in seen or len(items) >= max_posts:
                continue
            seen.add(url)
            items.append(item)
        if failure:
            error = failure
            break
    return items, ran, error


def candidate_artifact(source_id, items, captured_at, *, queries_run, error=''):
    """The file `scripts.social_posts validate` and `scripts.ai_queue pull` read.

    Posts are cleaned by the same code that validates them later: canonical post URL on the site's own host, a
    code-made item id, a real date, text within the size limit. Anything that fails is counted, not kept.
    """
    cleaned, unreadable = clean_social_candidates(source_id, items)
    return {'schema_version': 1, 'source_id': source_id, 'captured_at': captured_at, 'error': error,
            'stats': {'unreadable': unreadable, 'queries_run': queries_run, 'posts_fetched': len(items)},
            'candidates': cleaned}


def allowance_outcome(items, error):
    """The word `scripts.allowance finish` records for this attempt."""
    if error in (LOGIN_FAILED, RATE_LIMITED):
        return 'blocked'
    if error:
        return 'failed'
    return 'ok' if items else 'zero'
