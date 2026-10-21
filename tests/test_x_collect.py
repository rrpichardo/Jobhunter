"""X hiring-post collector: limits, allowance order, cookie handling and the twscrape adapter, all offline."""

from datetime import datetime, timezone
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
        assert phrases, query
        for phrase in phrases:  # EVERY quoted phrase, so one good phrase cannot hide a wasted one
            assert ROLE_TEXT.search(phrase), (query, phrase)
            assert role_family(phrase), (query, phrase)  # and a title like it is really delivered


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


def test_one_busy_search_cannot_use_the_whole_post_limit(tmp_path):
    fetcher = FakeFetcher()
    run(tmp_path, fetcher)
    assert max(limit for _, limit in fetcher.calls) == sc.LIMITS['x-twscrape']['per_query'] == 40


def test_a_missing_library_asks_for_setup_and_spends_nothing(tmp_path, monkeypatch, capsys):
    monkeypatch.delitem(sys.modules, 'twscrape', raising=False)
    monkeypatch.setattr(x.importlib.util, 'find_spec', lambda name: None)
    store = MemoryStore()
    out = tmp_path.parent / (tmp_path.name + '_x.json')
    code = x.main(['--run-id', 'r1', '--output', str(out)], store=store, environ=COOKIES, now=lambda: NOW)
    assert code == 4 and 'social extra' in capsys.readouterr().out and '_State' not in store.tables


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


def install_fake_twscrape(monkeypatch, tweets=(), search_error=None, init_error=None, no_response=False, account='active',
                          aborted=False, account_error=None, cursor=True, fail_after_pages=None):
    """A stand-in for twscrape 0.20.1. Like the real library: a search that X really answered adds to the account's
    per-queue request counter even when the answer holds no tweets (and then yields nothing); a request dropped by an
    HTML/Cloudflare block yields nothing and adds nothing, wherever in the pagination it happens (`aborted` drops the
    request after the last page). Each tweet is its own page here; a stream that runs out ends with one counted
    answer holding no posts, as in twscrape."""
    log = types.SimpleNamespace(api_args=None, cookies=None, level=None, yielded=0, closed=False)

    class HttpStatusError(Exception):
        def __init__(self, status):
            self.response = types.SimpleNamespace(status_code=status)

    class NoAccountError(Exception):
        pass

    def state(active=True, locks=None):
        return types.SimpleNamespace(active=active, locks=locks or {}, stats={})

    states = {'active': state(), 'banned': state(active=False),
              'cooling': state(locks={'SearchTimeline': datetime(2099, 1, 1, tzinfo=timezone.utc)}),
              'naive-lock': state(locks={'SearchTimeline': datetime(2099, 1, 1)}),
              'expired-lock': state(locks={'SearchTimeline': datetime(2000, 1, 1, tzinfo=timezone.utc)}),
              'missing': None}
    current = states[account]

    class Pool:
        async def add_account_cookies(self, username, cookies):
            if init_error:
                raise init_error
            log.cookies = (username, cookies)

        async def get_account(self, username):
            if account_error:
                raise account_error
            return current

    class API:
        def __init__(self, db_file, raise_when_no_account=False):
            log.api_args = (db_file, raise_when_no_account)
            self.pool = Pool()

        async def search_raw(self, query, limit=-1):
            if search_error:
                raise search_error(log) if callable(search_error) else search_error
            counted = 0
            try:
                if no_response:
                    return  # dropped silently: nothing yielded, nothing counted
                for number, tweet in enumerate(tweets):
                    if fail_after_pages is not None and number == fail_after_pages:
                        raise sys.modules['twscrape'].NoAccountError('x')
                    log.yielded += 1
                    counted += 1
                    page = {'tweets': [tweet], 'entries': [{'content': {'cursorType': 'Bottom', 'value': 'c'}}] if cursor else []}
                    yield types.SimpleNamespace(json=lambda page=page: page)
                if not aborted:
                    counted += 1  # the last answer, with no posts and no cursor, is counted but not yielded
            finally:
                log.closed = True
                if current is not None:  # recorded when the stream closes, as in twscrape
                    current.stats['SearchTimeline'] = current.stats.get('SearchTimeline', 0) + counted

    def parse_tweets(obj, limit=-1):
        return iter(obj['tweets'] if limit < 0 else obj['tweets'][:limit])

    class Logger:
        """The few loguru calls the adapter uses: sinks receive every message at or above their level."""
        def __init__(self):
            self.sinks = {}
            self.next_id = 0

        def add(self, sink, level='DEBUG', format='{message}'):
            self.next_id += 1
            self.sinks[self.next_id] = sink
            return self.next_id

        def remove(self, sink_id):
            del self.sinks[sink_id]

        def emit(self, text):
            for sink in list(self.sinks.values()):
                sink(text + '\n')

    log.logger = Logger()
    module = types.SimpleNamespace(API=API, HttpStatusError=HttpStatusError, NoAccountError=NoAccountError,
                                   models=types.SimpleNamespace(parse_tweets=parse_tweets),
                                   logger=log.logger,  # like the real package, the logger object itself
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
    assert folder.is_dir()
    if os.name != 'nt':  # Windows has no owner-only permission bits to check; the folder is still deleted below
        assert (folder.stat().st_mode & 0o077) == 0  # private
    found = fetcher.search('hiring "pm"', 10)
    assert [p['text'] for p in found] == ['post 1', 'post 3']  # the repost is skipped
    assert found[0]['links'] == ['https://acme.example/jobs'] and found[0]['created_at'].startswith('2026-10-15')
    fetcher.close()
    assert not folder.exists()


@pytest.mark.parametrize('error,expected', [
    (lambda log: sys.modules['twscrape'].NoAccountError('x'), x.CollectorFailure),  # active account, no rate-limit evidence
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


def test_a_search_that_runs_out_normally_is_not_a_refusal(monkeypatch):
    install_fake_twscrape(monkeypatch, [FakeTweet(1), FakeTweet(2)])
    fetcher = x.TwscrapeFetcher('tok', 'ct')
    try:
        assert len(fetcher.search('q', 5)) == 2
    finally:
        fetcher.close()


def test_a_block_after_some_pages_is_still_a_refusal_and_keeps_what_was_read(monkeypatch):
    install_fake_twscrape(monkeypatch, [FakeTweet(1), FakeTweet(2)], aborted=True)  # the next page request was dropped
    fetcher = x.TwscrapeFetcher('tok', 'ct')
    try:
        with pytest.raises(sc.FetchBlocked) as caught:
            fetcher.search('q', 5)
    finally:
        fetcher.close()
    assert len(caught.value.found) == 2


def test_a_run_with_a_block_after_some_pages_keeps_those_posts_and_records_the_refusal(monkeypatch, tmp_path):
    install_fake_twscrape(monkeypatch, [FakeTweet(1), FakeTweet(2)], aborted=True)
    code, out, store = run(tmp_path, None, environ=COOKIES)
    payload = json.loads(out.read_text())
    assert code == 0 and payload['error'] == 'social_login_failed' and len(payload['candidates']) == 2
    assert rows(store)['allowance/x-twscrape/2026-10-19']['state'] == 'blocked'


def test_a_last_page_that_says_there_is_no_next_page_is_a_normal_end(monkeypatch):
    install_fake_twscrape(monkeypatch, [FakeTweet(1)], aborted=True, cursor=False)  # no cursor: no further request exists
    fetcher = x.TwscrapeFetcher('tok', 'ct')
    try:
        assert len(fetcher.search('q', 5)) == 1
    finally:
        fetcher.close()


def test_a_rate_limit_after_some_pages_keeps_what_was_read(monkeypatch):
    install_fake_twscrape(monkeypatch, [FakeTweet(1), FakeTweet(2), FakeTweet(3)], fail_after_pages=2, account='cooling')
    fetcher = x.TwscrapeFetcher('tok', 'ct')
    fetcher._rate_limit_seen = True
    try:
        with pytest.raises(sc.FetchRateLimited) as caught:
            fetcher.search('q', 5)
    finally:
        fetcher.close()
    assert len(caught.value.found) == 2


def test_stopping_at_the_limit_is_not_mistaken_for_a_block(monkeypatch):
    install_fake_twscrape(monkeypatch, [FakeTweet(n) for n in range(1, 11)], aborted=True)
    fetcher = x.TwscrapeFetcher('tok', 'ct')
    try:
        assert len(fetcher.search('q', 3)) == 3  # we closed the stream ourselves; no final answer is expected
    finally:
        fetcher.close()


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


def test_an_answered_search_with_no_tweets_is_a_genuine_zero_even_though_the_library_yields_nothing(monkeypatch):
    install_fake_twscrape(monkeypatch, tweets=[])
    fetcher = x.TwscrapeFetcher('tok', 'ct')
    try:
        assert fetcher.search('q', 5) == []
    finally:
        fetcher.close()


def test_no_response_at_all_is_a_refusal_not_a_healthy_empty_result(monkeypatch):
    # twscrape ends the stream silently when X answers with an HTML/Cloudflare block
    install_fake_twscrape(monkeypatch, no_response=True)
    fetcher = x.TwscrapeFetcher('tok', 'ct')
    try:
        with pytest.raises(sc.FetchBlocked):
            fetcher.search('q', 5)
    finally:
        fetcher.close()


@pytest.mark.parametrize('account,said_rate_limited,expected', [
    ('banned', False, sc.FetchBlocked), ('missing', False, sc.FetchBlocked), ('banned', True, sc.FetchBlocked),
    ('cooling', True, sc.FetchRateLimited),           # X said "Rate limited" and the account is cooling down
    ('cooling', False, x.CollectorFailure),           # locked after a network/unknown error: not a rate limit
    ('naive-lock', False, x.CollectorFailure), ('expired-lock', False, x.CollectorFailure),
    ('active', False, x.CollectorFailure), ('active', True, sc.FetchRateLimited)])
def test_no_available_account_is_told_apart_rejected_session_rate_limit_or_collector_defect(
        monkeypatch, account, said_rate_limited, expected):
    def raise_no_account(log):
        if said_rate_limited:
            log.logger.emit('Rate limited: 200 - req - OK')
        return sys.modules['twscrape'].NoAccountError('x')
    install_fake_twscrape(monkeypatch, search_error=raise_no_account, account=account)
    fetcher = x.TwscrapeFetcher('tok', 'ct')
    try:
        with pytest.raises(expected):
            fetcher.search('q', 5)
    finally:
        fetcher.close()


def test_an_account_that_cannot_be_inspected_is_a_collector_defect_not_a_login_failure(monkeypatch):
    def raise_no_account(log):
        return sys.modules['twscrape'].NoAccountError('x')
    install_fake_twscrape(monkeypatch, search_error=raise_no_account, account_error=OSError('sqlite i/o error'))
    fetcher = x.TwscrapeFetcher('tok', 'ct')
    try:
        with pytest.raises(x.CollectorFailure):
            fetcher.search('q', 5)
    finally:
        fetcher.close()


def test_only_a_yes_or_no_is_kept_from_twscrapes_log_and_the_watcher_is_removed(monkeypatch):
    log, _ = install_fake_twscrape(monkeypatch)
    fetcher = x.TwscrapeFetcher('tok', 'ct')
    assert len(log.logger.sinks) == 1
    log.logger.emit('Rate limited: 200 - req-id-123 - (88) secret-looking-text')
    assert fetcher._rate_limit_seen is True
    assert 'secret-looking-text' not in repr(vars(fetcher))  # the message itself is never stored
    fetcher.close()
    assert log.logger.sinks == {}


def test_other_log_lines_do_not_count_as_a_rate_limit(monkeypatch):
    log, _ = install_fake_twscrape(monkeypatch)
    fetcher = x.TwscrapeFetcher('tok', 'ct')
    log.logger.emit('Unhandled API response code: 500 - req')
    log.logger.emit('Blocked by Cloudflare: 403')
    assert fetcher._rate_limit_seen is False
    fetcher.close()


def test_a_blocked_first_search_stops_the_run_records_blocked_and_spends_the_day(monkeypatch, tmp_path):
    install_fake_twscrape(monkeypatch, no_response=True)
    code, out, store = run(tmp_path, None, environ=COOKIES)  # the real adapter, over the stand-in
    payload = json.loads(out.read_text())
    assert code == 0 and payload['error'] == 'social_login_failed' and payload['candidates'] == []
    assert rows(store)['allowance/x-twscrape/2026-10-19']['state'] == 'blocked'


def test_a_genuine_zero_first_query_does_not_stop_the_run_or_record_blocked(monkeypatch, tmp_path):
    install_fake_twscrape(monkeypatch, tweets=[])  # X answered every search, none had posts
    code, out, store = run(tmp_path, None, environ=COOKIES)
    payload = json.loads(out.read_text())
    assert code == 0 and payload['error'] == '' and payload['stats']['queries_run'] == 10  # every search was sent
    assert rows(store)['allowance/x-twscrape/2026-10-19']['state'] == 'zero'


def test_a_startup_failure_spends_nothing_leaks_nothing_and_leaves_no_cookie_file(monkeypatch, tmp_path, capsys):
    log, _ = install_fake_twscrape(monkeypatch, init_error=RuntimeError('token=secret-auth-token-value sqlite i/o error'))
    code, out, store = run(tmp_path, None, environ=COOKIES)
    text = capsys.readouterr().out
    assert code == 4 and not out.exists() and '_State' not in store.tables
    assert 'secret' not in text and 'no allowance was spent' in text
    assert not __import__('pathlib').Path(log.api_args[0]).parent.exists()  # and the cookie file is gone


def test_cookies_pasted_with_quotes_or_a_newline_are_cleaned_and_blank_ones_count_as_missing(monkeypatch, tmp_path):
    log, _ = install_fake_twscrape(monkeypatch, [])
    code, _, _ = run(tmp_path, None, environ={'X_AUTH_TOKEN': ' "tok"\n', 'X_CT0': "'ct'  "})
    assert code == 0 and log.cookies == ('jobhunter-x', 'auth_token=tok; ct0=ct')
    code, _, store = run(tmp_path.parent / (tmp_path.name + 'b'), None, environ={'X_AUTH_TOKEN': 'tok', 'X_CT0': ' \n'})
    assert code == 4 and '_State' not in store.tables


def test_a_post_quoted_inside_a_new_one_but_dated_before_the_window_is_dropped(monkeypatch):
    old = FakeTweet(2)
    old.date = __import__('datetime').datetime(2024, 1, 1, tzinfo=timezone.utc)
    install_fake_twscrape(monkeypatch, [FakeTweet(1), old])
    fetcher = x.TwscrapeFetcher('tok', 'ct', since='2026-09-21')
    try:
        found = fetcher.search('q', 10)
    finally:
        fetcher.close()
    assert [post_['url'][-1] for post_ in found] == ['1']


def test_the_adapter_starts_against_the_real_library_when_it_is_installed(monkeypatch):
    # The stand-in above can only be as right as our reading of twscrape; this checks the names and the startup
    # against the real pinned package (skipped when the optional `social` extra is not installed).
    monkeypatch.delitem(sys.modules, 'twscrape', raising=False)
    twscrape = pytest.importorskip('twscrape')
    for name in ('API', 'HttpStatusError', 'NoAccountError', 'set_log_level', 'models', 'logger'):
        assert hasattr(twscrape, name), name
    assert callable(twscrape.models.parse_tweets) and callable(twscrape.logger.add) and callable(twscrape.logger.remove)
    fetcher = x.TwscrapeFetcher('tok', 'ct')
    folder = fetcher._dir
    try:
        assert folder.exists() and fetcher._successful_requests() == 0
    finally:
        fetcher.close()
    assert not folder.exists()
