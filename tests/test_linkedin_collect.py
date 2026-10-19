"""LinkedIn hiring-post collector: card reader, search handling, allowance order and cookie handling, all offline.
The browser class is exercised against the real Chromium when the optional `social` extra is installed."""

from datetime import datetime, timedelta, timezone
import hashlib
import json
import sys

import pytest

from jobhunter import linkedin_cards as lc
from jobhunter import social_collect as sc
from scripts import ai_queue as queue_cli
from scripts import linkedin_collect as li
from scripts import social_posts
from sheet_fakes import MemoryStore

NOW = '2026-10-19T16:00:00+00:00'
COOKIES = {'LINKEDIN_LI_AT': 'secret-li-at-value'}
WHEN = datetime(2026, 10, 15, 12, tzinfo=timezone.utc)


def post_id(when=WHEN, low=5):
    return str((int(when.timestamp() * 1000) << 22) | low)


def card(number, when=WHEN, *, text='Acme is hiring a Senior Product Manager, AI (Remote US).', style='href'):
    pid = post_id(when, number)
    reference = (f'<a href="/feed/update/urn:li:activity:{pid}/?utm_source=share">3d</a>' if style == 'href'
                 else f'<span data-urn="urn:li:activity:{pid}"></span>')
    return pid, (f'<li><div><a href="/company/acme/"><span>Acme Inc • 2nd</span></a>{reference}'
                 f'<p>{text}</p><a href="https://acme.example/jobs/pm?x=1">Apply</a>'
                 '<button>Like</button><button>Comment</button><button>Repost</button></div></li>')


def page(*cards, extra=''):
    return f'<html><body><nav>Home My Network Jobs</nav><main><ul>{"".join(cards)}</ul>{extra}</main></body></html>'


# ---- the card reader ------------------------------------------------------------------------------

def test_cards_are_found_by_post_id_with_author_links_text_and_a_date_from_the_id():
    first, one = card(1)
    second, two = card(2, WHEN + timedelta(days=1), text='Beta needs a Chief of Staff.', style='data')
    cards, stats = lc.extract_post_cards(page(one, two))
    assert [c['id'] for c in cards] == [first, second] and stats['cards'] == 2 and stats['post_ids'] == 2
    one_card = cards[0]
    assert one_card['url'] == f'https://www.linkedin.com/feed/update/urn:li:activity:{first}/'
    assert one_card['author'] == 'Acme Inc' and one_card['links'] == ['https://acme.example/jobs/pm?x=1']
    assert one_card['created_at'].date().isoformat() == '2026-10-15' and cards[1]['created_at'].date().isoformat() == '2026-10-16'
    assert 'Senior Product Manager' in one_card['text']
    assert 'Like' not in one_card['text'].splitlines() and 'Home My Network' not in one_card['text']


def test_a_single_result_does_not_swallow_the_whole_page():
    _, one = card(1)
    cards, _ = lc.extract_post_cards(page(one, extra='<footer>Cookie policy About Help Center</footer>'))
    assert len(cards) == 1 and 'Cookie policy' not in cards[0]['text'] and 'Home My Network' not in cards[0]['text']


def test_an_id_without_a_believable_date_is_counted_not_kept():
    html = page('<li><a href="/feed/update/urn:li:activity:12345678901/">x</a><p>old text</p></li>')
    cards, stats = lc.extract_post_cards(html)
    assert cards == [] and stats['undated'] == 1 and stats['post_ids'] == 1


def test_the_no_results_notice_is_recognised_and_empty_pages_have_no_cards():
    cards, stats = lc.extract_post_cards('<html><body><main><h2>No results found</h2></main></body></html>')
    assert cards == [] and stats['no_results'] and stats['post_ids'] == 0


def test_the_posts_link_form_is_read_too():
    pid = post_id(WHEN, 9)
    html = page(f'<li><a href="https://www.linkedin.com/posts/jane-doe_hiring-activity-{pid}-AbCd">post</a><p>text here</p></li>')
    cards, _ = lc.extract_post_cards(html)
    assert [c['id'] for c in cards] == [pid]


def test_a_single_result_is_not_grown_into_the_search_form_or_headings():
    _, one = card(1)
    html = ('<html><body><main><div><form><input placeholder="Search"></form><h1>Search results</h1>'
            f'<div>{one}</div></div></main></body></html>')
    cards, _ = lc.extract_post_cards(html)
    assert len(cards) == 1 and 'Search results' not in cards[0]['text'] and 'Search' not in cards[0]['text']


def test_a_suggested_post_nested_inside_a_card_is_left_out_of_it_and_does_not_shrink_it():
    first, _ = card(1)
    second = post_id(WHEN + timedelta(days=2), 7)
    html = page(f'<li><div data-urn="urn:li:activity:{first}"><a href="/in/jane/">Jane Doe</a><p>Hiring a PM now.</p>'
                f'<div><span>Suggested for you</span><div data-urn="urn:li:activity:{second}"><p>Unrelated post text</p></div>'
                f'</div></div></li>')
    cards, _ = lc.extract_post_cards(html)
    by_id = {c['id']: c for c in cards}
    assert 'Hiring a PM now.' in by_id[first]['text'] and 'Unrelated' not in by_id[first]['text']
    assert 'Unrelated post text' in by_id[second]['text']


def test_ids_in_side_panels_the_page_head_and_scripts_are_not_results():
    pid = post_id(WHEN, 3)
    html = (f'<html><head><link rel="canonical" href="https://www.linkedin.com/feed/update/urn:li:activity:{pid}/"></head>'
            f'<body><aside><a href="/feed/update/urn:li:activity:{pid}/">People also viewed</a></aside>'
            f'<script>{{"urn":"urn:li:activity:{pid}"}}</script><main><h2>No results found</h2></main></body></html>')
    cards, stats = lc.extract_post_cards(html)
    assert cards == [] and stats['post_ids'] == 0 and stats['no_results'] and stats['script_ids'] == 1


def test_a_page_that_says_no_results_has_no_cards_even_with_a_stray_link():
    _, one = card(1)
    cards, stats = lc.extract_post_cards(page(one, extra='<h2>No results found</h2>'))
    assert cards == [] and stats['no_results']


def test_percent_encoded_ids_are_read():
    pid = post_id(WHEN, 4)
    cards, _ = lc.extract_post_cards(page(f'<li><a href="/feed/update/urn%3Ali%3Aactivity%3A{pid}/">3d</a><p>Hiring a PM</p><p>x</p></li>'))
    assert [c['id'] for c in cards] == [pid]


def test_author_is_a_real_name_never_a_slug_and_outside_links_are_unwrapped_and_linkedin_hosts_excluded():
    pid = post_id(WHEN, 5)
    html = page(f'<li><a href="https://de.linkedin.com/in/jane-doe-4a5b6c/"><img alt="avatar"></a>'
                f'<a href="https://de.linkedin.com/in/jane-doe-4a5b6c/">Jane Doe Jane Doe</a>'
                f'<a href="/feed/update/urn:li:activity:{pid}/">3d</a><p>We are hiring a Product Manager.</p>'
                '<a href="https://media.licdn.com/dms/image/x.png">pic</a><a href="https://help.linkedin.com/x">help</a>'
                '<a href="https://www.linkedin.com/redir/redirect?url=https%3A%2F%2Facme.example%2Fjobs%2Fpm&amp;urlhash=abc">Apply</a></li>')
    card_ = lc.extract_post_cards(html)[0][0]
    assert card_['author'] == 'Jane Doe' and card_['links'] == ['https://acme.example/jobs/pm']


# ---- the fetcher over a fake session ----------------------------------------------------------------

class FakeSession:
    def __init__(self, pages):
        self.pages, self.urls, self.closed = list(pages), [], False

    def get(self, url, **options):
        self.urls.append(url)
        self.options = options
        return self.pages[min(len(self.urls), len(self.pages)) - 1]

    def close(self):
        self.closed = True


def ok(*cards, url='https://www.linkedin.com/search/results/content/?keywords=x'):
    return li.Page(url, 200, page(*cards) if cards else page(extra='<h2>No results found</h2>'))


def fetcher(*pages, since='2026-09-21'):
    return li.LinkedInFetcher(FakeSession(pages), since_day=since)


def test_a_search_returns_posts_in_the_window_and_drops_older_ones():
    old, old_html = card(3, WHEN - timedelta(days=60))
    _, new_html = card(4)
    posts = fetcher(ok(old_html, new_html)).search('q', 10)
    assert len(posts) == 1 and posts[0]['created_at'].startswith('2026-10-15')


def test_the_post_limit_is_enforced():
    cards = [card(n, WHEN + timedelta(hours=n))[1] for n in range(1, 6)]
    assert len(fetcher(ok(*cards)).search('q', 3)) == 3


@pytest.mark.parametrize('result,expected', [
    (li.Page('https://www.linkedin.com/login?session_redirect=x', 200, '<html></html>'), sc.FetchBlocked),
    (li.Page('https://www.linkedin.com/authwall?trk=x', 200, '<html></html>'), sc.FetchBlocked),
    (li.Page('https://www.linkedin.com/checkpoint/challenge/x', 200, '<html></html>'), sc.FetchBlocked),
    (li.Page('https://www.linkedin.com/search/results/content/', 999, ''), sc.FetchBlocked),
    (li.Page('https://www.linkedin.com/search/results/content/', 403, ''), sc.FetchBlocked),
    (li.Page('https://www.linkedin.com/search/results/content/', 429, ''), sc.FetchRateLimited),
    (li.Page('https://www.linkedin.com/search/results/content/', 500, ''), RuntimeError),
    (li.Page('https://www.linkedin.com/search/results/content/', 200, '<html><body>something new</body></html>'), RuntimeError),
])
def test_walls_and_errors_map_to_fixed_failures(result, expected):
    with pytest.raises(expected):
        fetcher(result).search('q', 5)


def test_ids_that_cannot_be_read_are_a_failure_not_a_healthy_zero():
    html = page('<li><a href="/feed/update/urn:li:activity:12345678901/">3d</a><p>old</p></li>')  # no believable date
    with pytest.raises(RuntimeError, match='layout_not_recognised'):
        fetcher(li.Page('https://www.linkedin.com/search/results/content/', 200, html)).search('q', 5)


def test_a_page_where_every_card_is_a_stub_is_a_failure():
    pid = post_id(WHEN, 6)
    html = page(f'<li><a href="/feed/update/urn:li:activity:{pid}/">3d</a></li>')
    with pytest.raises(RuntimeError, match='layout_not_recognised'):
        fetcher(li.Page('https://www.linkedin.com/search/results/content/', 200, html)).search('q', 5)


def test_a_sign_in_form_on_the_results_page_is_a_login_failure():
    html = '<html><body><main><form><input type="password"></form></main></body></html>'
    with pytest.raises(sc.FetchBlocked):
        fetcher(li.Page('https://www.linkedin.com/search/results/content/', 200, html)).search('q', 5)


def test_a_browser_error_leaves_a_fixed_record_and_a_redirect_loop_means_a_stale_login():
    class Failing:
        def __init__(self, error):
            self.error = error

        def get(self, url, **options):
            raise self.error
    f = li.LinkedInFetcher(Failing(RuntimeError('net::ERR_TOO_MANY_REDIRECTS at https://www.linkedin.com/?token=secret')), since_day='2026-09-21')
    with pytest.raises(sc.FetchBlocked):
        f.search('q', 5)
    assert f.diagnostics[0]['error'] == 'redirect_loop' and 'secret' not in json.dumps(f.diagnostics)
    g = li.LinkedInFetcher(Failing(RuntimeError('something else with secret')), since_day='2026-09-21')
    with pytest.raises(RuntimeError, match='browser_error'):
        g.search('q', 5)
    assert g.diagnostics[0]['error'] == 'browser_error' and 'secret' not in json.dumps(g.diagnostics)


def test_the_diagnostic_path_keeps_only_the_first_segment():
    f = fetcher(li.Page('https://www.linkedin.com/checkpoint/challenge/AgEsecrettoken123', 200, '<html></html>'))
    with pytest.raises(sc.FetchBlocked):
        f.search('q', 5)
    assert f.diagnostics[0]['path'] == '/checkpoint' and 'secret' not in json.dumps(f.diagnostics)


def test_a_page_that_says_no_results_is_a_genuine_zero():
    empty = li.Page('https://www.linkedin.com/search/results/content/', 200,
                    '<html><body><main><h2>No results found</h2></main></body></html>')
    assert fetcher(empty).search('q', 5) == []


def test_each_search_leaves_a_fixed_shape_record_without_query_or_page_text():
    f = fetcher(ok(card(1)[1]))
    f.search('hiring "secret query"', 5)
    record = f.diagnostics[0]
    assert record['status'] == 200 and record['cards'] == 1 and 'secret' not in json.dumps(record)


def test_the_search_url_carries_the_query_and_the_date_filter_only():
    session = FakeSession([ok()])
    li.LinkedInFetcher(session, since_day='2026-10-01', recent='past-week').search('hiring "chief of staff"', 5)
    assert session.urls[0].startswith('https://www.linkedin.com/search/results/content/?keywords=hiring%20%22chief%20of%20staff%22')
    assert 'past-week' in session.urls[0] and li.recent_filter(1) == 'past-24h' and li.recent_filter(3) == 'past-week' and li.recent_filter(28) == 'past-month'


# ---- the run ------------------------------------------------------------------------------------------

def run(tmp_path, f, *, environ=COOKIES, store=None, extra=()):
    out = tmp_path.parent / (tmp_path.name + '_li.json')
    store = MemoryStore() if store is None else store
    code = li.main(['--run-id', 'r1', '--output', str(out), *extra], store=store, fetcher=f, environ=environ,
                   now=lambda: NOW, sleep=lambda s: None, rng=lambda: 0.5)
    return code, out, store


def rows(store):
    return {row[0]: json.loads(row[1]) for row in store.tables['_State'][1:]}


def test_a_run_reserves_the_day_first_writes_candidates_and_closes_the_day(tmp_path, capsys):
    f = fetcher(ok(card(1)[1]), ok(), ok(), ok(), ok())
    code, out, store = run(tmp_path, f)
    payload = json.loads(out.read_text())
    text = capsys.readouterr().out
    assert code == 0 and len(payload['candidates']) == 1 and payload['candidates'][0]['item_id']
    assert payload['stats']['queries_run'] == 5 and len(payload['stats']['searches']) == 5
    assert rows(store)['allowance/linkedin-login/2026-10-19']['state'] == 'ok' and f.session.closed
    assert 'secret' not in text and 'secret' not in out.read_text()


def test_the_allowance_is_reserved_before_the_first_request(tmp_path):
    seen = []
    store = MemoryStore()

    class Spy(FakeSession):
        def get(self, url, **options):
            seen.append(json.loads(store.tables['_State'][1][1])['state'])
            return super().get(url, **options)
    run(tmp_path, li.LinkedInFetcher(Spy([ok()]), since_day='2026-09-21'), store=store)
    assert seen and seen[0] == 'reserved'


def test_a_wall_on_the_first_search_stops_the_run_records_blocked_and_spends_the_day(tmp_path):
    wall = li.Page('https://www.linkedin.com/login', 200, '')
    f = fetcher(wall)
    code, out, store = run(tmp_path, f)
    payload = json.loads(out.read_text())
    assert code == 0 and payload['error'] == 'social_login_failed' and len(f.session.urls) == 1
    assert rows(store)['allowance/linkedin-login/2026-10-19']['state'] == 'blocked'


def test_a_spent_day_collects_nothing_and_exits_three(tmp_path, capsys):
    store = MemoryStore()
    assert run(tmp_path, fetcher(ok()), store=store)[0] == 0
    f2 = fetcher(ok())
    code, out, _ = run(tmp_path.parent / (tmp_path.name + 'b'), f2, store=store)
    assert code == 3 and f2.session.urls == [] and 'allowance_spent' in capsys.readouterr().out


@pytest.mark.parametrize('environ', [{}, {'LINKEDIN_LI_AT': ''}])
def test_missing_cookie_spends_nothing_and_prints_the_name_only(tmp_path, capsys, environ):
    f = fetcher(ok())
    code, out, store = run(tmp_path, f, environ=environ)
    assert code == 4 and '_State' not in store.tables and f.session.urls == []
    text = capsys.readouterr().out
    assert 'LINKEDIN_LI_AT' in text and 'secret' not in text


def test_the_shorter_cookie_name_also_works(tmp_path):
    code, _, _ = run(tmp_path, fetcher(ok()), environ={'LI_AT': 'secret-li-at-value'})
    assert code == 0


def test_a_missing_browser_library_asks_for_setup_and_spends_nothing(tmp_path, monkeypatch, capsys):
    monkeypatch.delitem(sys.modules, 'playwright', raising=False)
    monkeypatch.setattr(li.importlib.util, 'find_spec', lambda name: None)
    store = MemoryStore()
    out = tmp_path.parent / (tmp_path.name + '_li.json')
    code = li.main(['--run-id', 'r1', '--output', str(out)], store=store, environ=COOKIES, now=lambda: NOW)
    assert code == 4 and 'social extra' in capsys.readouterr().out and '_State' not in store.tables


def test_a_browser_that_cannot_start_spends_nothing_and_leaks_nothing(tmp_path, monkeypatch, capsys):
    def broken(*args, **kwargs):
        raise RuntimeError('token=secret-li-at-value could not launch')
    monkeypatch.setitem(sys.modules, 'playwright', object())
    monkeypatch.setattr(li, 'BrowserSession', broken)
    code, out, store = run(tmp_path, None)
    text = capsys.readouterr().out
    assert code == 4 and '_State' not in store.tables and not out.exists()
    assert 'secret' not in text and 'no allowance was spent' in text


def test_a_cookie_pasted_with_a_newline_quotes_or_spaces_is_cleaned_before_it_reaches_the_browser(tmp_path, monkeypatch):
    received = []

    class Spy:
        def __init__(self, value, rng=None):
            received.append(value)
            self.diagnostics = []

        def search(self, query, limit):
            return []

        def close(self):
            pass
    monkeypatch.setitem(sys.modules, 'playwright', object())
    monkeypatch.setattr(li, 'BrowserSession', Spy)
    monkeypatch.setattr(li, 'LinkedInFetcher', lambda session, **kwargs: session)
    code, _, _ = run(tmp_path, None, environ={'LINKEDIN_LI_AT': '  "abc123"\n'})
    assert code == 0 and received == ['abc123']


def test_a_blank_cookie_counts_as_not_set(tmp_path, capsys):
    code, _, store = run(tmp_path, fetcher(ok()), environ={'LINKEDIN_LI_AT': ' \n'})
    assert code == 4 and '_State' not in store.tables


def test_a_doomed_output_path_spends_no_allowance(tmp_path):
    existing = tmp_path.parent / (tmp_path.name + '_li.json')
    existing.write_text('keep')
    store = MemoryStore()
    code = li.main(['--run-id', 'r1', '--output', str(existing)], store=store, fetcher=fetcher(ok()), environ=COOKIES,
                   now=lambda: NOW, sleep=lambda s: None)
    assert code == 2 and '_State' not in store.tables and existing.read_text() == 'keep'


def test_the_queries_in_the_registry_respect_the_limit_and_name_collected_roles():
    from jobhunter.postings import ROLE_TEXT, role_family
    import re
    queries = sc.load_queries('sources/social_queries.yaml', li.SOURCE)
    assert 1 <= len(queries) <= sc.LIMITS[li.SOURCE]['post_searches']
    for query in queries:
        phrases = re.findall(r'"([^"]+)"', query)
        assert phrases and all(ROLE_TEXT.search(p) and role_family(p) for p in phrases), query


def test_the_candidate_file_flows_through_the_queue_and_the_validator(tmp_path, capsys):
    code, out, _ = run(tmp_path, fetcher(ok(card(1)[1]), ok(), ok(), ok(), ok()))
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    work = tmp_path.parent / (tmp_path.name + '_work.json')
    assert queue_cli.main(['pull', '--source', 'linkedin-login', '--candidates', str(out), '--candidates-sha256', digest,
                           '--output', str(work), '--id-field', 'item_id'], store=MemoryStore()) == 0
    work_data = json.loads(work.read_text())
    item = work_data['candidates'][0]
    assert item['url'].startswith('https://www.linkedin.com/feed/update/urn:li:activity:') and item['author'] == 'Acme Inc'


# ---- the real browser (only when the optional extra and its Chromium are installed) -----------------------

def test_the_browser_session_loads_scrolls_expands_and_returns_the_page_with_the_cookie_only_in_memory():
    pytest.importorskip('playwright')
    pid, one = card(1, text='Acme is hiring a Product Manager <button>…more</button>')
    html = page(one)
    try:
        session = li.BrowserSession('secret-li-at-value', rng=lambda: 0)
    except Exception as exc:  # noqa: BLE001 - no Chromium available here
        pytest.skip(f'browser unavailable: {type(exc).__name__}')
    try:
        seen = {}

        def answer(route):
            seen['cookie'] = route.request.headers.get('cookie', '')
            seen['agent'] = route.request.headers.get('user-agent', '')
            route.fulfill(status=200, content_type='text/html', body=html)
        session._context.route('**/*', answer)
        result = session.get('https://www.linkedin.com/search/results/content/?keywords=x')
    finally:
        session.close()
    cards, _ = lc.extract_post_cards(result.html)
    assert result.status == 200 and [c['id'] for c in cards] == [pid]
    assert 'li_at=secret-li-at-value' in seen['cookie'] and result.ready  # the page had a result, so no 25 s wait ran out


# ---- job listings (same session, same single allowance) ---------------------------------------------------

def job(number, *, title='Senior Product Manager, AI', age='3 days ago', style='href', extra=''):
    ident = 3900000000 + number
    ref = (f'<a href="/jobs/view/{ident}/?trackingId=abc&currentJobId={ident}">{title}</a>' if style == 'href'
           else f'<div data-occludable-job-id="{ident}"><span>{title}</span></div>')
    return ident, (f'<li>{ref}<span>{title} with verification</span><span>Acme Corp</span>'
                   f'<span>San Francisco, CA (Hybrid)</span><span>$180K/yr - $240K/yr</span><span>{age}</span>'
                   f'<button>Easy Apply</button>{extra}</li>')


def jobs_page(*cards):
    return li.Page('https://www.linkedin.com/jobs/search/?keywords=x', 200,
                   f'<html><body><nav>Jobs Messaging</nav><main><ul>{"".join(cards)}</ul></main></body></html>')


def test_job_cards_are_found_by_job_id_with_their_own_text_and_age():
    first, one = job(1)
    second, two = job(2, title='Chief of Staff', age='2 weeks ago', style='attr')
    cards, stats = lc.extract_job_cards(jobs_page(one, two).html)
    assert [c['id'] for c in cards] == [str(first), str(second)]
    assert (stats['job_ids'], stats['cards'], stats['empty'], stats['short_cards']) == (2, 2, 0, 0)
    assert cards[0]['url'] == f'https://www.linkedin.com/jobs/view/{first}/' and cards[0]['age_days'] == 3
    assert cards[1]['age_days'] == 14 and 'Acme Corp' in cards[0]['text'] and 'Jobs Messaging' not in cards[0]['text']


def test_a_job_search_keeps_cards_inside_the_window_and_those_with_no_readable_age():
    cards = [job(1)[1], job(2, age='3 months ago')[1], job(3, age='Actively recruiting')[1]]
    f = li.LinkedInFetcher(FakeSession([jobs_page(*cards)]), since_day='2026-09-21',
                           captured=datetime(2026, 10, 19, 16, tzinfo=timezone.utc))
    found = f.search_jobs('q', 10)
    assert [j['url'][-11:-1] for j in found] == ['3900000001', '3900000003']
    assert found[0]['created_at'].startswith('2026-10-16') and found[1]['created_at'].startswith('2026-10-19')
    assert f.diagnostics[0]['outside_window'] == 1 and f.diagnostics[0]['undated'] == 1 and f.diagnostics[0]['kind'] == 'jobs'
    assert f.session.options['expand'] is False and 'jobs/view' in f.session.options['ready']


@pytest.mark.parametrize('page,expected', [
    (li.Page('https://www.linkedin.com/checkpoint/challenge/x', 200, ''), sc.FetchBlocked),
    (li.Page('https://www.linkedin.com/jobs/search/', 429, ''), sc.FetchRateLimited),
    (li.Page('https://www.linkedin.com/jobs/search/', 200, '<html><body>something new</body></html>'), RuntimeError)])
def test_job_search_walls_map_to_fixed_failures(page, expected):
    with pytest.raises(expected):
        li.LinkedInFetcher(FakeSession([page]), since_day='2026-09-21').search_jobs('q', 5)


def test_a_job_page_that_says_no_jobs_found_is_a_genuine_zero():
    empty = li.Page('https://www.linkedin.com/jobs/search/', 200, '<html><body><main><h2>No matching jobs found</h2></main></body></html>')
    assert li.LinkedInFetcher(FakeSession([empty]), since_day='2026-09-21').search_jobs('q', 5) == []


def run_both(tmp_path, f, *, store=None):
    out = tmp_path.parent / (tmp_path.name + '_li.json')
    jobs = tmp_path.parent / (tmp_path.name + '_jobs.json')
    store = MemoryStore() if store is None else store
    code = li.main(['--run-id', 'r1', '--output', str(out), '--jobs-output', str(jobs)], store=store, fetcher=f,
                   environ=COOKIES, now=lambda: NOW, sleep=lambda s: None, rng=lambda: 0.5)
    return code, out, jobs, store


def test_one_session_and_one_allowance_cover_posts_and_jobs(tmp_path, capsys):
    post_pages = [ok(card(1)[1])] + [ok()] * 4
    job_pages = [jobs_page(job(n)[1]) for n in range(1, 6)]
    f = li.LinkedInFetcher(FakeSession(post_pages + job_pages), since_day='2026-09-21',
                           captured=datetime(2026, 10, 19, 16, tzinfo=timezone.utc))
    code, out, jobs, store = run_both(tmp_path, f)
    posts_payload, jobs_payload = json.loads(out.read_text()), json.loads(jobs.read_text())
    text = capsys.readouterr().out
    assert code == 0 and len(posts_payload['candidates']) == 1 and len(jobs_payload['candidates']) == 5
    assert jobs_payload['source_id'] == 'linkedin-jobs' and jobs_payload['stats']['queries_run'] == 5
    assert [r['kind'] for r in jobs_payload['stats']['searches']] == ['jobs'] * 5
    assert [r['kind'] for r in posts_payload['stats']['searches']] == ['posts'] * 5
    assert len([k for k in rows(store) if k.startswith('allowance/')]) == 1  # one reservation for the whole session
    assert rows(store)['allowance/linkedin-login/2026-10-19']['state'] == 'ok' and 'secret' not in text + jobs.read_text()
    assert 'linkedin_jobs_candidates_sha256=' in text and f.session.closed


def test_a_refused_post_search_skips_the_job_searches_and_records_the_same_word_for_both(tmp_path):
    wall = li.Page('https://www.linkedin.com/login', 200, '')
    f = li.LinkedInFetcher(FakeSession([wall]), since_day='2026-09-21')
    code, out, jobs, store = run_both(tmp_path, f)
    assert code == 0 and len(f.session.urls) == 1  # the job pages were never requested
    assert json.loads(out.read_text())['error'] == json.loads(jobs.read_text())['error'] == 'social_login_failed'
    assert rows(store)['allowance/linkedin-login/2026-10-19']['state'] == 'blocked'


def test_a_browser_that_cannot_start_spends_nothing_for_either_file(tmp_path, monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError('token=secret-li-at-value')
    monkeypatch.setitem(sys.modules, 'playwright', object())
    monkeypatch.setattr(li, 'BrowserSession', broken)
    code, out, jobs, store = run_both(tmp_path, None)
    assert code == 4 and '_State' not in store.tables and not out.exists() and not jobs.exists()


def test_the_two_output_files_must_differ_and_a_doomed_jobs_path_spends_nothing(tmp_path):
    store = MemoryStore()
    same = tmp_path.parent / (tmp_path.name + '_same.json')
    assert li.main(['--run-id', 'r1', '--output', str(same), '--jobs-output', str(same)], store=store, fetcher=fetcher(ok()),
                   environ=COOKIES, now=lambda: NOW) == 2 and '_State' not in store.tables
    existing = tmp_path.parent / (tmp_path.name + '_exists.json')
    existing.write_text('keep')
    assert li.main(['--run-id', 'r1', '--output', str(tmp_path.parent / (tmp_path.name + '_new.json')),
                    '--jobs-output', str(existing)], store=store, fetcher=fetcher(ok()), environ=COOKIES,
                   now=lambda: NOW) == 2 and '_State' not in store.tables


def test_the_job_queries_respect_the_limit_and_each_names_a_collected_role():
    from jobhunter.postings import role_family
    queries = sc.load_queries('sources/social_queries.yaml', li.JOBS_QUERY_KEY, limit=sc.LIMITS[li.SOURCE]['job_searches'])
    assert 1 <= len(queries) <= 5 and all(role_family(q) for q in queries), queries


def test_a_job_card_flows_through_the_queue_and_the_validator_into_a_lead(tmp_path, capsys):
    ident, one = job(1)
    f = li.LinkedInFetcher(FakeSession([ok()] * 5 + [jobs_page(one)] + [jobs_page()] * 4), since_day='2026-09-21',
                           captured=datetime(2026, 10, 19, 16, tzinfo=timezone.utc))
    f.session.pages[5:] = [jobs_page(one)] + [li.Page('https://www.linkedin.com/jobs/search/', 200,
                                                    '<html><body><main>No jobs found</main></body></html>')] * 4
    code, out, jobs, store = run_both(tmp_path, f)
    digest = hashlib.sha256(jobs.read_bytes()).hexdigest()
    work = tmp_path.parent / (tmp_path.name + '_work.json')
    assert queue_cli.main(['pull', '--source', 'linkedin-jobs', '--candidates', str(jobs), '--candidates-sha256', digest,
                           '--output', str(work), '--id-field', 'item_id'], store=MemoryStore()) == 0
    work_digest = capsys.readouterr().out.split('work_sha256=')[1].split()[0]
    item = json.loads(work.read_text())['candidates'][0]
    assert item['item_id'] == str(ident) and item['created_at'].startswith('2026-10-16')
    facts = tmp_path.parent / (tmp_path.name + '_facts.json')
    facts.write_text(json.dumps({'processed': [str(ident)], 'facts': [{
        'item_id': str(ident), 'title': 'Senior Product Manager, AI', 'company': 'Acme Corp',
        'location': 'San Francisco, CA (Hybrid)', 'salary': '$180K/yr - $240K/yr',
        'description_quote': 'Acme Corp', 'apply_url': ''}]}))
    result = tmp_path.parent / (tmp_path.name + '_result.json')
    assert social_posts.main(['validate', '--source', 'linkedin-jobs', '--candidates', str(work), '--candidates-sha256',
                              work_digest, '--extractions', str(facts), '--output', str(result)]) == 0
    posting = json.loads(result.read_text())['postings'][0]
    assert posting['job_id'].startswith(f'linkedin-job:{ident}:') and posting['apply_url'] == f'https://www.linkedin.com/jobs/view/{ident}/'
