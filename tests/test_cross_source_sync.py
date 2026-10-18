"""Cross-run reconciliation uses employer links without changing user-owned cells."""

import pytest

from sheet_fakes import MemoryStore
from jobhunter.postings import Posting, to_row
from jobhunter.sheets import sync_jobs
from scripts.source_probe import record

STAMP = '2026-10-18T00:00:00+00:00'
URL = 'https://job-boards.greenhouse.io/acme/jobs/123'


def row(identity, source, url=URL):
    return to_row(Posting(identity, source, 'Acme', 'Product Manager, AI', 'United States',
                          'Build AI products.', url, STAMP))


def deliver(store, rows, identity):
    sources = [record(source, 'OK', STAMP, selected=sum(r['Source'] == source for r in rows))
               for source in sorted({r['Source'] for r in rows})]
    return sync_jobs(store, rows, sources, run_id=identity, now=lambda: STAMP,
                     sleep=lambda _: None, jitter=lambda: 0)


@pytest.mark.parametrize('aggregate_first', [False, True])
def test_cross_source_reconciliation_preserves_existing_id_date_and_user_cells(aggregate_first):
    direct = row('greenhouse:acme:123', 'greenhouse:acme')
    aggregate = row('remotive:9', 'remotive', URL + '?ref=remotive')
    first, second = (aggregate, direct) if aggregate_first else (direct, aggregate)
    store = MemoryStore()
    deliver(store, [first], 'first')
    headers, values = store.tables['Jobs']
    for name, value in [('Status', 'Applied'), ('Notes', 'Keep this note'), ('My rating', '5'),
                        ('Date found', '2026-10-01')]:
        values[headers.index(name)] = value
    deliver(store, [second], 'second')
    deliver(store, [second], 'second')
    deliver(store, [second], 'third')
    assert len(store.tables['Jobs']) == 2
    result = dict(zip(headers, store.tables['Jobs'][1]))
    assert result['Job ID'] == first['Job ID']
    assert result['Source'] == first['Source']
    assert (result['Status'], result['Notes'], result['My rating'], result['Date found']) == (
        'Applied', 'Keep this note', '5', '2026-10-01')
    assert 'greenhouse:acme' in result['More details'] and 'remotive' in result['More details']
    assert result['More details'].count('First seen by remotive:') == 1


def test_cross_source_reconciliation_handles_old_and_new_identity_in_the_same_batch():
    store = MemoryStore()
    direct = row('greenhouse:acme:123', 'greenhouse:acme')
    aggregate = row('remotive:9', 'remotive', URL + '?ref=remotive')
    deliver(store, [aggregate], 'first')
    result = deliver(store, [direct, aggregate], 'second')
    assert len(store.tables['Jobs']) == 2
    assert store.tables['Jobs'][1][0] == 'remotive:9'
    assert result['unique_jobs'] == 1
    headers = store.tables['Run Log'][0]
    assert store.tables['Run Log'][-1][headers.index('Jobs unique')] == 1


def test_existing_ambiguous_employer_links_require_manual_reconciliation():
    store = MemoryStore()
    first = row('greenhouse:acme:123', 'greenhouse:acme')
    second = row('remotive:9', 'remotive', URL + '?ref=remotive')
    from jobhunter.sheet_records import JOB_HEADERS
    store.tables['Jobs'] = [list(JOB_HEADERS), [first[h] for h in JOB_HEADERS], [second[h] for h in JOB_HEADERS]]
    with pytest.raises(ValueError, match='ambiguous_existing_job_identity'):
        deliver(store, [row('third:7', 'third')], 'new')
    assert all(title != 'Jobs' for title, _ in store.writes)


def test_distinct_source_requisitions_sharing_a_generic_link_remain_separate():
    store = MemoryStore()
    deliver(store, [row('remotive:1', 'remotive', 'https://example.com/careers')], 'one')
    deliver(store, [row('remotive:2', 'remotive', 'https://example.com/careers')], 'two')
    assert len(store.tables['Jobs']) == 3
    headers = store.tables['Jobs'][0]
    assert 'Possible duplicate of remotive:1' in store.tables['Jobs'][2][headers.index('More details')]


def test_a_historical_generic_link_cannot_collapse_new_source_requisitions():
    store = MemoryStore()
    deliver(store, [row('remotive:1', 'remotive', 'https://example.com/careers')], 'first')
    store.writes.clear()
    incoming = [row(f'himalayas:{n}', 'himalayas', 'https://example.com/careers')
                | {'Job title': f'Product Manager, AI {n}'} for n in (1, 2)]
    deliver(store, incoming, 'second')
    deliver(store, incoming, 'second')
    assert len(store.tables['Jobs']) == 4
    assert store.tables['Jobs'][1][0] == 'remotive:1'
    headers = store.tables['Jobs'][0]
    for values in store.tables['Jobs'][2:]:
        assert 'Possible duplicate of remotive:1' in values[headers.index('More details')]
        assert 'needs review' in values[headers.index('More details')]


def test_new_sources_sharing_an_uncertain_link_never_block_the_daily_batch():
    store = MemoryStore()
    for source in ('remotive', 'himalayas', 'jobicy', 'fourth'):
        incoming = row(source + ':1', source, 'https://example.com/careers/pm')
        deliver(store, [incoming], source)
        deliver(store, [incoming], source)
    assert len(store.tables['Jobs']) == 5
    headers = store.tables['Jobs'][0]
    assert all('needs review' in values[headers.index('More details')]
               for values in store.tables['Jobs'][2:])


def test_custom_greenhouse_requisition_reconciles_across_runs():
    store = MemoryStore()
    deliver(store, [row('remotive:1', 'remotive', 'https://example.com/careers?gh_jid=111')], 'first')
    deliver(store, [row('himalayas:2', 'himalayas', 'https://example.com/careers?gh_jid=111')], 'second')
    assert len(store.tables['Jobs']) == 2
    assert store.tables['Jobs'][1][0] == 'remotive:1'


def test_same_batch_discovery_attribution_survives_later_direct_only_syncs():
    from jobhunter.postings import dedupe
    direct = Posting('greenhouse:acme:123', 'greenhouse:acme', 'Acme', 'Product Manager, AI',
                     'United States', 'Build AI products.', URL, STAMP)
    other = Posting('remotive:9', 'remotive', 'Acme', direct.title, direct.location,
                    direct.text, URL, STAMP)
    store = MemoryStore()
    deliver(store, [to_row(*item) for item in dedupe([direct, other])], 'both')
    headers, values = store.tables['Jobs']
    initial = values[headers.index('More details')]
    assert f'First seen by greenhouse:acme: {STAMP}' in initial
    assert f'First seen by remotive: {STAMP}' in initial
    for name, value in [('Status', 'Applied'), ('Notes', 'Keep this note'), ('My rating', '5')]:
        values[headers.index(name)] = value
    deliver(store, [to_row(direct)], 'direct-only')
    details = store.tables['Jobs'][1][headers.index('More details')]
    assert 'Also listed by: remotive' in details
    from dataclasses import replace
    third = replace(other, job_id='himalayas:2', source_id='himalayas')
    incoming = [to_row(*item) for item in dedupe([direct, third])]
    deliver(store, incoming, 'third-source')
    expected = store.tables['Jobs'][1][headers.index('More details')]
    assert 'Also listed by: himalayas, remotive' in expected
    assert expected.count('Also listed by:') == 1
    for source in ('greenhouse:acme', 'remotive', 'himalayas'):
        assert expected.count(f'First seen by {source}: {STAMP}') == 1
    deliver(store, incoming, 'third-source-repeat')
    assert store.tables['Jobs'][1][headers.index('More details')] == expected
    assert len(store.tables['Jobs']) == 2
    result = dict(zip(headers, store.tables['Jobs'][1]))
    assert (result['Status'], result['Notes'], result['My rating']) == ('Applied', 'Keep this note', '5')


def test_legacy_same_batch_attribution_is_retained_without_inventing_its_time():
    from jobhunter.sheet_records import JOB_HEADERS
    store = MemoryStore()
    old = row('greenhouse:acme:123', 'greenhouse:acme')
    old['More details'] = 'Source: ' + URL + '\nAlso listed by: remotive'
    store.tables['Jobs'] = [list(JOB_HEADERS), [old[h] for h in JOB_HEADERS]]
    deliver(store, [row('greenhouse:acme:123', 'greenhouse:acme')], 'legacy')
    details = store.tables['Jobs'][1][JOB_HEADERS.index('More details')]
    assert 'Also listed by: remotive' in details
    assert 'First seen by remotive:' not in details  # historical time was not retained


def test_discovery_times_are_ordered_by_instant_and_not_timezone_text():
    from dataclasses import replace
    direct = Posting('greenhouse:acme:123', 'greenhouse:acme', 'Acme', 'Product Manager, AI',
                     'United States', 'Build AI products.', URL, '2026-10-18T09:00:00+00:00')
    store = MemoryStore()
    deliver(store, [to_row(direct)], 'first-instant')
    earlier = replace(direct, captured_at='2026-10-18T10:30:00+02:00')
    deliver(store, [to_row(earlier)], 'earlier-instant')
    headers = store.tables['Jobs'][0]
    details = store.tables['Jobs'][1][headers.index('More details')]
    assert 'First seen by greenhouse:acme: 2026-10-18T10:30:00+02:00' in details
    deliver(store, [to_row(direct)], 'later-instant')
    assert store.tables['Jobs'][1][headers.index('More details')] == details
