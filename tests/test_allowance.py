"""One live collection per social source per New York day: reserved first, fail closed, no time-zone database."""

from datetime import datetime, timedelta, timezone
import json

import pytest

from jobhunter import allowance as a
from scripts import allowance as cli
from sheet_fakes import MemoryStore

SRC = 'linkedin-login'


def utc(text):
    return datetime.fromisoformat(text).replace(tzinfo=timezone.utc)


@pytest.mark.parametrize('moment,day', [
    ('2026-10-19T03:59:59', '2026-10-18'), ('2026-10-19T04:00:00', '2026-10-19'),   # EDT, midnight is 04:00Z
    ('2026-12-01T04:59:59', '2026-11-30'), ('2026-12-01T05:00:00', '2026-12-01'),   # EST, midnight is 05:00Z
    ('2026-03-08T04:59:59', '2026-03-07'), ('2026-03-08T05:00:00', '2026-03-08'),   # the day DST starts
    ('2026-03-09T03:59:59', '2026-03-08'), ('2026-03-09T04:00:00', '2026-03-09'),
    ('2026-11-01T03:59:59', '2026-10-31'), ('2026-11-01T04:00:00', '2026-11-01'),   # the day DST ends
    ('2026-11-02T04:59:59', '2026-11-01'), ('2026-11-02T05:00:00', '2026-11-02'),
])
def test_new_york_day_at_the_boundaries(moment, day):
    assert a.new_york_day(utc(moment)) == day


def test_new_york_day_matches_the_system_time_zone_database_every_hour_for_five_years():
    zoneinfo = pytest.importorskip('zoneinfo')
    try:
        zone = zoneinfo.ZoneInfo('America/New_York')
    except zoneinfo.ZoneInfoNotFoundError:
        pytest.skip('no system tz database (the rule-based function exists because of this)')
    moment, end = utc('2026-01-01T00:00:00'), utc('2031-01-01T00:00:00')
    while moment < end:
        assert a.new_york_day(moment) == moment.astimezone(zone).date().isoformat(), moment
        moment += timedelta(minutes=30)


def test_a_naive_time_is_refused():
    with pytest.raises(ValueError, match='invalid_allowance_time'):
        a.new_york_day(datetime(2026, 10, 18))


def reserve(store, now, source=SRC, run='run1'):
    return a.reserve(store, source, run, now=lambda: now, sleep=lambda s: None, jitter=lambda: 0)


def finish(store, now, outcome='ok', source=SRC, run='run1', day=None):
    return a.finish(store, source, run, outcome, day=day, now=lambda: now, sleep=lambda s: None, jitter=lambda: 0)


NOON = '2026-10-18T16:00:00+00:00'   # 12:00 in New York
LATE = '2026-10-19T03:30:00+00:00'   # 23:30 the same New York day
NEXT = '2026-10-19T04:00:00+00:00'   # 00:00 the next New York day


def test_the_first_reservation_of_a_day_succeeds_and_a_second_is_refused():
    store = MemoryStore()
    assert reserve(store, NOON) == '2026-10-18'
    with pytest.raises(a.AllowanceSpent):
        reserve(store, LATE, run='run2')
    assert store.owner is None
    row = json.loads(store.tables['_State'][1][1])
    assert row == {'state': 'reserved', 'at': NOON, 'run': 'run1'}


def test_the_next_new_york_day_restores_the_allowance():
    store = MemoryStore()
    reserve(store, NOON)
    assert reserve(store, NEXT, run='run2') == '2026-10-19'


def test_sources_have_separate_allowances():
    store = MemoryStore()
    reserve(store, NOON)
    assert reserve(store, NOON, source='x-twscrape', run='run1') == '2026-10-18'


@pytest.mark.parametrize('outcome', ['ok', 'zero', 'failed', 'blocked'])
def test_a_failed_blocked_or_empty_attempt_still_spends_the_day(outcome):
    store = MemoryStore()
    reserve(store, NOON)
    finish(store, LATE, outcome)
    assert json.loads(store.tables['_State'][1][1])['state'] == outcome
    with pytest.raises(a.AllowanceSpent):
        reserve(store, LATE, run='run2')


def test_finish_needs_the_matching_reservation():
    store = MemoryStore()
    with pytest.raises(ValueError, match='allowance_not_reserved'):
        finish(store, NOON)
    reserve(store, NOON)
    with pytest.raises(ValueError, match='allowance_not_reserved'):
        finish(store, NOON, run='other')
    with pytest.raises(ValueError, match='invalid_allowance_outcome'):
        finish(store, NOON, outcome='great')


@pytest.mark.parametrize('source,run', [('facebook', 'run1'), ('', 'run1'), (SRC, 'has space'), (SRC, ''), (SRC, 'x' * 81)])
def test_bad_sources_and_run_ids_are_refused_before_any_write(source, run):
    store = MemoryStore()
    with pytest.raises(ValueError):
        a.reserve(store, source, run, now=lambda: NOON, sleep=lambda s: None, jitter=lambda: 0)
    assert store.writes == [] and store.owner is None


def test_a_held_writer_lock_means_no_reservation_so_the_caller_collects_nothing():
    store = MemoryStore()
    store.owner = 'someone-else'
    with pytest.raises(ValueError, match='writer_locked'):
        reserve(store, NOON)
    assert store.tables.get('_State') is None


def test_an_unknown_write_outcome_fails_closed_and_keeps_the_lock():
    store = MemoryStore()
    real = store.write

    def lost_response(title, writes):
        real(title, writes)
        store.mutation_unknown = True
        raise ValueError('sheet_mutation_unconfirmed')
    store.write = lost_response
    with pytest.raises(ValueError, match='sheet_mutation_unconfirmed'):
        reserve(store, NOON)
    assert store.owner is not None  # lock retained for operator recovery, never auto-released


def test_a_corrupt_allowance_row_fails_closed():
    store = MemoryStore()
    store.ensure_tab('_State', ('Key', 'Value'))
    store.tables['_State'].append([f'allowance/{SRC}/2026-10-18', 'not json'])
    with pytest.raises(ValueError, match='invalid_allowance_state'):
        reserve(store, NOON)
    assert store.writes == []


def test_the_state_row_holds_no_secret_or_account_data():
    store = MemoryStore()
    reserve(store, NOON)
    assert set(json.loads(store.tables['_State'][1][1])) == {'state', 'at', 'run'}


# ---- the command line --------------------------------------------------------------------------

def test_cli_reserve_then_spent_then_finish_then_status(capsys):
    store = MemoryStore()
    assert cli.main(['reserve', '--source', SRC, '--run-id', 'r1'], store=store) == 0
    assert 'allowance_reserved' in capsys.readouterr().out
    assert cli.main(['reserve', '--source', SRC, '--run-id', 'r2'], store=store) == cli.EXIT_SPENT == 3
    assert 'allowance_spent' in capsys.readouterr().out
    assert cli.main(['finish', '--source', SRC, '--run-id', 'r1', '--outcome', 'zero'], store=store) == 0
    capsys.readouterr()
    assert cli.main(['status', '--source', SRC], store=store) == 0
    assert 'spent state=zero run=r1' in capsys.readouterr().out
    assert cli.main(['status', '--source', 'x-twscrape'], store=store) == 0
    assert 'available' in capsys.readouterr().out


def test_cli_any_other_failure_says_to_collect_nothing(capsys):
    store = MemoryStore()
    store.owner = 'someone-else'
    assert cli.main(['reserve', '--source', SRC, '--run-id', 'r1'], store=store) == 2
    text = capsys.readouterr().out
    assert 'writer_locked' in text and 'collect nothing' in text


# ---- a collection that crosses midnight in New York --------------------------------------------

BEFORE_MIDNIGHT = '2026-10-20T03:59:59+00:00'   # 23:59:59 on October 19 in New York
AFTER_MIDNIGHT = '2026-10-20T04:00:01+00:00'    # 00:00:01 on October 20


def state_rows(store):
    return {row[0]: json.loads(row[1]) for row in store.tables['_State'][1:]}


def test_finish_closes_the_day_that_was_reserved_when_the_run_crosses_midnight():
    store = MemoryStore()
    day = reserve(store, BEFORE_MIDNIGHT)
    assert day == '2026-10-19'
    assert finish(store, AFTER_MIDNIGHT, 'ok', day=day) == '2026-10-19'
    rows = state_rows(store)
    assert list(rows) == [f'allowance/{SRC}/2026-10-19'] and rows[f'allowance/{SRC}/2026-10-19']['state'] == 'ok'
    # the new day's allowance was neither consumed nor changed
    assert reserve(store, AFTER_MIDNIGHT, run='run2') == '2026-10-20'


def test_finish_without_a_day_finds_the_reservation_by_run_id_across_midnight():
    store = MemoryStore()
    reserve(store, BEFORE_MIDNIGHT)
    assert finish(store, AFTER_MIDNIGHT, 'zero') == '2026-10-19'
    assert state_rows(store)[f'allowance/{SRC}/2026-10-19']['state'] == 'zero'
    assert f'allowance/{SRC}/2026-10-20' not in state_rows(store)


def test_finish_never_writes_a_row_that_belongs_to_another_run():
    store = MemoryStore()
    reserve(store, BEFORE_MIDNIGHT, run='run1')
    reserve(store, AFTER_MIDNIGHT, run='run2')
    with pytest.raises(ValueError, match='allowance_not_reserved'):
        finish(store, AFTER_MIDNIGHT, run='run3')
    with pytest.raises(ValueError, match='allowance_not_reserved'):
        finish(store, AFTER_MIDNIGHT, run='run1', day='2026-10-20')  # that day belongs to run2
    assert finish(store, AFTER_MIDNIGHT, run='run2') == '2026-10-20'
    assert state_rows(store)[f'allowance/{SRC}/2026-10-19']['state'] == 'reserved'


@pytest.mark.parametrize('day', ['today', '2026-1-1', '2026-10-19; drop', 5, '2026-02-30', '2026-99-99', '2026-00-10',
                                 '2025-02-29', '0000-01-01'])
def test_a_malformed_day_is_refused_before_any_write(day):
    store = MemoryStore()
    reserve(store, NOON)
    writes = len(store.writes)
    with pytest.raises(ValueError, match='invalid_allowance_day'):
        finish(store, NOON, day=day)
    assert len(store.writes) == writes


def test_cli_finish_takes_the_reserved_day(capsys):
    store = MemoryStore()
    assert cli.main(['reserve', '--source', SRC, '--run-id', 'r1'], store=store) == 0
    day = capsys.readouterr().out.split('day=')[1].split()[0]
    assert cli.main(['finish', '--source', SRC, '--run-id', 'r1', '--outcome', 'ok', '--day', day], store=store) == 0
    assert f'day={day}' in capsys.readouterr().out
    assert cli.main(['finish', '--source', SRC, '--run-id', 'r1', '--outcome', 'ok', '--day', 'bad'], store=store) == 2
    assert 'invalid_allowance_day' in capsys.readouterr().out


# 2026-03-08 is the spring-forward day in New York (the clocks jump at 02:00 local)
SPRING_BEFORE = '2026-03-09T03:59:59+00:00'   # 23:59:59 on March 8 (EDT)
SPRING_AFTER = '2026-03-09T04:00:01+00:00'    # 00:00:01 on March 9


def test_finish_without_a_day_finds_the_reservation_across_the_spring_clock_change():
    store = MemoryStore()
    assert reserve(store, SPRING_BEFORE) == '2026-03-08'
    assert finish(store, SPRING_AFTER, 'ok') == '2026-03-08'
    assert state_rows(store)[f'allowance/{SRC}/2026-03-08']['state'] == 'ok'


def test_finish_without_a_day_finds_the_reservation_across_the_fall_clock_change():
    # 2026-11-01 is the fall-back day: that New York date is 25 hours long
    store = MemoryStore()
    assert reserve(store, '2026-11-02T04:59:59+00:00') == '2026-11-01'   # 23:59:59 EST
    assert finish(store, '2026-11-02T05:00:01+00:00', 'zero') == '2026-11-01'


def test_a_closed_attempt_is_never_rewritten_with_a_different_outcome():
    store = MemoryStore()
    reserve(store, NOON)
    finish(store, NOON, 'ok')
    before = json.loads(store.tables['_State'][1][1])
    with pytest.raises(ValueError, match='allowance_already_closed'):
        finish(store, NOON, 'failed')
    assert json.loads(store.tables['_State'][1][1]) == before  # the original audit evidence is untouched


def test_repeating_the_same_outcome_is_harmless_and_writes_nothing():
    store = MemoryStore()
    reserve(store, NOON)
    finish(store, NOON, 'zero')
    writes = len(store.writes)
    assert finish(store, LATE, 'zero') == '2026-10-18'
    assert len(store.writes) == writes
