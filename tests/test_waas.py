"""Work at a Startup public pages: listing page data, each job's own page, and the Accept header the site requires."""

import html
import json

import httpx

from jobhunter import postings as p
from scripts import source_probe as probe

STAMP = '2026-10-19T17:00:00+00:00'
ENTRY = {'id': 'waas-product', 'kind': 'waas', 'url': 'https://www.workatastartup.com/jobs/l/product-manager'}


def page(props):
    return f'<div id="app" data-page="{html.escape(json.dumps({"component": "x", "props": props}), quote=True)}"></div>'


LISTING = page({'jobs': [
    {'id': 11, 'title': 'Senior Product Manager, AI', 'location': 'San Francisco', 'salary': '$180K - $240K',
     'companyName': 'Acme AI', 'companySlug': 'acme'},
    {'id': 12, 'title': 'Software Engineer', 'location': 'Remote (US)', 'salary': '$150K - $200K', 'companyName': 'Acme AI'},
    {'title': 'No id here'}], 'totalJobsCount': 241})
DETAIL = page({'job': {'id': 11, 'title': 'Senior Product Manager, AI', 'location': 'San Francisco, CA, US',
                       'salaryRange': '$180K - $240K', 'descriptionHtml': '<p>Own the <b>agent</b> roadmap.</p>'},
               'company': {'name': 'Acme AI'}})


def test_listing_rows_come_from_the_page_data_and_a_row_without_an_id_is_rejected():
    stubs, rejected = p.stubs_waas(LISTING, {'source_id': 'waas-product'})
    assert [s['job_id'] for s in stubs] == ['waas-product:11', 'waas-product:12'] and rejected == 1
    assert stubs[0]['url'] == 'https://www.workatastartup.com/jobs/11' and stubs[0]['salary'] == '$180K - $240K'


def test_a_job_page_gives_clean_text_company_location_and_salary_and_an_empty_one_is_rejected():
    found = p.detail_waas(DETAIL)
    assert found['text'] == 'Own the agent roadmap.' and found['company'] == 'Acme AI' and found['location'] == 'San Francisco, CA, US'
    try:
        p.detail_waas(page({'job': {'descriptionHtml': ''}, 'company': {}}))
    except ValueError as exc:
        assert str(exc) == 'invalid_board_response'
    else:
        raise AssertionError('an empty description must be rejected')


def test_the_source_asks_for_html_and_delivers_only_the_matching_job():
    seen = []

    def handler(request):
        seen.append((str(request.url), request.headers['accept']))
        if request.headers['accept'].startswith('text/html') is False:
            return httpx.Response(406)  # what the real site does
        return httpx.Response(200, text=DETAIL if request.url.path == '/jobs/11' else LISTING)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        source, jobs, note = probe.probe_source(client, ENTRY, STAMP, lookback_days=28)
    assert source['status'] == 'OK' and [j.job_id for j in jobs] == ['waas-product:11']
    assert jobs[0].company == 'Acme AI' and jobs[0].posted_at == '' and 'date_unknown=1' in note
    assert [url for url, _ in seen] == ['https://www.workatastartup.com/jobs/l/product-manager', 'https://www.workatastartup.com/jobs/11']


def test_a_406_is_reported_as_blocked_not_as_an_empty_source():
    with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(406))) as client:
        source, jobs, _ = probe.probe_source(client, ENTRY, STAMP)
    assert source['status'] == 'blocked' and jobs == []


def test_the_registry_lists_both_public_pages():
    import yaml
    entries = yaml.safe_load(open('sources/v0_sources.yaml'))['detail_sources']
    assert {e['id'] for e in entries if e['kind'] == 'waas'} == {'waas-product', 'waas-operations'}
