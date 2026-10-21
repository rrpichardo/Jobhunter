"""The trace must not change which facts are accepted or which postings are collected.

Each test keeps a copy of the rule as it was before reason codes existed and compares it with the current code over a
grid of inputs, so a later edit that quietly loosens or tightens either rule fails here.
"""

import itertools

import pytest

from jobhunter import post_facts as pf
from jobhunter.postings import Posting, collection_match, collection_reason, collection_region, role_family, salary_preference
from jobhunter.records import https_url

TEXT = 'Acme is hiring a Senior Product Manager, AI (Remote US), open to MBA students graduating in spring 2027. $170k-$210k. Apply: https://acme.example/jobs/pm'
CANDIDATE = {'item_id': '1', 'url': 'https://x.com/a/status/1', 'created_at': '2026-10-15T12:00:00+00:00', 'text': TEXT,
             'links': ['https://acme.example/jobs/pm']}
GOOD = {'item_id': '1', 'title': 'Senior Product Manager, AI', 'company': 'Acme', 'location': 'Remote US',
        'salary': '$170k-$210k', 'description_quote': 'Acme is hiring a Senior Product Manager, AI (Remote US), open to MBA students graduating in spring 2027.',
        'apply_url': 'https://acme.example/jobs/pm'}
VALUES = {
    'title': ['Senior Product Manager, AI', '', '   ', 'Not in the post', 3, None, 'P' * 1001],
    'company': ['Acme', '', ' ', 'Beta', 7],
    'location': ['Remote US', '', 'Mars', 5],
    'salary': ['$170k-$210k', '', '$1', None],
    'description_quote': ['Acme is hiring a Senior Product Manager, AI (Remote US), open to MBA students graduating in spring 2027.', '', 'x', 'A' * 301, 9],
    'apply_url': ['https://acme.example/jobs/pm', '', 'https://evil.example/x', 'http://acme.example/jobs/pm', 4],
}


def old_accepts(fact):
    """The acceptance rule exactly as it was before the reason codes (a value either passes or the fact is refused)."""
    if not isinstance(fact, dict) or set(fact) != pf.fact_fields('item_id'):
        return False
    candidate = CANDIDATE if isinstance(fact['item_id'], str) and fact['item_id'] == '1' else None
    if candidate is None:
        return False
    for field, value in fact.items():
        if field == 'item_id':
            continue
        if (not isinstance(value, str) or len(value) > (300 if field == 'description_quote' else 1000)
                or (not value.strip() and field not in {'location', 'salary', 'apply_url'})
                or (value and field != 'apply_url' and value not in candidate['text'])):
            return False
    link = fact['apply_url']
    return not (link and (link not in candidate['links'] or not https_url(link)))


def new_accepts(fact):
    try:
        pf._posting(fact, {'1': CANDIDATE}, '2026-10-19T00:00:00+00:00', source_id='x-twscrape', id_field='item_id',
                    id_prefix='x', permalink=lambda c: c['url'])
    except (ValueError, TypeError, AttributeError):
        return False
    return True


def test_the_fact_checker_accepts_and_rejects_exactly_what_it_did_before():
    checked = 0
    for field, options in VALUES.items():                      # every single-field change
        for value in options:
            fact = GOOD | {field: value}
            assert new_accepts(fact) == old_accepts(fact), (field, value)
            checked += 1
    for (f1, v1s), (f2, v2s) in itertools.combinations(VALUES.items(), 2):   # every pair of changes
        for v1, v2 in itertools.product(v1s, v2s):
            fact = GOOD | {f1: v1, f2: v2}
            assert new_accepts(fact) == old_accepts(fact), (f1, v1, f2, v2)
            checked += 1
    for fact in ['text', None, [], {'item_id': '1'}, GOOD | {'extra': 'x'}, GOOD | {'item_id': '2'}, GOOD | {'item_id': 1}]:
        assert new_accepts(fact) == old_accepts(fact), fact
    assert checked > 400 and new_accepts(GOOD) and not new_accepts(GOOD | {'company': 'Beta'})


TITLES = ['Senior Product Manager, AI', 'Chief of Staff', 'Strategy Lead', 'Forward Deployed AI Strategist', 'Entrepreneur in Residence',
          'Project Manager', 'Marketing Manager', 'Software Engineer', 'Product Marketing Manager', 'Intern, Product Manager', 'Program Manager']
PLACES = ['Remote US', 'New York, NY', 'London, UK', 'Toronto, Canada', 'Colombia', 'Brazil', 'Remote - Brazil', 'Sao Paulo, Brazil', '', 'Worldwide']
SALARIES = ['', 'USD 50,000 per year', 'USD 90,000 per year', 'USD 120,000 per year', 'USD 200,000 per year', '$190k-$220k', 'EUR 50,000 per year']


def posting(title, place, salary, remote):
    return Posting('x:1:abc', 'x-twscrape', 'Acme', title, place, 'Open to MBA students graduating in spring 2027.', 'https://acme.example/jobs/1',
                   '2026-10-19T00:00:00+00:00', salary=salary, remote=remote)


def old_collection_match(item):
    return bool(role_family(item.title)
                and collection_region(item.location, remote=item.remote) is not None
                and salary_preference(item)[0] != 'below floor')


@pytest.mark.parametrize('remote', [False, True])
def test_the_collection_filter_collects_exactly_what_it_did_before_and_every_drop_has_a_reason(remote):
    reasons = set()
    for title, place, salary in itertools.product(TITLES, PLACES, SALARIES):
        item = posting(title, place, salary, remote)
        reason = collection_reason(item)
        assert collection_match(item) == old_collection_match(item) == (reason == ''), (title, place, salary)
        assert reason in {'', 'role_not_in_scope', 'place_excluded', 'pay_below_floor'}
        reasons.add(reason)
    assert reasons == {'', 'role_not_in_scope', 'place_excluded', 'pay_below_floor'}   # the grid reaches every outcome
