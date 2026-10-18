"""Current user preferences, independent of the historical AI-only probe."""
from dataclasses import replace

import httpx
import pytest

from jobhunter import postings as p
from scripts import source_probe


def job(**changes):
    base = p.Posting('lever:acme:1', 'lever:acme', 'Acme', 'Product Manager',
                     'United States', 'Build billing products.', 'https://jobs.lever.co/acme/1',
                     '2026-10-18T00:00:00+00:00', salary='USD 140,000 annually')
    return replace(base, **changes)


@pytest.mark.parametrize('title', ['Product Manager, Billing', 'Senior Product Manager',
    'Group Product Manager', 'Product Lead', 'Chief of Staff', 'MBA Leadership Development Program',
    'Strategy Manager', 'Director of Strategy', 'Entrepreneur in Residence', 'Project Manager'])
def test_non_ai_role_families_are_collection_candidates(title):
    assert p.collection_match(job(title=title))


@pytest.mark.parametrize('title', ['Software Engineer', 'Product Marketing Manager', 'Program Manager',
    'Project Manager Intern', 'Summer Associate, Strategy', 'Product Designer', 'Strategy Analyst'])
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
             'descriptionPlain': 'Build billing products.', 'hostedUrl': f'https://jobs.lever.co/acme/{i}'}
            for i, title in enumerate(['Product Manager', 'Chief of Staff', 'Project Manager', 'Engineer'])]
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=data)))
    entry = {'id': 'lever:acme', 'kind': 'lever', 'board': 'acme', 'company': 'Acme', 'url': 'https://test.example/jobs'}
    record, jobs, _ = source_probe.probe_source(client, entry, '2026-10-18T00:00:00+00:00')
    assert [item.title for item in jobs] == ['Product Manager', 'Chief of Staff', 'Project Manager']
    assert record['pm_candidates'] == 3 and record['selected_for_m0'] == 3


@pytest.mark.parametrize('location', ['Bogotá, CO', 'Medellín, CO', 'Santo Domingo, DO'])
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


def test_mixed_us_latam_location_retained_without_assuming_which_floor_applies():
    candidate = job(location='Remote (US or Colombia)', salary='USD 90,000 annually')
    assert p.collection_match(candidate)
    assert p.salary_preference(candidate)[0] == 'unresolved'


def test_unresolved_salary_check_is_in_details_not_next_step():
    row = p.to_row(job(salary=''))
    assert row['Next step'] == ''
    assert 'Check first:' in row['More details']


def test_board_caps_prioritize_product_roles_over_adjacent_roles():
    titles = ['Project Manager'] * 8 + ['Chief of Staff', 'Product Manager, AI']
    data = [{'id': str(i), 'text': title, 'categories': {'location': 'United States'},
             'descriptionPlain': 'Build products.', 'hostedUrl': f'https://jobs.lever.co/acme/{i}'}
            for i, title in enumerate(titles)]
    with httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(200, json=data))) as client:
        _, jobs, _ = source_probe.probe_source(client, {'id':'lever:acme', 'kind':'lever',
            'board':'acme', 'company':'Acme', 'url':'https://test.example/jobs'}, '2026-10-18T00:00:00+00:00')
    assert jobs[0].title == 'Product Manager, AI'
    assert len(jobs) == 8
