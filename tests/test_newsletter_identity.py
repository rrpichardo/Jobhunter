"""Newsletter job identity: tracking links must not create new jobs; legacy rows and user cells are preserved."""

import hashlib

import pytest

from jobhunter import post_facts as pf
from jobhunter import postings as p
from jobhunter.sheet_records import JOB_HEADERS, plan_jobs, reconcile_jobs

STAMP = '2026-10-19T16:00:00+00:00'


def newsletter_jobs(slug, roles):
    text = '\n'.join(f'{title} at Acme, Remote, open to MBA students graduating in spring 2027. Apply {link}' for title, link in roles)
    candidate = {'item_id': slug, 'url': f'https://alirohdejobs.substack.com/p/{slug}',
                 'created_at': STAMP, 'text': text, 'links': [link for _, link in roles]}
    facts = [{'item_id': slug, 'title': title, 'company': 'Acme', 'location': 'Remote', 'salary': '',
              'description_quote': f'{title} at Acme, Remote, open to MBA students graduating in spring 2027.', 'apply_url': link} for title, link in roles]
    result = pf.social_result('alirohde-rss', [candidate], facts, STAMP, listed=1, stats={})
    return [p.Posting(**row) for row in result['postings']]


def test_tracking_changes_do_not_create_a_new_newsletter_job_next_week():
    a = newsletter_jobs('edition-275-example', [('Chief of Staff',
        'https://boards.greenhouse.io/acme/jobs/12345?utm_campaign=275')])
    b = newsletter_jobs('edition-276-example', [('Chief of Staff',
        'https://job-boards.greenhouse.io/acme/jobs/12345?utm_campaign=276')])
    assert a[0].job_id == b[0].job_id  # one job; the cross-source merge of identical IDs is covered where that merge lives


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
