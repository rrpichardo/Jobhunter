"""The AI read-queue: read each free-text item once, keep leftovers visible, never lose an item."""

import json

import pytest

from jobhunter import ai_queue as q
from scripts import ai_queue as cli
from sheet_fakes import MemoryStore

SRC = 'hn-who-is-hiring'
T0 = '2026-10-18T10:00:00+00:00'
T1 = '2026-10-19T10:00:00+00:00'
T5 = '2026-10-23T10:00:00+00:00'


def cand(number, created='2026-10-10T00:00:00+00:00'):
    return {'comment_id': str(number), 'created_at': created, 'text': f'text {number}', 'links': []}


def pull(store, items, now, **kwargs):
    return q.pull(store, SRC, items, now=lambda: now, sleep=lambda s: None, jitter=lambda: 0, **kwargs)


def commit(store, ids, now):
    return q.commit(store, SRC, ids, now=lambda: now, sleep=lambda s: None, jitter=lambda: 0)


def state(store, kind=None):
    rows = store.tables['_State']
    return {r[0]: r[1] for r in rows[1:] if r and r[1] and (kind is None or f'/{kind}/' in r[0])}


def test_first_pull_queues_everything_and_hands_all_of_it_to_the_ai():
    store = MemoryStore()
    work, summary = pull(store, [cand(1), cand(2), cand(3)], T0)
    assert [c['comment_id'] for c in work] == ['1', '2', '3']
    assert summary['new_today'] == 3 and summary['to_read_now'] == 3 and summary['already_read'] == 0
    assert sorted(state(store, 'pending')) == [f'queue/{SRC}/pending/{i}' for i in '123']
    assert store.owner is None  # the writer lock is released


def test_items_the_ai_already_read_are_not_sent_again_tomorrow():
    store = MemoryStore()
    pull(store, [cand(1), cand(2)], T0)
    assert commit(store, ['1'], T0)['marked_read'] == 1
    work, summary = pull(store, [cand(1), cand(2), cand(3)], T1)
    assert [c['comment_id'] for c in work] == ['2', '3']         # 1 is done; 2 waited a day; 3 is new
    assert summary['already_read'] == 1 and summary['new_today'] == 1
    assert f'queue/{SRC}/done/1' in state(store, 'done')


def test_an_item_that_was_not_committed_comes_back_and_waits_oldest_first():
    store = MemoryStore()
    pull(store, [cand(1)], T0)
    work, summary = pull(store, [cand(2), cand(1)], T1)   # 1 was never committed (a crash after pull)
    assert [c['comment_id'] for c in work] == ['1', '2']
    assert summary['oldest_unread_age_days'] == 1


def test_the_safety_stop_holds_the_newest_back_and_reports_it_then_they_drain_next_run():
    store = MemoryStore()
    items = [cand(n) for n in range(1, 6)]
    work, summary = pull(store, items, T0, limit=2)
    assert len(work) == 2 and summary['held_by_safety_stop'] == 3
    commit(store, [c['comment_id'] for c in work], T0)
    work2, summary2 = pull(store, items, T1, limit=2)
    assert len(work2) == 2 and summary2['held_by_safety_stop'] == 1 and summary2['already_read'] == 2
    assert not {c['comment_id'] for c in work} & {c['comment_id'] for c in work2}


def test_an_unread_item_that_left_the_window_is_counted_expired_not_kept_forever():
    store = MemoryStore()
    pull(store, [cand(1), cand(2)], T0)
    work, summary = pull(store, [cand(2)], T5)
    assert summary['expired_unread'] == 1 and [c['comment_id'] for c in work] == ['2']
    assert f'queue/{SRC}/pending/1' not in state(store, 'pending')


def test_commit_is_idempotent_and_clears_pending():
    store = MemoryStore()
    pull(store, [cand(1)], T0)
    commit(store, ['1'], T0)
    assert commit(store, ['1'], T1)['marked_read'] == 0
    assert state(store, 'pending') == {} and list(state(store, 'done')) == [f'queue/{SRC}/done/1']


def test_the_queue_never_stores_item_text_and_ignores_the_delivery_journal_rows():
    store = MemoryStore()
    store.ensure_tab('_State', ('Key', 'Value'))
    store.tables['_State'].append(['m0/run/abc/manifest', '{"state":"done"}'])
    pull(store, [cand(1)], T0)
    assert 'text 1' not in json.dumps(store.tables['_State'])
    assert ['m0/run/abc/manifest', '{"state":"done"}'] in store.tables['_State']


def test_sources_do_not_share_a_queue():
    store = MemoryStore()
    q.pull(store, 'other-source', [cand(1)], now=lambda: T0, sleep=lambda s: None, jitter=lambda: 0)
    commit(store, ['1'], T0)  # commits hn-who-is-hiring/1 only
    work, _ = q.pull(store, 'other-source', [cand(1)], now=lambda: T1, sleep=lambda s: None, jitter=lambda: 0)
    assert [c['comment_id'] for c in work] == ['1']


@pytest.mark.parametrize('source,ids', [('Bad Source', ['1']), ('', ['1']), (SRC, ['has space']), (SRC, ['../x']),
                                        (SRC, [1]), (SRC, ['1', '1']), (SRC, 'x')])
def test_bad_sources_and_item_ids_are_refused_before_any_write(source, ids):
    store = MemoryStore()
    with pytest.raises(ValueError):
        q.commit(store, source, ids, now=lambda: T0, sleep=lambda s: None, jitter=lambda: 0)
    assert store.writes == [] and store.owner is None


def test_a_corrupt_queue_row_fails_closed_without_writing():
    store = MemoryStore()
    store.ensure_tab('_State', ('Key', 'Value'))
    store.tables['_State'].append([f'queue/{SRC}/pending/1', 'not json'])
    with pytest.raises(ValueError, match='invalid_queue_state'):
        pull(store, [cand(1)], T0)
    assert store.writes == [] and store.owner is None


def test_a_held_writer_lock_stops_the_queue_too():
    store = MemoryStore()
    store.owner = 'someone-else'
    with pytest.raises(ValueError, match='writer_locked'):
        pull(store, [cand(1)], T0)
    assert store.tables.get('_State') is None and store.owner == 'someone-else'


# ---- the command line --------------------------------------------------------------------------

def artifact(tmp_path, name, payload):
    from jobhunter.artifacts import write_artifact
    path = tmp_path.parent / (tmp_path.name + name)
    return path, write_artifact(path, payload)


def test_cli_pull_then_commit_round_trip(tmp_path, capsys):
    store = MemoryStore()
    path, digest = artifact(tmp_path, '_cand.json', {'schema_version': 1, 'candidates': [cand(1), cand(2)]})
    out = tmp_path.parent / (tmp_path.name + '_work.json')
    assert cli.main(['pull', '--source', SRC, '--candidates', str(path), '--candidates-sha256', digest,
                     '--output', str(out)], store=store) == 0
    assert 'to_read_now=2' in capsys.readouterr().out
    work = json.loads(out.read_text())
    assert [c['comment_id'] for c in work['candidates']] == ['1', '2'] and work['queue']['new_today'] == 2
    result, rdigest = artifact(tmp_path, '_res.json', {'processed_ids': ['1']})
    assert cli.main(['commit', '--source', SRC, '--result', str(result), '--result-sha256', rdigest], store=store) == 0
    assert 'marked_read=1' in capsys.readouterr().out
    assert list(state(store, 'done')) == [f'queue/{SRC}/done/1']


def test_cli_rejects_a_changed_candidates_file(tmp_path, capsys):
    path, _ = artifact(tmp_path, '_cand2.json', {'candidates': [cand(1)]})
    store = MemoryStore()
    assert cli.main(['pull', '--source', SRC, '--candidates', str(path), '--candidates-sha256', '0' * 64,
                     '--output', str(tmp_path.parent / 'nope.json')], store=store) == 2
    assert 'artifact_digest_mismatch' in capsys.readouterr().out and store.writes == []
