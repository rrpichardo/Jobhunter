"""a16z portfolio board: search page -> each job's own page, read from semantic tags (no class names)."""

import httpx
import pytest

from jobhunter import postings as p
from scripts import source_probe as probe

STAMP = '2026-10-19T17:00:00+00:00'
ENTRY = {'id': 'a16z-product', 'kind': 'a16z', 'url': 'https://jobs.a16z.com/jobs?q=product%20manager'}

LISTING = ('<html><body><h2><a class="x" href="/jobs/stripe/8176254--product-manager-startup-products">Product Manager,  Startup Products</a></h2>'
           '<h2><a href="/jobs/acme-ai/1f473f3b-437d-4781-b0b4-83480f22c739--staff-engineer">Staff Engineer</a></h2>'
           '<a href="/jobs/stripe/8176254--product-manager-startup-products">again</a>'
           '<a href="/jobs/komodo">company page</a><a href="/jobs/komodo/99--empty"> </a></body></html>')
DETAIL = ('<html><head><script type="application/ld+json">{"@type":"BreadcrumbList","itemListElement":['
          '{"@type":"ListItem","position":1,"name":"All portfolio jobs"},{"@type":"ListItem","position":2,"name":"Stripe"},'
          '{"@type":"ListItem","position":3,"name":"Product Manager"}]}</script></head><body><nav>Sign in Portfolio Team</nav>'
          '<main><h1>Product Manager,  Startup Products</h1><dl><div><dt>Location</dt><dd>NYC, Chicago</dd></div>'
          '<div><dt>Compensation</dt><dd>USD 180,000–240,000 (Annual)</dd></div></dl><h2>About the role</h2>'
          '<span>Posted</span>   <span>Sep 11, 2026</span><p>Own the <b>startup</b> roadmap.</p></main><footer>Disclosures</footer></body></html>')


def test_listing_rows_use_link_text_dedupe_by_id_and_skip_non_job_links():
    stubs, rejected = p.stubs_a16z(LISTING, {'source_id': 'a16z-product'})
    assert [s['job_id'] for s in stubs] == ['a16z:stripe:8176254--product-manager-startup-products', 'a16z:acme-ai:1f473f3b-437d-4781-b0b4-83480f22c739--staff-engineer']
    assert stubs[0]['title'] == 'Product Manager, Startup Products' and stubs[0]['company'] == 'Stripe'
    assert stubs[0]['url'] == 'https://jobs.a16z.com/jobs/stripe/8176254--product-manager-startup-products'
    assert rejected == 1  # the link with no text


def test_a_page_with_no_job_links_is_a_layout_change_not_an_empty_board():
    with pytest.raises(ValueError, match='invalid_board_response'):
        p.stubs_a16z('<html><body>Something new</body></html>', {'source_id': 'a16z-product'})


def test_a_job_page_gives_company_place_pay_date_and_the_description_without_the_site_chrome():
    found = p.detail_a16z(DETAIL)
    assert found['company'] == 'Stripe' and found['location'] == 'NYC, Chicago'
    assert found['salary'] == 'USD 180,000–240,000 (Annual)' and found['posted_at'] == '2026-09-11T00:00:00+00:00'
    assert 'Own the startup roadmap.' in found['text'] and 'Sign in' not in found['text'] and 'Disclosures' not in found['text']


@pytest.mark.parametrize('page', ['<html><body><h1>x</h1></body></html>', '<html><body><h2>About the role</h2></body></html>'])
def test_a_job_page_in_a_new_layout_is_rejected(page):
    with pytest.raises(ValueError, match='invalid_board_response'):
        p.detail_a16z(page)


def test_the_source_delivers_the_matching_job_with_its_own_date():
    def handler(request):
        return httpx.Response(200, text=DETAIL if '--product-manager' in request.url.path else LISTING)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        source, jobs, note = probe.probe_source(client, ENTRY, STAMP, lookback_days=60)
    assert source['status'] == 'OK' and [j.job_id for j in jobs] == ['a16z:stripe:8176254--product-manager-startup-products']
    assert jobs[0].company == 'Stripe' and jobs[0].posted_at.startswith('2026-09-11') and 'outside_window=0' in note


def test_a_posting_older_than_the_window_is_dropped():
    def handler(request):
        return httpx.Response(200, text=DETAIL if '--product-manager' in request.url.path else LISTING)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        source, jobs, note = probe.probe_source(client, ENTRY, STAMP, lookback_days=3)
    assert jobs == [] and 'outside_window=1' in note


def test_the_registry_has_the_four_searches_and_no_listing_only_entry_for_a16z():
    import yaml
    registry = yaml.safe_load(open('sources/v0_sources.yaml'))
    assert {e['id'] for e in registry['detail_sources'] if e['kind'] == 'a16z'} == {
        'a16z-product', 'a16z-chief-of-staff', 'a16z-strategy', 'a16z-founder-in-residence'}
    assert all(e['kind'] != 'a16z' for e in registry['listing_only'])


def test_two_jobs_with_one_title_slug_are_two_jobs_and_a_mixed_case_id_is_read():
    listing = ('<a href="/jobs/revolut/chief-risk-officer--consider-nh78abc">Chief Risk Officer</a>'
               '<a href="/jobs/revolut/chief-risk-officer--consider-zz91def">Chief Risk Officer</a>'
               '<a href="/jobs/boltz/am9icG9zdDpwnBcz44i-P6UF_KHLuTfq--chief-of-staff">Chief of Staff</a>')
    stubs, rejected = p.stubs_a16z(listing, {'source_id': 'a16z-chief-of-staff'})
    assert len({s['job_id'] for s in stubs}) == 3 and rejected == 0
    assert all(__import__('re').fullmatch(r"[A-Za-z0-9][A-Za-z0-9:._~-]{0,300}", s['job_id']) for s in stubs)


def test_an_empty_search_that_says_so_is_zero_jobs_not_a_failed_source():
    assert p.stubs_a16z('<html><body><p>0 jobs</p><p>No roles match those filters.</p></body></html>', {'source_id': 'x'}) == ([], 0)


def test_the_description_starts_after_the_about_the_role_heading_and_the_fuller_location_wins():
    page = DETAIL.replace('<dt>Location</dt><dd>NYC, Chicago</dd></div>', '<dt>Location</dt><dd>NYC…</dd></div><div><dt>Location</dt><dd>NYC, Chicago, Seattle</dd>')
    found = p.detail_a16z(page)
    assert found['location'] == 'NYC, Chicago, Seattle' and not found['text'].startswith('Product Manager')


def test_the_same_job_found_by_two_searches_is_one_row():
    def mk(source):
        return p.Posting('a16z:acme:1--pm', source, 'Acme', 'Product Manager', 'Remote', 'text',
                         'https://jobs.a16z.com/jobs/acme/1--pm', STAMP)
    kept = p.dedupe([mk('a16z-product'), mk('a16z-strategy')])
    assert len(kept) == 1 and 'Also listed by: a16z-strategy' in kept[0][1]
