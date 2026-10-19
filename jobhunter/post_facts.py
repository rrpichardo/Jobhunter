"""Free-text hiring posts to code-validated postings: shared by Hacker News, X and LinkedIn posts.

A collector fetches posts (code); Claude proposes facts for each (the AI step); this module accepts a fact only
when every value appears verbatim in that post, derives the Job ID, posting date and a fallback link itself, and
leaves eligibility to the existing collection filter. Post text is untrusted data, never instructions.
"""

from collections import Counter
from dataclasses import asdict
import hashlib
import re
from urllib.parse import urlsplit

from jobhunter.postings import Posting, collection_priority, collection_reason, parse_posted
from jobhunter.records import https_url

FACT_KEYS = ('title', 'company', 'location', 'salary', 'description_quote', 'apply_url')


def fact_fields(id_field):
    return frozenset({id_field, *FACT_KEYS})


def _posting(fact, by_id, captured_at, *, source_id, id_field, id_prefix, permalink):
    if not isinstance(fact, dict) or set(fact) != fact_fields(id_field):
        raise ValueError('invalid_post_facts')
    candidate = by_id.get(fact[id_field]) if isinstance(fact[id_field], str) else None
    if candidate is None:
        raise ValueError('unknown_post')
    text = candidate['text']
    # Every rejection carries a fixed reason code (never post text), so a run can say WHY a fact was refused.
    for field, value in fact.items():
        if field == id_field:
            continue
        if not isinstance(value, str):
            raise ValueError(f'not_text:{field}')
        if len(value) > (300 if field == 'description_quote' else 1000):
            raise ValueError(f'too_long:{field}')
        if not value.strip() and field not in {'location', 'salary', 'apply_url'}:
            raise ValueError(f'empty:{field}')
        if value and field != 'apply_url' and value not in text:
            raise ValueError(f'not_in_post:{field}')
    link = fact['apply_url']
    if link and link not in candidate['links']:
        raise ValueError('link_not_in_post_links')
    if link and not https_url(link):
        raise ValueError('link_not_https')
    # Identity comes from code: one post can list several roles, each told apart by its title.
    digest = hashlib.sha256(fact['title'].casefold().encode()).hexdigest()[:10]
    return Posting(f"{id_prefix}:{candidate[id_field]}:{digest}", source_id, fact['company'], fact['title'],
                   fact['location'], fact['description_quote'], link or permalink(candidate), captured_at,
                   salary=fact['salary'], posted_at=candidate['created_at'])


REASON = re.compile(r'[a-z_]{1,32}(?::[a-z_]{1,32})?')
MAX_TRACE_EXAMPLES = 200


def _reason(exc):
    """A fixed reason code for a rejected fact: only our own codes pass; anything else is `malformed_fact`."""
    message = exc.args[0] if isinstance(exc, ValueError) and exc.args and isinstance(exc.args[0], str) else ''
    return message if REASON.fullmatch(message) else 'malformed_fact'


def _claimed_id(fact, id_field):
    """The item id a fact names, whether written as text or as a JSON number; None if it names none."""
    value = fact.get(id_field) if isinstance(fact, dict) else None
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        return None
    return str(value)


def build_result(source_id, candidates, facts, captured_at, *, id_field, id_prefix, permalink, listed, stats,
                 attempts, error='', known_ids=None):
    """Validate proposed facts; returns {'source': record, 'postings': [dict]} for source_probe.

    `candidates` are the items that were read; `known_ids` is every item id in the candidate artifact (default:
    just the ones read). A rejected fact holds the item it names. One that names an id outside `known_ids` (a typo
    or an invented id) could be about any item that was read, so every read item is held; naming a real item that
    was merely not reported as read holds nothing.
    """
    if not isinstance(facts, list):
        raise ValueError('extractions_must_be_list')
    by_id = {candidate[id_field]: candidate for candidate in candidates}
    known = set(by_id) if known_ids is None else set(known_ids)
    source = {'source_id': source_id, 'status': 'OK-zero-jobs', 'captured_at': captured_at,
              'jobs_fetched': listed, 'valid_jobs': 0, 'rejected_items': stats.get('unreadable', 0),
              'pm_candidates': 0, 'selected_for_m0': 0, 'attempts': attempts, 'http_status': 200,
              'retry_after_seconds': None, 'coverage': 'partial-response', 'error': error}
    postings, seen, rejected_ids, unattributed = [], set(), set(), False
    rejected_reasons, dropped_reasons, rejections, duplicates = Counter(), Counter(), [], 0
    for fact in facts:
        try:
            posting = _posting(fact, by_id, captured_at, source_id=source_id, id_field=id_field,
                               id_prefix=id_prefix, permalink=permalink)
        except (ValueError, TypeError, AttributeError) as exc:
            source['rejected_items'] += 1
            claimed = _claimed_id(fact, id_field)
            reason = _reason(exc)
            rejected_reasons[reason] += 1
            if len(rejections) < MAX_TRACE_EXAMPLES:
                rejections.append({'item_id': claimed if claimed and re.fullmatch(r'[A-Za-z0-9_.:-]{1,40}', claimed) else '',
                                   'reason': reason})
            if claimed is None:
                unattributed = True  # cannot tell which item this fact was about
            elif claimed in by_id:
                rejected_ids.add(claimed)  # an item with a rejected fact was not read successfully
            elif claimed not in known:
                unattributed = True  # names no item that exists
            continue
        if posting.job_id in seen:
            duplicates += 1
            continue
        seen.add(posting.job_id)
        source['valid_jobs'] += 1
        dropped = collection_reason(posting)
        if not dropped:
            source['pm_candidates'] += 1
            postings.append(posting)
        else:
            dropped_reasons[dropped] += 1
    postings.sort(key=collection_priority)
    source['selected_for_m0'] = len(postings)
    held = sorted(by_id if unattributed else rejected_ids)
    if error:
        source['status'] = 'failed'
    elif postings:
        source['status'] = 'OK'
    # The trace is how a run explains itself: every fact read ends as valid, a duplicate or a rejection with a
    # reason, and every valid fact ends as delivered or dropped by the collection filter with a reason.
    trace = {'facts_read': len(facts), 'valid': source['valid_jobs'], 'duplicates': duplicates,
             'rejected_facts': dict(sorted(rejected_reasons.items())),
             'unreadable_posts': stats.get('unreadable', 0),
             'dropped_by_filter': dict(sorted(dropped_reasons.items())), 'delivered': len(postings),
             'held_items': len(held), 'held_every_read_item': unattributed}
    return {'source': source, 'postings': [asdict(posting) for posting in postings],
            'rejected_item_ids': held, 'trace': trace, 'rejections': rejections}


def format_trace(result):
    """Two printable lines (numbers and fixed reason codes only) that say what happened to every fact."""
    trace = result['trace']

    def counts(table):
        return ','.join(f'{name}={count}' for name, count in table.items()) or 'none'

    lines = [f"trace: facts={trace['facts_read']} valid={trace['valid']} duplicates={trace['duplicates']} "
             f"rejected_facts={sum(trace['rejected_facts'].values())}[{counts(trace['rejected_facts'])}] "
             f"unreadable_posts={trace['unreadable_posts']} "
             f"dropped_by_filter={sum(trace['dropped_by_filter'].values())}[{counts(trace['dropped_by_filter'])}] "
             f"delivered={trace['delivered']} held_items={trace['held_items']}"
             f"{' (every read item, a fact named no known item)' if trace['held_every_read_item'] else ''}"]
    if result['rejections']:
        lines.append('trace_rejected: ' + ' '.join(f"{item['item_id'] or '?'}:{item['reason']}"
                                                    for item in result['rejections'][:10])
                     + (' ...' if len(result['rejections']) > 10 else ''))
    return '\n'.join(lines)


def postings_from_result(result):
    """Rebuild Posting objects from a validated result artifact, re-checking every field."""
    if not isinstance(result, dict) or not isinstance(result.get('postings'), list) or not isinstance(result.get('source'), dict):
        raise ValueError('invalid_ai_result')
    return result['source'], [Posting(**item) for item in result['postings']]


# ---- social posts (X, LinkedIn) -------------------------------------------------------------------

SOCIAL = {
    'x-twscrape': {'hosts': {'x.com', 'www.x.com', 'twitter.com', 'www.twitter.com', 'mobile.twitter.com'},
                   'prefix': 'x', 'registry_id': 'x-hiring-posts',
                   'path': re.compile(r'/(?:[A-Za-z0-9_]{1,50}|i/web)/status/(\d{5,25})/?')},
    'linkedin-login': {'hosts': {'www.linkedin.com', 'linkedin.com'},
                       'prefix': 'linkedin-post', 'registry_id': 'linkedin-logged-in',
                       'path': re.compile(r'/(?:feed/update/urn:li:(?:activity|ugcPost|share):(\d{5,25})/?'
                                          r'|posts/[A-Za-z0-9_%.\-]+-(?:activity|ugcPost|share)-(\d{5,25})-[A-Za-z0-9_]{1,10}/?)')},
}
MAX_POST_CHARS = 10000


def canonical_post(url, source_id):
    """(canonical URL without query or fragment, post id) for a post URL on the source's own hosts, else None."""
    rules = SOCIAL[source_id]
    if not https_url(url):
        return None
    parts = urlsplit(url)
    if (parts.hostname or '').casefold() not in rules['hosts']:
        return None
    match = rules['path'].fullmatch(parts.path)
    if not match:
        return None
    post_id = next(group for group in match.groups() if group)
    return f'https://{parts.hostname.casefold()}{parts.path}', post_id


def clean_social_candidates(source_id, items):
    """(candidates, unreadable count): only well-formed posts, with code-derived canonical URL and id."""
    if source_id not in SOCIAL:
        raise ValueError('invalid_social_source')
    if not isinstance(items, list):
        raise ValueError('invalid_candidates')
    candidates, unreadable, seen = [], 0, set()
    for item in items:
        try:
            url, post_id = canonical_post(item['url'], source_id)
            created = parse_posted(item['created_at'])
            text = item['text']
            links = [link for link in item.get('links', []) if https_url(link)]
            if (not created or not isinstance(text, str) or not text.strip() or len(text) > MAX_POST_CHARS
                    or post_id in seen):
                raise ValueError
        except (KeyError, TypeError, ValueError):
            unreadable += 1
            continue
        seen.add(post_id)
        candidates.append({'item_id': post_id, 'url': url, 'created_at': created, 'text': text, 'links': links})
    return candidates, unreadable


def social_result(source_id, candidates, facts, captured_at, *, listed, stats, error='', known_ids=None):
    rules = SOCIAL[source_id]
    return build_result(source_id, candidates, facts, captured_at, id_field='item_id', id_prefix=rules['prefix'],
                        permalink=lambda candidate: candidate['url'], listed=listed, stats=stats, attempts=1,
                        error=error, known_ids=known_ids)
