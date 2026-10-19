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


# ---- the fetcher over a fake session ----------------------------------------------------------------

class FakeSession:
    def __init__(self, pages):
        self.pages, self.urls, self.closed = list(pages), [], False

    def get(self, url):
        self.urls.append(url)
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
        def get(self, url):
            seen.append(json.loads(store.tables['_State'][1][1])['state'])
            return super().get(url)
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


def test_a_failure_to_start_the_browser_is_written_down_with_a_fixed_word(tmp_path, monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError('token=secret-li-at-value could not launch')
    monkeypatch.setitem(sys.modules, 'playwright', object())
    monkeypatch.setattr(li, 'BrowserSession', broken)
    code, out, store = run(tmp_path, None)
    payload = json.loads(out.read_text())
    assert code == 0 and payload['error'] == 'social_collector_error' and 'secret' not in out.read_text()
    assert rows(store)['allowance/linkedin-login/2026-10-19']['state'] == 'failed'


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
    assert 'li_at=secret-li-at-value' in seen['cookie'] and 'Headless' not in seen['agent'] and 'Chrome/' in seen['agent']
