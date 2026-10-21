"""Regressions for the exact-head October 19 review findings; all inputs are synthetic."""

import hashlib
import sys
from pathlib import Path

import pytest

from jobhunter import post_facts as pf
from jobhunter import postings as p
from jobhunter.sheet_records import JOB_HEADERS, plan_jobs, reconcile_jobs
from scripts import eval_reading as ev
from scripts import linkedin_collect as li
from scripts import x_collect as x

STAMP = '2026-10-19T16:00:00+00:00'


@pytest.mark.parametrize('collector', [x, li], ids=['x', 'linkedin'])
@pytest.mark.parametrize('failure', ['workbook', 'reservation'])
def test_startup_failure_disposes_of_the_authenticated_resource(tmp_path, monkeypatch, collector, failure):
    # The external session is represented by a real temporary file: missing cleanup leaves it on disk.
    private = tmp_path / 'synthetic-session'
    private.write_text('synthetic fixture, no credentials')

    class Session:
        def close(self):
            private.unlink()

    session = Session()
    monkeypatch.setitem(sys.modules, 'twscrape' if collector is x else 'playwright', object())
    constructor = 'TwscrapeFetcher' if collector is x else 'BrowserSession'
    monkeypatch.setattr(collector, constructor, lambda *a, **kw: session)
    if failure == 'workbook':
        from jobhunter import google_auth
        monkeypatch.setattr(google_auth, 'open_workbook', lambda: (_ for _ in ()).throw(ValueError('google_not_configured')))
        store = None
    else:
        monkeypatch.setattr(collector, 'reserve', lambda *a: (_ for _ in ()).throw(ValueError('invalid_allowance_state')))
        store = object()
    settings = {'X_AUTH_TOKEN': 'synthetic-only', 'X_CT0': 'synthetic-only', 'LINKEDIN_LI_AT': 'synthetic-only'}
    output = tmp_path.parent / (tmp_path.name + '-output.json')
    code = collector.main(['--run-id', 'repair-check', '--output', str(output)], store=store,
                          environ=settings, now=lambda: STAMP)
    assert code == 2 and not output.exists()
    assert not private.exists(), 'the authenticated resource must be disposed of on every startup failure'


@pytest.mark.parametrize('prefix,sources', [('waas', ('waas-product', 'waas-operations')),
                                          ('a16z', ('a16z-product', 'a16z-strategy'))])
def test_same_id_discoveries_keep_each_sources_earliest_time(prefix, sources):
    def posting(source, stamp):
        return p.Posting(prefix + ':11', source, 'Acme', 'Product Manager', 'Remote', 'text',
                         'https://acme.example/careers', stamp)
    kept = p.dedupe([posting(sources[0], STAMP), posting(sources[1], STAMP),
                     posting(sources[1], '2026-10-18T10:00:00+00:00')])
    assert len(kept) == 1
    assert f'First seen by {sources[1]}: 2026-10-18T10:00:00+00:00' in kept[0][1]


def test_unknown_fact_id_cannot_copy_a_name_into_the_trace():
    from test_social_posts import build, fact
    result = build([fact(item_id='example_person_name')])
    assert result['rejections'] == [{'item_id': '', 'reason': 'unknown_post'}]
    assert 'example_person_name' not in pf.format_trace(result)


def test_reason_codes_are_an_allowlist_not_arbitrary_lowercase_text():
    assert pf._reason(ValueError('example_person_name')) == 'malformed_fact'
    assert pf._reason(ValueError('empty:company')) == 'empty:company'


@pytest.mark.parametrize('processed', [[], ['1'], ['1', '1'], ['1', '2', 'unknown']])
def test_model_comparison_refuses_incomplete_or_unrecognized_reading(processed):
    items = [{'item_id': str(n), 'text': 'No roles here.', 'url': f'https://x.com/example/status/{n}',
              'links': [], 'created_at': STAMP} for n in (1, 2)]
    with pytest.raises(ValueError, match='incomplete_eval_reading'):
        ev.compare(items, 'item_id', {'processed': processed, 'facts': []},
                   {'processed': ['1', '2'], 'facts': []}, ('sonnet', 'haiku'))


def test_linkedin_output_alias_is_rejected_before_any_allowance_or_request(tmp_path):
    from sheet_fakes import MemoryStore
    from test_linkedin_collect import fetcher, ok, COOKIES
    output = str(tmp_path.parent / (tmp_path.name + '-alias.json'))
    alias = str(tmp_path.parent) + '/./' + Path(output).name
    store = MemoryStore()
    session = fetcher(ok())
    code = li.main(['--run-id', 'alias-check', '--output', output, '--jobs-output', alias],
                   store=store, fetcher=session, environ=COOKIES, now=lambda: STAMP, sleep=lambda _: None)
    assert code == 2
    assert '_State' not in store.tables and not Path(output).exists()
    assert session.session.urls == []


def newsletter_jobs(slug, roles):
    text = '\n'.join(f'{title} at Acme, Remote, for MBA students graduating in spring 2027. Apply {link}' for title, link in roles)
    candidate = {'item_id': slug, 'url': f'https://alirohdejobs.substack.com/p/{slug}',
                 'created_at': STAMP, 'text': text, 'links': [link for _, link in roles]}
    facts = [{'item_id': slug, 'title': title, 'company': 'Acme', 'location': 'Remote', 'salary': '',
              'description_quote': f'{title} at Acme, Remote, for MBA students graduating in spring 2027.', 'apply_url': link} for title, link in roles]
    result = pf.social_result('alirohde-rss', [candidate], facts, STAMP, listed=1, stats={})
    return [p.Posting(**row) for row in result['postings']]


def test_tracking_changes_do_not_create_a_new_newsletter_job_next_week():
    a = newsletter_jobs('edition-275-example', [('Chief of Staff',
        'https://boards.greenhouse.io/acme/jobs/12345?utm_campaign=275')])
    b = newsletter_jobs('edition-276-example', [('Chief of Staff',
        'https://job-boards.greenhouse.io/acme/jobs/12345?utm_campaign=276')])
    assert a[0].job_id == b[0].job_id
    assert len(p.dedupe(a + b)) == 1


def test_two_newsletter_roles_sharing_a_generic_link_are_both_retained():
    jobs = newsletter_jobs('edition-275-example', [('Chief of Staff', 'https://acme.example/careers'),
                                                  ('Product Manager', 'https://acme.example/careers')])
    assert {job.title for job in jobs} == {'Chief of Staff', 'Product Manager'}
    assert len({job.job_id for job in jobs}) == 2
    assert len(p.dedupe(jobs)) == 2


def legacy_newsletter_row(link, title='Chief of Staff'):
    row = p.to_row(newsletter_jobs('edition-275-example', [(title, link)])[0])
    return row | {'Job ID': 'alirohde:' + hashlib.sha256(link.encode()).hexdigest()[:16],
                  'Status': 'Applied', 'Notes': 'Keep my notes', 'My rating': '5', 'Date found': '2026-10-16'}


@pytest.mark.parametrize('old_link,new_link', [
    ('https://boards.greenhouse.io/acme/jobs/12345?utm_campaign=275',
     'https://boards.greenhouse.io/acme/jobs/12345?utm_campaign=276'),
])
def test_newsletter_identity_repairs_reuse_legacy_rows_and_preserve_user_cells(old_link, new_link):
    old = legacy_newsletter_row(old_link)
    headers = list(reversed(JOB_HEADERS))
    rows = [headers, [old[h] for h in headers]]
    incoming = p.to_row(newsletter_jobs('edition-276-example', [('Chief of Staff', new_link)])[0])
    assert reconcile_jobs(rows, [incoming])[0]['Job ID'] == old['Job ID']
    writes = plan_jobs(rows, [incoming])
    protected = {headers.index(h) + 1 for h in ('Job ID', 'Date found', 'Status', 'Notes', 'My rating')}
    assert all(write.row == 2 and write.column not in protected for write in writes)
    for write in writes:
        rows[write.row - 1][write.column - 1] = write.values[0][0]
    saved = dict(zip(headers, rows[1]))
    assert {h: saved[h] for h in ('Job ID', 'Date found', 'Status', 'Notes', 'My rating')} == {
        h: old[h] for h in ('Job ID', 'Date found', 'Status', 'Notes', 'My rating')}
    assert plan_jobs(rows, [incoming]) == []


def test_shared_generic_link_does_not_reassign_a_different_role_to_a_legacy_row():
    link = 'https://acme.example/careers'
    old = legacy_newsletter_row(link)
    incoming = p.to_row(newsletter_jobs('edition-276-example', [('Product Manager', link)])[0])
    rows = [list(JOB_HEADERS), [old[h] for h in JOB_HEADERS]]
    writes = plan_jobs(rows, [incoming])
    assert len(writes) == 1 and writes[0].row == 3
    assert dict(zip(JOB_HEADERS, writes[0].values[0]))['Job title'] == 'Product Manager'


def test_multiple_legacy_matches_stop_without_choosing_whose_notes_to_keep():
    links = [f'https://boards.greenhouse.io/acme/jobs/12345?utm_campaign={n}' for n in (275, 276)]
    old = [legacy_newsletter_row(link) for link in links]
    rows = [list(JOB_HEADERS)] + [[row[h] for h in JOB_HEADERS] for row in old]
    incoming = p.to_row(newsletter_jobs('edition-277-example', [('Chief of Staff',
        'https://boards.greenhouse.io/acme/jobs/12345')])[0])
    with pytest.raises(ValueError, match='ambiguous_existing_job_identity'):
        plan_jobs(rows, [incoming])


def test_a_generic_legacy_link_never_guesses_identity_from_company_and_title():
    link = 'https://acme.example/careers'
    old = legacy_newsletter_row(link)
    incoming = p.to_row(newsletter_jobs('edition-276-example', [('Chief of Staff', link)])[0])
    rows = [list(JOB_HEADERS), [old[h] for h in JOB_HEADERS]]
    writes = plan_jobs(rows, [incoming])
    assert len(writes) == 1 and writes[0].row == 3
    new = dict(zip(JOB_HEADERS, writes[0].values[0]))
    assert new['Job ID'] != old['Job ID'] and 'needs review' in new['More details']
    assert rows[1][JOB_HEADERS.index('Notes')] == 'Keep my notes'
