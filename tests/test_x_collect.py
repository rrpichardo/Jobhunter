"""X hiring-post collector: limits, allowance order, cookie handling and the twscrape adapter, all offline."""

import json
import sys
import types

import pytest

from jobhunter import allowance as allowance_module
from jobhunter import social_collect as sc
from scripts import ai_queue as queue_cli
from scripts import social_posts
from scripts import x_collect as x
from sheet_fakes import MemoryStore

NOW = '2026-10-19T16:00:00+00:00'
COOKIES = {'X_AUTH_TOKEN': 'secret-auth-token-value', 'X_CT0': 'secret-ct0-value'}


def post(number, text='Acme is hiring a Senior Product Manager, AI (Remote US). Apply: https://acme.example/jobs/pm'):
    return {'url': f'https://x.com/acme/status/{1850000000000000000 + number}',
            'created_at': '2026-10-15T12:00:00+00:00', 'text': text, 'links': ['https://acme.example/jobs/pm']}


class FakeFetcher:
    def __init__(self, pages=None, fail=None):
        self.pages, self.fail, self.calls, self.closed = pages or {}, fail, [], False

    def search(self, query, limit):
        self.calls.append((query, limit))
        if self.fail and len(self.calls) == self.fail[0]:
            raise self.fail[1]
        return self.pages.get(len(self.calls), [])[:limit]

    def close(self):
        self.closed = True


def run(tmp_path, fetcher, *, store=None, environ=COOKIES, extra=()):
    out = tmp_path.parent / (tmp_path.name + '_x.json')
    store = MemoryStore() if store is None else store
    code = x.main(['--run-id', 'r1', '--output', str(out), *extra], store=store, fetcher=fetcher,
                  environ=environ, now=lambda: NOW, sleep=lambda s: None, rng=lambda: 0.5)
    return code, out, store


def rows(store):
    return {row[0]: json.loads(row[1]) for row in store.tables['_State'][1:]}


def test_every_search_names_a_role_the_delivery_filter_collects():
    import re
    from jobhunter.postings import ROLE_TEXT, role_family
    for query in sc.load_queries('sources/social_queries.yaml', 'x-twscrape'):
        phrases = re.findall(r'"([^"]+)"', query)
        assert phrases and any(ROLE_TEXT.search(phrase) for phrase in phrases), query
        assert any(role_family(phrase) for phrase in phrases), query  # and a title like it is really delivered


def test_the_registry_queries_load_and_respect_the_query_limit():
    queries = sc.load_queries('sources/social_queries.yaml', 'x-twscrape')
    assert 1 <= len(queries) <= sc.LIMITS['x-twscrape']['queries']


@pytest.mark.parametrize('bad', ['x', 'hiring; rm -rf /', 'a' * 201, 'line\nbreak', '$(whoami) hiring'])
def test_unsafe_queries_are_refused(tmp_path, bad):
    path = tmp_path / 'q.yaml'
    path.write_text(json.dumps({'x-twscrape': [bad]}))
    with pytest.raises(ValueError, match='invalid_social_queries'):
        sc.load_queries(path, 'x-twscrape')


def test_a_run_reserves_the_day_first_searches_writes_candidates_and_closes_the_day(tmp_path, capsys):
    fetcher = FakeFetcher({1: [post(1), post(2)], 2: [post(2), post(3)]})
    code, out, store = run(tmp_path, fetcher)
    assert code == 0 and fetcher.closed
    payload = json.loads(out.read_text())
    assert payload['source_id'] == 'x-twscrape' and payload['error'] == ''
    assert [c['url'][-1] for c in payload['candidates']] == ['1', '2', '3']  # the repeat of post 2 is dropped
    assert payload['stats']['queries_run'] == len(sc.load_queries('sources/social_queries.yaml', 'x-twscrape'))
    assert all('since:2026-09-21' in q and q.endswith('-filter:replies') for q, _ in fetcher.calls)
    assert rows(store) == {'allowance/x-twscrape/2026-10-19': {'state': 'ok', 'at': rows(store)['allowance/x-twscrape/2026-10-19']['at'], 'run': 'r1'}}
    assert 'x_candidates_sha256=' in capsys.readouterr().out


def test_the_allowance_is_reserved_before_the_first_request(tmp_path):
    seen = []

    class Probe(FakeFetcher):
        def search(self, query, limit):
            seen.append(dict(rows(store)))
            return super().search(query, limit)

    store = MemoryStore()
    run(tmp_path, Probe(), store=store)
    assert seen and all(r['allowance/x-twscrape/2026-10-19']['state'] == 'reserved' for r in seen)


def test_a_spent_day_collects_nothing_and_exits_three(tmp_path, capsys):
    store = MemoryStore()
    allowance_module.reserve(store, 'x-twscrape', 'earlier', now=lambda: NOW, sleep=lambda s: None, jitter=lambda: 0)
    fetcher = FakeFetcher({1: [post(1)]})
    code, out, _ = run(tmp_path, fetcher, store=store)
    assert code == 3 and fetcher.calls == [] and not out.exists()
    assert 'allowance_spent' in capsys.readouterr().out


@pytest.mark.parametrize('environ', [{}, {'X_AUTH_TOKEN': 'only-one'}, {'X_CT0': 'only-one'}])
def test_missing_cookies_spend_nothing_and_print_names_only(tmp_path, capsys, environ):
    fetcher = FakeFetcher()
    code, out, store = run(tmp_path, fetcher, environ=environ)
    text = capsys.readouterr().out
    assert code == 4 and 'x_needs_setup' in text and 'only-one' not in text
    assert '_State' not in store.tables and fetcher.calls == [] and not out.exists()


def test_a_doomed_output_path_spends_no_allowance(tmp_path):
    out = tmp_path.parent / (tmp_path.name + '_exists.json')
    out.write_text('keep')
    store = MemoryStore()
    assert x.main(['--run-id', 'r1', '--output', str(out)], store=store, fetcher=FakeFetcher(), environ=COOKIES,
                  now=lambda: NOW, sleep=lambda s: None) == 2
    assert '_State' not in store.tables and out.read_text() == 'keep'


def test_the_post_limit_stops_the_run_and_later_queries_are_not_sent(tmp_path, monkeypatch):
    monkeypatch.setitem(sc.LIMITS['x-twscrape'], 'posts', 3)
    fetcher = FakeFetcher({1: [post(1), post(2)], 2: [post(3), post(4)], 3: [post(5)]})
    code, out, _ = run(tmp_path, fetcher)
    assert code == 0 and len(json.loads(out.read_text())['candidates']) == 3
    assert [limit for _, limit in fetcher.calls] == [3, 1]  # the second query was only allowed one more post


@pytest.mark.parametrize('failure,error,state', [
    (sc.FetchBlocked(), 'social_login_failed', 'blocked'),
    (sc.FetchRateLimited(), 'social_rate_limited', 'blocked'),
    (RuntimeError('token=secret-auth-token-value leaked in a message'), 'social_collector_error', 'failed'),
])
def test_a_failure_keeps_earlier_posts_records_a_fixed_word_and_still_spends_the_day(tmp_path, capsys, failure, error, state):
    fetcher = FakeFetcher({1: [post(1)]}, fail=(2, failure))
    code, out, store = run(tmp_path, fetcher)
    text = capsys.readouterr().out
    assert code == 0 and 'secret' not in text and 'secret' not in out.read_text()
    payload = json.loads(out.read_text())
    assert payload['error'] == error and len(payload['candidates']) == 1
    assert rows(store)['allowance/x-twscrape/2026-10-19']['state'] == state


def test_zero_results_record_zero(tmp_path):
    code, out, store = run(tmp_path, FakeFetcher())
    assert code == 0 and rows(store)['allowance/x-twscrape/2026-10-19']['state'] == 'zero'


def test_the_error_words_are_accepted_by_the_sheet_writer():
    from jobhunter.sheets import SOURCE_ERRORS
    assert {sc.LOGIN_FAILED, sc.RATE_LIMITED, sc.COLLECTOR_ERROR} <= SOURCE_ERRORS


def test_the_candidate_file_flows_through_the_queue_and_the_validator(tmp_path, capsys):
    code, out, _ = run(tmp_path, FakeFetcher({1: [post(1)]}))
    digest = __import__('hashlib').sha256(out.read_bytes()).hexdigest()
    work = tmp_path.parent / (tmp_path.name + '_work.json')
    assert queue_cli.main(['pull', '--source', 'x-twscrape', '--candidates', str(out), '--candidates-sha256', digest,
                           '--output', str(work), '--id-field', 'item_id'], store=MemoryStore()) == 0
    work_digest = capsys.readouterr().out.split('work_sha256=')[1].split()[0]
    facts = tmp_path.parent / (tmp_path.name + '_facts.json')
    facts.write_text(json.dumps({'processed': ['1850000000000000001'], 'facts': [{
        'item_id': '1850000000000000001', 'title': 'Senior Product Manager, AI', 'company': 'Acme',
        'location': 'Remote US', 'salary': '', 'description_quote': 'Acme is hiring a Senior Product Manager, AI (Remote US).',
        'apply_url': 'https://acme.example/jobs/pm'}]}))
    result = tmp_path.parent / (tmp_path.name + '_result.json')
    assert social_posts.main(['validate', '--source', 'x-twscrape', '--candidates', str(work), '--candidates-sha256',
                              work_digest, '--extractions', str(facts), '--output', str(result)]) == 0
    assert json.loads(result.read_text())['postings'][0]['title'] == 'Senior Product Manager, AI'


# ---- the twscrape adapter, against a stand-in for the library ------------------------------------

class FakeTweet:
    def __init__(self, number, retweet=False):
        self.url = f'https://x.com/acme/status/{1850000000000000000 + number}'
        self.date = __import__('datetime').datetime(2026, 10, 15, 12, tzinfo=__import__('datetime').timezone.utc)
        self.rawContent = f'post {number}'
        self.links = [types.SimpleNamespace(url='https://acme.example/jobs')]
        self.retweetedTweet = object() if retweet else None
        self.user = types.SimpleNamespace(username='acme_hiring')


def install_fake_twscrape(monkeypatch, tweets=(), search_error=None, init_error=None):
    log = types.SimpleNamespace(api_args=None, cookies=None, level=None, yielded=0, closed=False)

    class HttpStatusError(Exception):
        def __init__(self, status):
            self.response = types.SimpleNamespace(status_code=status)

    class NoAccountError(Exception):
        pass

    class Pool:
        async def add_account_cookies(self, username, cookies):
            if init_error:
                raise init_error
            log.cookies = (username, cookies)

    class API:
        def __init__(self, db_file, raise_when_no_account=False):
            log.api_args = (db_file, raise_when_no_account)
            self.pool = Pool()

        async def search(self, query, limit=-1):
            if search_error:
                raise search_error(log) if callable(search_error) else search_error
            try:
                for tweet in tweets:
                    log.yielded += 1
                    yield tweet
            finally:
                log.closed = True

    module = types.SimpleNamespace(API=API, HttpStatusError=HttpStatusError, NoAccountError=NoAccountError,
                                   set_log_level=lambda level: setattr(log, 'level', level))
    monkeypatch.setitem(sys.modules, 'twscrape', module)
    return log, module


def test_the_adapter_uses_a_private_temporary_database_turns_telemetry_off_and_cleans_up(monkeypatch):
    monkeypatch.delenv('TWS_TELEMETRY', raising=False)
    monkeypatch.delenv('DO_NOT_TRACK', raising=False)
    log, _ = install_fake_twscrape(monkeypatch, [FakeTweet(1), FakeTweet(2, retweet=True), FakeTweet(3)])
    fetcher = x.TwscrapeFetcher('tok', 'ct')
    import os
    assert os.environ['TWS_TELEMETRY'] == '0' and os.environ['DO_NOT_TRACK'] == '1'
    db, raise_flag = log.api_args
    assert raise_flag is True and log.level == 'ERROR' and log.cookies == ('jobhunter-x', 'auth_token=tok; ct0=ct')
    folder = __import__('pathlib').Path(db).parent
    assert folder.is_dir() and (folder.stat().st_mode & 0o077) == 0  # private
    found = fetcher.search('hiring "pm"', 10)
    assert [p['text'] for p in found] == ['post 1', 'post 3']  # the repost is skipped
    assert found[0]['links'] == ['https://acme.example/jobs'] and found[0]['created_at'].startswith('2026-10-15')
    fetcher.close()
    assert not folder.exists()


@pytest.mark.parametrize('error,expected', [
    (lambda log: sys.modules['twscrape'].NoAccountError('x'), sc.FetchBlocked),
    (lambda log: sys.modules['twscrape'].HttpStatusError(403), sc.FetchBlocked),
    (lambda log: sys.modules['twscrape'].HttpStatusError(401), sc.FetchBlocked),
    (lambda log: sys.modules['twscrape'].HttpStatusError(429), sc.FetchRateLimited),
    (lambda log: sys.modules['twscrape'].HttpStatusError(500), Exception),
])
def test_the_adapter_maps_site_refusals_to_fixed_failures(monkeypatch, error, expected):
    install_fake_twscrape(monkeypatch, search_error=error)
    fetcher = x.TwscrapeFetcher('tok', 'ct')
    try:
        with pytest.raises(expected):
            fetcher.search('q', 5)
    finally:
        fetcher.close()


def test_the_adapter_stops_at_the_limit_even_when_the_library_would_yield_more_and_closes_the_stream(monkeypatch):
    log, _ = install_fake_twscrape(monkeypatch, [FakeTweet(n) for n in range(1, 11)])
    fetcher = x.TwscrapeFetcher('tok', 'ct')
    try:
        found = fetcher.search('q', 3)
    finally:
        fetcher.close()
    assert len(found) == 3 and log.yielded == 3 and log.closed  # it never read the other seven


def test_the_adapter_keeps_the_public_author_as_evidence(monkeypatch):
    install_fake_twscrape(monkeypatch, [FakeTweet(1)])
    fetcher = x.TwscrapeFetcher('tok', 'ct')
    try:
        found = fetcher.search('q', 5)
    finally:
        fetcher.close()
    assert found[0]['author'] == 'acme_hiring'


def test_a_failed_start_removes_the_temporary_cookie_database(monkeypatch):
    log, _ = install_fake_twscrape(monkeypatch, init_error=RuntimeError('sqlite i/o error'))
    with pytest.raises(RuntimeError):
        x.TwscrapeFetcher('tok', 'ct')
    assert not __import__('pathlib').Path(log.api_args[0]).parent.exists()


def test_authors_reach_the_candidate_file_and_unsafe_ones_are_dropped(tmp_path):
    good = {**post(1), 'author': 'acme_hiring'}
    bad = {**post(2), 'author': '<script>alert(1)</script>'}
    code, out, _ = run(tmp_path, FakeFetcher({1: [good, bad]}))
    candidates = json.loads(out.read_text())['candidates']
    assert candidates[0]['author'] == 'acme_hiring' and 'author' not in candidates[1]


@pytest.mark.parametrize('failure,status', [(sc.FetchBlocked(), 'blocked'), (sc.FetchRateLimited(), 'blocked'),
                                            (RuntimeError('boom'), 'failed')])
def test_a_refusal_stays_blocked_through_the_validated_source_record(tmp_path, capsys, failure, status):
    from jobhunter.sheets import prepare_payload
    from jobhunter import post_facts as pf
    code, out, _ = run(tmp_path, FakeFetcher({1: [post(1)]}, fail=(2, failure)))
    digest = __import__('hashlib').sha256(out.read_bytes()).hexdigest()
    facts = tmp_path.parent / (tmp_path.name + '_nf.json')
    facts.write_text(json.dumps({'processed': [], 'facts': []}))
    result = tmp_path.parent / (tmp_path.name + '_nr.json')
    assert social_posts.main(['validate', '--source', 'x-twscrape', '--candidates', str(out), '--candidates-sha256', digest,
                              '--extractions', str(facts), '--output', str(result)]) == 0
    source = json.loads(result.read_text())['source']
    assert source['status'] == status and source['error'] in {sc.LOGIN_FAILED, sc.RATE_LIMITED, sc.COLLECTOR_ERROR}
    prepare_payload([], [source])  # the Sheet writer accepts the record
    assert {sc.LOGIN_FAILED, sc.RATE_LIMITED} == set(pf.BLOCKED_ERRORS)
