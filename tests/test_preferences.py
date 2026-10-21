"""Current user preferences, independent of the historical AI-only probe."""
from dataclasses import replace

import httpx
import pytest

from jobhunter import postings as p
from scripts import source_probe
from mba_fixtures import mba


def job(**changes):
    base = p.Posting('lever:acme:1', 'lever:acme', 'Acme', 'Product Manager',
                     'United States', mba('Build billing products. This role is open to MBA students graduating in spring 2027.'), 'https://jobs.lever.co/acme/1',
                     '2026-10-18T00:00:00+00:00', salary='USD 140,000 annually')
    return replace(base, **changes)


@pytest.mark.parametrize('title', ['Product Manager, Billing', 'Senior Product Manager',
    'Group Product Manager', 'Product Lead', 'Chief of Staff', 'MBA Leadership Development Program',
    'Strategy Manager', 'Director of Strategy', 'Entrepreneur in Residence', 'Project Manager',
    'Forward-Deployed AI Strategist', 'Forward Deployed Strategist', 'Senior Forward Deployed AI Strategist - Public Sector',
    'AI Strategist, Forward Deployed', 'AI Strategist (Forward-Deployed)', 'FDE Strategist', 'Forward Deployed Strategy Lead',
    'AI Deployment Strategist', 'AI Implementation Strategist', 'Senior AI Implementation Strategist (Remote)',
    'GenAI Deployment Strategist', 'Deployment Strategist', 'AI Strategist (FDE)', 'Staff Forward Deployed Strategist',
    'Forward Deployed AI Strategist (Remote, US)'])
def test_non_ai_role_families_are_collection_candidates(title):
    assert p.collection_match(job(title=title))


@pytest.mark.parametrize('title', ['Software Engineer', 'Product Marketing Manager', 'Program Manager',
    'Project Manager Intern', 'Summer Associate, Strategy', 'Product Designer', 'Strategy Analyst',
    'Forward Deployed Engineer', 'Forward-Deployed Software Engineer, Strategy Platform', 'Implementation Strategist',
    'AI Deployment Engineer', 'Forward-Deployed Engineer - AI Strategy', 'Strategy & Operations - Forward Deployed Engineer',
    'Strategy, Forward Deployed Engineer', 'Forward Deployed Engineering Lead (AI Strategy)', 'FDE Engineer (AI Strategy)',
    'Forward Deployed Developer - Strategy', 'FDE - AI Strategy', 'AI Strategy FDE', 'Strategy (FDE)', 'FDE (AI Strategy)',
    'Forward Deployed Eng. - AI Strategy', 'Forward Deployed Engr - Strategy', 'Forward Deployed Developers - Strategy',
    'Forward Deployed Software Development - AI Strategy', 'Forward Deployed SDE - Strategy'])
def test_unapproved_or_intern_titles_are_not_candidates(title):
    assert not p.collection_match(job(title=title))


@pytest.mark.parametrize('location,remote,salary,expected', [
    ('United States', False, 'USD 139,999 annually', False),
    ('Remote - US', True, 'USD 70,000 annually', False),
    ('United States', True, 'USD 140,000 annually', True),
    ('United States', False, 'USD 120,000 - 145,000 annually', True),
    ('LATAM', True, 'USD 69,999 annually', False),
    ('Remote - Brazil', False, 'USD 70,000 annually', True),
    ('Colombia', False, 'USD 70,000 annually', True),
    ('Dominican Republic (Hybrid)', False, 'USD 70,000 annually', True),
    ('Brazil (Hybrid)', False, 'USD 170,000 annually', False),
    ('Canada (Remote)', True, 'USD 170,000 annually', False),
    ('United States or LATAM', True, 'USD 70,000 annually', True),
])
def test_region_and_salary_floors(location, remote, salary, expected):
    assert p.collection_match(job(location=location, remote=remote, salary=salary)) is expected


@pytest.mark.parametrize('location', ['United States', 'Remote - Colombia', 'Colombia (Hybrid)'])
@pytest.mark.parametrize('salary', ['', '$200k', 'COP 700,000,000 annually', 'USD 200,000 OTE annually',
                                    'USD 90 hourly', 'USD 20,000 monthly'])
def test_unknown_salary_is_retained_but_flagged_for_checking(location, salary):
    candidate = job(location=location, salary=salary)
    assert p.collection_match(candidate)
    row = p.to_row(candidate)
    assert row['Fit'] == '' and row['Status'] == 'New'
    assert row['Next step'] == '' and 'annual USD base salary' in row['More details']
    assert 'Salary preference: unresolved' in row['More details']


def test_unknown_location_does_not_get_confirmed_salary_preference():
    row = p.to_row(job(location=''))
    assert 'location' in row['More details']
    assert 'Salary preference: satisfied' not in row['More details']


def test_matching_salary_is_a_preference_check_not_full_eligibility():
    row = p.to_row(job())
    assert row['Fit'] == '' and row['Next step'] == ''
    assert 'Salary preference: satisfied (annual USD floor 140000)' in row['More details']
    assert 'Role family: Product management' in row['More details']


def test_broader_roles_flow_through_probe_without_ai_signal():
    data = [{'id': str(i), 'text': title, 'categories': {'location': 'United States'},
             'descriptionPlain': 'Build billing products. This role is open to MBA students graduating in spring 2027.', 'hostedUrl': f'https://jobs.lever.co/acme/{i}'}
            for i, title in enumerate(['Product Manager', 'Chief of Staff', 'Project Manager', 'Engineer'])]
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=data)))
    entry = {'id': 'lever:acme', 'kind': 'lever', 'board': 'acme', 'company': 'Acme', 'url': 'https://test.example/jobs'}
    record, jobs, _ = source_probe.probe_source(client, entry, '2026-10-18T00:00:00+00:00')
    assert [item.title for item in jobs] == ['Product Manager', 'Chief of Staff', 'Project Manager']
    assert record['pm_candidates'] == 3 and record['selected_for_m0'] == 3


@pytest.mark.parametrize('location', ['Bogotá, CO', 'Medellín, CO', 'Santo Domingo, DO',
    'Bogotá, CO (Hybrid)', 'Bogotá, CO - Hybrid', 'Medellín, Antioquia, CO',
    'Medellín, Antioquia, CO (Remote)', 'Santo Domingo, DO (Hybrid)',
    'Bogotá D.C., CO', 'Bogota DC, CO', 'Bogotá DC, CO'])
def test_approved_regional_cities_use_latam_floor(location):
    candidate = job(location=location, salary='USD 80,000 annually')
    assert p.collection_region(location) == 'LATAM'
    assert p.collection_match(candidate)
    assert p.salary_preference(candidate) == ('satisfied', 70_000)


@pytest.mark.parametrize('location', ['Bogotá', 'Medellín', 'Santo Domingo'])
def test_city_without_country_is_retained_as_unresolved_not_assumed_eligible(location):
    candidate = job(location=location, salary='USD 80,000 annually')
    assert p.collection_match(candidate)
    assert p.salary_preference(candidate)[0] == 'unresolved'


@pytest.mark.parametrize('location', ['', 'Remote', 'Worldwide'])
def test_unknown_location_still_excludes_salary_below_every_floor(location):
    candidate = job(location=location, salary='USD 50,000 annually')
    assert not p.collection_match(candidate)
    assert not p.collection_stub_match(candidate.title, location, candidate.salary)


@pytest.mark.parametrize('location', ['Remote (US or Colombia)',
    'New York, NY or Bogotá, Colombia', 'San Francisco, CA; Remote - Latin America',
    'Austin, Texas or Remote (Colombia)', 'Bogotá, Colombia; Seattle', 'Bogotá, CO or New York, NY',
    'New York, NY or Bogotá, CO', 'Seattle or Medellín, CO', 'Austin, TX or Santo Domingo, DO',
    'Bogotá, Colombia or Pittsburgh, PA', 'Colombia or Philadelphia, PA',
    'Bogotá, Colombia or Boulder, CO', 'Medellín, CO / Boulder, CO',
    'Remote - LATAM or Little Rock, AR', 'Boulder, CO / Medellín, CO',
    'Little Rock, AR or Remote - LATAM', 'Pittsburgh, PA or Bogotá, Colombia'])
def test_mixed_us_latam_location_retained_without_assuming_which_floor_applies(location):
    candidate = job(location=location, salary='USD 90,000 annually')
    assert p.collection_match(candidate)
    assert p.salary_preference(candidate)[0] == 'unresolved'


@pytest.mark.parametrize('location', ['Colombia, CO', 'Panama, PA (Remote)',
    'Argentina, AR (Remote)', 'Medellín, Antioquia, CO', 'Bogota, D.C., CO'])
def test_explicit_regional_country_codes_do_not_fabricate_a_us_option(location):
    candidate = job(location=location, salary='USD 90,000 annually')
    assert p.salary_preference(candidate) == ('satisfied', 70_000)


@pytest.mark.parametrize('location', ['Pittsburgh, PA', 'Boulder, CO (Hybrid)', 'Little Rock, AR'])
def test_standalone_us_ambiguous_state_codes_still_use_us_floor(location):
    assert p.salary_preference(job(location=location, salary='USD 90,000 annually')) == ('below floor', 140_000)


@pytest.mark.parametrize('separator', [' | ', ' - ', ' · ', ' & ', ' y ', '\n', ' — '])
def test_locality_normalization_cannot_swallow_another_location(separator):
    for first, second in [('Bogotá, Colombia', 'Boulder, CO'), ('Medellín, CO', 'Boulder, CO')]:
        for location in [first + separator + second, second + separator + first]:
            candidate = job(location=location, salary='USD 90,000 annually')
            assert p.salary_preference(candidate)[0] == 'unresolved', location
            assert p.collection_match(candidate), location


@pytest.mark.parametrize('location', ['Medellín, Unknown Department, CO', 'Bogotá DC', 'Bogotá D.C.',
    'Bogotá, DC', 'Bogotá DC (Remote)', 'Bogotá, DC (Hybrid)',
    'Bogotá, D.C. | Washington, DC', 'Bogotá, D.C.', 'Bogotá, D.C. (On-site)',
    'Bogotá, Distrito Capital', 'Bogotá, Cundinamarca', 'Medellín, Antioquia'])
def test_unverified_city_or_department_form_stays_unresolved(location):
    candidate = job(location=location, salary='USD 90,000 annually')
    assert p.collection_match(candidate)
    assert p.salary_preference(candidate)[0] == 'unresolved'


@pytest.mark.parametrize('location', ['Colombia or Boulder CO', 'Colombia or Pittsburgh PA',
    'Bogotá, Colombia - Boulder CO', 'LATAM/Houston TX', 'Colombia or boulder co',
    'Boulder CO or Colombia', 'Colombia or Unclassified place', 'Remote - LATAM / Unclassified place',
    'Colombia or Remote', 'Remote or Colombia', 'Colombia or (Remote)',
    'Remote, or Colombia', 'Remote, or Bogotá, Colombia', 'Remote, and Colombia',
    'Remoto, o Colombia', 'Remoto, y Colombia', 'Remote, & Colombia', 'Remote, / Colombia',
    'Remote - or Colombia', 'Remote: or Colombia', 'Remote / or Colombia',
    'Colombia or - Remote', 'Colombia and / Remote'])
def test_alternative_places_need_resolution_even_without_us_city_comma(location):
    candidate = job(location=location, salary='USD 90,000 annually')
    assert p.collection_match(candidate)
    assert p.salary_preference(candidate)[0] == 'unresolved'


@pytest.mark.parametrize('location', ['Boulder CO', 'Unclassified place'])
def test_unrecognized_location_is_unknown_not_confirmed_outside_scope(location):
    candidate = job(location=location, salary='USD 150,000 annually')
    assert p.collection_match(candidate)
    assert p.salary_preference(candidate)[0] == 'unresolved'


@pytest.mark.parametrize('location', ['Bogotá, Colombia, Toronto, Canada', 'Colombia, Canada',
    'Remote - Colombia, Canada', 'Colombia, Portland', 'Colombia, Raleigh',
    'Bogotá, Colombia, London, UK', 'Colombia, Unclassified place', 'Unclassified city, Colombia'])
def test_unknown_comma_delimited_place_cannot_satisfy_the_latam_floor(location):
    candidate = job(location=location, salary='USD 90,000 annually')
    assert p.collection_match(candidate)
    assert p.salary_preference(candidate)[0] == 'unresolved'


@pytest.mark.parametrize('location', ['Remote – Colombia', 'Colombia – Remote', 'Remote — LATAM',
    'Remoto - Colombia', 'Colombia - Bogotá', 'Bogotá, Colombia', 'Medellín, Antioquia, Colombia',
    'Colombia - Bogotá (Remote)', 'Bogotá (Remote), Colombia'])
def test_attached_remote_labels_and_known_regional_qualifiers_keep_latam_floor(location):
    candidate = job(location=location, salary='USD 90,000 annually')
    assert p.salary_preference(candidate) == ('satisfied', 70_000)


@pytest.mark.parametrize('location', ['Remote, Colombia', 'Remoto, Colombia', 'Remote, LATAM',
    'Remote, Bogotá, Colombia', 'Remote, Medellín, Antioquia, Colombia', 'Remote, Mexico',
    'Remote, Santo Domingo, Dominican Republic'])
def test_comma_prefix_remote_mode_is_attached_to_regional_location(location):
    assert p.salary_preference(job(location=location, salary='USD 90,000 annually')) == ('satisfied', 70_000)


def test_jsearch_remote_latam_metadata_flows_through_salary_and_row_checks():
    from test_source_probe import JSEARCH_BODY
    import copy
    payload = copy.deepcopy(JSEARCH_BODY)
    item = payload['data'][0]
    item.update(job_is_remote=True, job_city='Bogotá', job_state='Bogotá, D.C.', job_country='CO',
                job_min_salary=90_000, job_max_salary=100_000,
                job_salary_currency='USD', job_salary_period='YEAR')
    postings, _, _ = p.parse_jsearch(payload, {'source_id':'jsearch', 'captured_at':'2026-10-18T00:00:00+00:00'})
    candidate = postings[0]
    assert candidate.remote and candidate.location.startswith('Remote, ')
    assert p.salary_preference(candidate) == ('satisfied', 70_000)
    assert 'Salary preference: satisfied (annual USD floor 70000)' in p.to_row(candidate)['More details']


def test_unresolved_salary_check_is_in_details_not_next_step():
    row = p.to_row(job(salary=''))
    assert row['Next step'] == ''
    assert 'Check first:' in row['More details']


def test_every_board_match_is_kept_with_product_roles_first():
    titles = ['Project Manager'] * 8 + ['Chief of Staff', 'Product Manager, AI']
    data = [{'id': str(i), 'text': title, 'categories': {'location': 'United States'},
             'descriptionPlain': 'Build products. This role is open to MBA students graduating in spring 2027.', 'hostedUrl': f'https://jobs.lever.co/acme/{i}'}
            for i, title in enumerate(titles)]
    with httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(200, json=data))) as client:
        _, jobs, _ = source_probe.probe_source(client, {'id':'lever:acme', 'kind':'lever',
            'board':'acme', 'company':'Acme', 'url':'https://test.example/jobs'}, '2026-10-18T00:00:00+00:00')
    assert jobs[0].title == 'Product Manager, AI'
    assert len(jobs) == 10  # no per-source cap: every matching role is kept


def test_detail_pages_are_fetched_for_every_match_with_product_roles_first():
    import html
    import json
    titles = ['Project Manager'] * 8 + ['Product Manager']
    postings = [{'id':i, 'title':title, 'url':f'/companies/acme/jobs/{i}',
                 'location':'United States', 'companyName':'Acme', 'salaryRange':''}
                for i, title in enumerate(titles)]
    listing = '<div data-page="' + html.escape(json.dumps({'props':{'jobPostings':postings}}), quote=True) + '"></div>'
    detail = '<script type="application/ld+json">{"@type":"JobPosting","description":"Build products. This role is open to MBA students graduating in spring 2027."}</script>'
    seen = []
    def serve(request):
        seen.append(str(request.url))
        return httpx.Response(200, text=listing if 'jobs/role' in str(request.url) else detail)
    with httpx.Client(transport=httpx.MockTransport(serve)) as client:
        _, jobs, _ = source_probe.probe_source(client, {'id':'yc-product', 'kind':'yc',
            'url':'https://www.ycombinator.com/jobs/role/product-manager'}, '2026-10-18T00:00:00+00:00')
    assert jobs[0].title == 'Product Manager'
    assert any(url.endswith('/8') for url in seen)
    assert len(seen) == 10  # one listing plus a page for each of the nine matches
