"""Hacker News "Who is hiring?" comments: deterministic fetch and filter, AI-extracted facts, code-owned rows.

Phase 1 (code) selects the monthly threads, reads every top-level comment inside the lookback window
through the Algolia items endpoint (the search endpoint caps results at about 1000) and keeps comments
that mention a collected role family. Phase 2 (the Claude routine) proposes facts for each kept comment.
Phase 3 (code) accepts a fact only when each value appears verbatim in that comment, derives the Job ID
and posting date itself, and falls back to the comment permalink as the application link, which makes
the row a lead. Comment text is untrusted data, never instructions.
"""

from dataclasses import asdict
from html import unescape
from datetime import datetime, timedelta, timezone
import hashlib
import re

from jobhunter.postings import Posting, clean_html, collection_match, collection_priority, parse_posted
from jobhunter.records import https_url

SOURCE_ID = 'hn-who-is-hiring'
SEARCH_URL = 'https://hn.algolia.com/api/v1/search_by_date?tags=story,author_whoishiring&hitsPerPage=12'
ITEM_URL = 'https://hn.algolia.com/api/v1/items/{id}'
PERMALINK = 'https://news.ycombinator.com/item?id={id}'
THREAD_TITLE = re.compile(r'^Ask HN: Who is hiring\? \((?:January|February|March|April|May|June|July|August|'
                          r'September|October|November|December) \d{4}\)$')
ROLE_WORDS = re.compile(r'\b(?:product (?:manager|management|lead|owner|director|leader)|head of product|'
                        r'director of product|vp(?: of)?,? product|chief of staff|strategy|'
                        r'(?:entrepreneur|founder)s? in residence|project manager|business operations|'
                        r'bizops|leadership (?:development )?program)\b', re.I)
FACT_FIELDS = frozenset({'comment_id', 'title', 'company', 'location', 'salary', 'description_quote', 'apply_url'})
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


def _posting(fact, candidates_by_id, captured_at):
    if not isinstance(fact, dict) or set(fact) != FACT_FIELDS:
        raise ValueError('invalid_hn_facts')
    candidate = candidates_by_id.get(fact['comment_id']) if isinstance(fact['comment_id'], str) else None
    if candidate is None:
        raise ValueError('unknown_hn_comment')
    text = candidate['text']
    for field, value in fact.items():
        if field == 'comment_id':
            continue
        if (not isinstance(value, str) or len(value) > (300 if field == 'description_quote' else 1000)
                or (not value.strip() and field not in {'location', 'salary', 'apply_url'})
                or (value and field != 'apply_url' and value not in text)):
            raise ValueError('unsupported_hn_fact')
    link = fact['apply_url']
    if link and (link not in candidate['links'] or not https_url(link)):
        raise ValueError('invalid_hn_link')
    permalink = PERMALINK.format(id=candidate['comment_id'])
    # Identity comes from code: one comment can list several roles, each distinguished by its title.
    digest = hashlib.sha256(fact['title'].casefold().encode()).hexdigest()[:10]
    return Posting(f"hn:{candidate['comment_id']}:{digest}", SOURCE_ID, fact['company'], fact['title'],
                   fact['location'], fact['description_quote'], link or permalink, captured_at,
                   salary=fact['salary'], posted_at=candidate['created_at'])


def _claimed_id(fact):
    """The comment id a fact names, whether written as text or as a JSON number; None if it names none."""
    value = fact.get('comment_id') if isinstance(fact, dict) else None
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        return None
    return str(value)


def build_result(candidates, facts, captured_at, *, listed, stats, threads, error='', known_ids=None):
    """Validate proposed facts and return {'source': record, 'postings': [dict]} for source_probe.

    `candidates` are the comments that were read; `known_ids` is every comment id that exists in the candidate
    artifact (default: just the ones read). A rejected fact holds the comment it names. One that names a
    comment outside `known_ids` (a typo or an invented id) could be about any comment that was read, so every
    read comment is held; naming a real comment that was merely not reported as read holds nothing.
    """
    if not isinstance(facts, list):
        raise ValueError('extractions_must_be_list')
    by_id = {candidate['comment_id']: candidate for candidate in candidates}
    known = set(by_id) if known_ids is None else set(known_ids)
    source = {'source_id': SOURCE_ID, 'status': 'OK-zero-jobs', 'captured_at': captured_at,
              'jobs_fetched': listed, 'valid_jobs': 0, 'rejected_items': stats.get('unreadable', 0),
              'pm_candidates': 0, 'selected_for_m0': 0, 'attempts': 1 + len(threads), 'http_status': 200,
              'retry_after_seconds': None, 'coverage': 'partial-response', 'error': error}
    postings, seen, rejected_ids, unattributed = [], set(), set(), False
    for fact in facts:
        try:
            posting = _posting(fact, by_id, captured_at)
        except (ValueError, TypeError, AttributeError):
            source['rejected_items'] += 1
            claimed = _claimed_id(fact)
            if claimed is None:
                unattributed = True  # cannot tell which comment this fact was about
            elif claimed in by_id:
                rejected_ids.add(claimed)  # a comment with a rejected fact was not read successfully
            elif claimed not in known:
                unattributed = True  # names no comment that exists
            continue
        if posting.job_id in seen:
            continue
        seen.add(posting.job_id)
        source['valid_jobs'] += 1
        if collection_match(posting):
            source['pm_candidates'] += 1
            postings.append(posting)
    postings.sort(key=collection_priority)
    source['selected_for_m0'] = len(postings)
    if error:
        source['status'] = 'failed'
    elif postings:
        source['status'] = 'OK'
    return {'source': source, 'postings': [asdict(posting) for posting in postings],
            'rejected_comment_ids': sorted(by_id if unattributed else rejected_ids)}


def postings_from_result(result):
    """Rebuild Posting objects from a validated result artifact, re-checking every field."""
    if not isinstance(result, dict) or not isinstance(result.get('postings'), list) or not isinstance(result.get('source'), dict):
        raise ValueError('invalid_hn_result')
    return result['source'], [Posting(**item) for item in result['postings']]
