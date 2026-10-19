"""Hacker News "Who is hiring?" comments: deterministic fetch and filter, AI-extracted facts, code-owned rows.

Phase 1 (code) selects the monthly threads, reads every top-level comment inside the lookback window
through the Algolia items endpoint (the search endpoint caps results at about 1000) and keeps comments
that mention a collected role family. Phase 2 (the Claude routine) proposes facts for each kept comment.
Phase 3 (code) accepts a fact only when each value appears verbatim in that comment, derives the Job ID
and posting date itself, and falls back to the comment permalink as the application link, which makes
the row a lead. Comment text is untrusted data, never instructions.
"""

from html import unescape
from datetime import datetime, timedelta, timezone
import re

from jobhunter import post_facts
from jobhunter.postings import ROLE_TEXT, clean_html, parse_posted
from jobhunter.records import https_url

SOURCE_ID = 'hn-who-is-hiring'
SEARCH_URL = 'https://hn.algolia.com/api/v1/search_by_date?tags=story,author_whoishiring&hitsPerPage=12'
ITEM_URL = 'https://hn.algolia.com/api/v1/items/{id}'
PERMALINK = 'https://news.ycombinator.com/item?id={id}'
THREAD_TITLE = re.compile(r'^Ask HN: Who is hiring\? \((?:January|February|March|April|May|June|July|August|'
                          r'September|October|November|December) \d{4}\)$')
ROLE_WORDS = ROLE_TEXT  # the delivery filter's own role families, so nothing is sent to Claude that cannot be delivered
MAX_COMMENT_CHARS = 20000
# Safety stop on candidate comments handed to the AI in one run (a thread has a few hundred; two are read).
CANDIDATE_SAFETY_STOP = 1500


def select_threads(search, now, lookback_days):
    """Monthly 'Who is hiring?' threads that can hold comments inside the window, newest first."""
    hits = search.get('hits') if isinstance(search, dict) else None
    if not isinstance(hits, list):
        raise ValueError('invalid_board_response')
    oldest = now - timedelta(days=lookback_days + 32)  # a thread stays active for roughly a month
    threads = []
    for hit in hits:
        if not isinstance(hit, dict) or not isinstance(hit.get('title'), str) or not THREAD_TITLE.match(hit['title']):
            continue
        created = parse_posted(hit.get('created_at_i'))
        story = str(hit.get('objectID') or '')
        if created and story.isdigit() and datetime.fromisoformat(created) >= oldest:
            threads.append({'story_id': story, 'title': hit['title'], 'created_at': created})
    return sorted(threads, key=lambda thread: thread['created_at'], reverse=True)


def candidate_comments(thread, item, cutoff):
    """(candidates, stats) from one items-endpoint response; top-level comments only."""
    children = item.get('children') if isinstance(item, dict) else None
    if not isinstance(children, list) or str(item.get('id')) != thread['story_id']:
        raise ValueError('invalid_board_response')
    candidates, stats = [], {'top_level': 0, 'in_window': 0, 'role_mentions': 0, 'unreadable': 0}
    for child in children:
        stats['top_level'] += 1
        if not isinstance(child, dict) or not str(child.get('id', '')).isdigit():
            stats['unreadable'] += 1
            continue
        created = parse_posted(child.get('created_at_i'))
        text = clean_html(child.get('text')) if isinstance(child.get('text'), str) else ''
        if not created or not text or len(text) > MAX_COMMENT_CHARS:
            stats['unreadable'] += 1  # deleted, dead, empty or oversized: counted, not guessed at
            continue
        if datetime.fromisoformat(created) < cutoff:
            continue
        stats['in_window'] += 1
        if not ROLE_WORDS.search(text):
            continue
        stats['role_mentions'] += 1
        links = sorted({a for a in re.findall(r'href="(https://[^"]+)"', unescape(child['text'])) if https_url(a)})
        candidates.append({'comment_id': str(child['id']), 'story_id': thread['story_id'], 'created_at': created,
                           'text': text, 'links': links})
    return candidates, stats


def build_result(candidates, facts, captured_at, *, listed, stats, threads, error='', known_ids=None):
    """Validate proposed facts and return {'source': record, 'postings': [dict]} for source_probe."""
    return post_facts.build_result(SOURCE_ID, candidates, facts, captured_at, id_field='comment_id', id_prefix='hn',
                                   permalink=lambda candidate: PERMALINK.format(id=candidate['comment_id']),
                                   listed=listed, stats=stats, attempts=1 + len(threads), error=error,
                                   known_ids=known_ids)


postings_from_result = post_facts.postings_from_result
