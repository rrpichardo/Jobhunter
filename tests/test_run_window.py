"""Run modes: 28 days by hand, 3 days daily, and a daily run refused when it would leave a gap."""

from datetime import datetime, timedelta, timezone

import pytest

from jobhunter import run_window as rw
from scripts import run_window as cli
from sheet_fakes import MemoryStore

HEADERS = ['Run ID', 'Started', 'Completed', 'Jobs input', 'Jobs unique', 'Status']
NOW = datetime(2026, 10, 21, 10, 7, tzinfo=timezone.utc)


def row(run, started, status='complete', done=True, jobs=10):
    finished = (started + timedelta(minutes=20)).isoformat() if done else ''
    return [run, started.isoformat(), finished, jobs, jobs, status]


def log(*rows):
    store = MemoryStore()
    store.tables['Run Log'] = [HEADERS, *rows]
    return store


def run(mode, store, capsys, now=NOW):
    code = cli.main(['--mode', mode], store=store, now=lambda: now)
    return code, capsys.readouterr().out


def test_a_manual_run_is_always_28_days_and_does_not_even_read_the_sheet(capsys):
    code, out = run('manual', None, capsys)  # no store: it must not be needed
    assert code == 0 and 'window_days=28' in out


def test_a_daily_run_after_a_recent_complete_run_is_3_days(capsys):
    code, out = run('daily', log(row('r1', NOW - timedelta(hours=24))), capsys)
    assert code == 0 and 'window_days=3' in out


def test_one_missed_day_is_covered_even_with_scheduler_drift(capsys):
    code, out = run('daily', log(row('r1', NOW - timedelta(hours=48, minutes=40))), capsys)
    assert code == 0 and 'window_days=3' in out


@pytest.mark.parametrize('hours', [1, 24, 48, 53.9])
def test_every_accepted_gap_fits_inside_the_window_with_a_full_day_to_spare(hours):
    gap = timedelta(hours=hours)
    days, _ = rw.window_days('daily', [HEADERS, row('r1', NOW - gap)], NOW)
    assert days == 3 and timedelta(days=days) - gap >= timedelta(hours=18)  # room for drift and run time


@pytest.mark.parametrize('hours', [54.1, 72, 200])
def test_a_longer_gap_is_refused_not_stretched(hours, capsys):
    code, out = run('daily', log(row('r1', NOW - timedelta(hours=hours))), capsys)
    assert code == 3 and 'last_run_too_old' in out and 'window_days' not in out


def test_two_missed_days_need_a_manual_catch_up(capsys):
    code, out = run('daily', log(row('r1', NOW - timedelta(days=3))), capsys)
    assert code == 3 and 'catch_up_needed: last_run_too_old' in out and 'window_days' not in out


def test_the_first_ever_run_must_be_manual(capsys):
    for store in (log(), MemoryStore()):  # an empty Run Log, and no Run Log at all
        code, out = run('daily', store, capsys)
        assert code == 3 and 'no_complete_run' in out


def test_only_complete_runs_count_a_pending_or_unfinished_run_does_not(capsys):
    old = row('old', NOW - timedelta(days=5))
    pending = row('p', NOW - timedelta(hours=2), status='pending', done=False)
    code, out = run('daily', log(old, pending), capsys)
    assert code == 3 and 'last_run_too_old' in out


def test_a_complete_with_source_failure_run_still_counts(capsys):
    code, out = run('daily', log(row('r1', NOW - timedelta(hours=20), status='complete-with-source-failure')), capsys)
    assert code == 0 and 'window_days=3' in out


def test_the_newest_complete_run_decides(capsys):
    code, out = run('daily', log(row('old', NOW - timedelta(days=9)), row('new', NOW - timedelta(hours=5))), capsys)
    assert code == 0


def batches(base, started, sizes, **kwargs):
    return [row(f'{base}-b{number:03d}', started + timedelta(minutes=3 * number), jobs=size, **kwargs)
            for number, size in enumerate(sizes, 1)]


def test_a_fully_delivered_batched_run_counts_from_its_first_batch(capsys):
    code, out = run('daily', log(*batches('d1', NOW - timedelta(hours=30), [150, 150, 44])), capsys)
    assert code == 0 and 'window_days=3' in out


def test_a_batched_run_stopped_after_the_first_batch_does_not_count(capsys):
    code, out = run('daily', log(*batches('d1', NOW - timedelta(hours=30), [150])), capsys)  # more may have followed
    assert code == 3 and 'no_complete_run' in out


def test_a_batched_run_with_a_missing_or_unfinished_batch_does_not_count(capsys):
    skipped = batches('d1', NOW - timedelta(hours=30), [150, 150, 44])
    del skipped[1]  # b002 never delivered
    unfinished = batches('d2', NOW - timedelta(hours=30), [150, 44])
    unfinished[1] = row('d2-b002', NOW - timedelta(hours=29), status='pending', done=False, jobs=44)
    for rows in (skipped, unfinished):
        code, out = run('daily', log(*rows), capsys)
        assert code == 3


def test_an_older_whole_run_is_not_replaced_by_a_newer_partial_one(capsys):
    old_whole = row('old', NOW - timedelta(hours=40))
    code, out = run('daily', log(old_whole, *batches('new', NOW - timedelta(hours=5), [150])), capsys)
    assert code == 0 and 'started ' + (NOW - timedelta(hours=40)).isoformat() in out


def test_a_naive_timestamp_is_read_as_utc():
    started = (NOW - timedelta(hours=10)).replace(tzinfo=None).isoformat()
    rows = [HEADERS, ['r1', started, started, 1, 1, 'complete']]
    assert rw.window_days('daily', rows, NOW)[0] == 3


def test_a_corrupt_run_log_fails_closed_without_a_window(capsys):
    store = MemoryStore()
    store.tables['Run Log'] = [['Run ID', 'Run ID', 'Started', 'Completed', 'Status']]  # duplicate header
    code, out = run('daily', store, capsys)
    assert code == 2 and 'window_days' not in out


def test_an_unknown_mode_is_refused():
    with pytest.raises(ValueError, match='invalid_run_mode'):
        rw.window_days('weekly', [], NOW)


def test_the_run_log_is_only_read_never_written():
    store = log(row('r1', NOW - timedelta(hours=3)))
    cli.main(['--mode', 'daily'], store=store, now=lambda: NOW)
    assert store.writes == [] and store.owner is None


# ---- the real store without a Run Log tab, and rows whose times make no sense -------------------

def test_a_real_workbook_with_no_run_log_tab_means_no_prior_run_exit_3_not_an_error(capsys):
    from fake_workbook import FakeWorkbook
    from jobhunter.sheet_io import GspreadStore
    store = GspreadStore(FakeWorkbook())  # a workbook that has never been written to
    assert store.has_tab('Run Log') is False
    code, out = run('daily', store, capsys)
    assert code == 3 and 'no_complete_run' in out


def test_has_tab_is_true_when_the_tab_exists_and_refuses_unapproved_tabs():
    from jobhunter.sheet_io import GspreadStore

    class Workbook:
        def fetch_sheet_metadata(self):
            return {'sheets': [{'properties': {'title': 'Run Log', 'sheetId': 7,
                                               'gridProperties': {'rowCount': 10, 'columnCount': 8}}}]}
    store = GspreadStore(Workbook())
    assert store.has_tab('Run Log') is True and store.has_tab('Jobs') is False
    with pytest.raises(ValueError, match='unapproved_tab'):
        store.has_tab('Secrets')


@pytest.mark.parametrize('started,done', [
    (NOW + timedelta(days=30), NOW + timedelta(days=30, minutes=20)),   # started in the future
    (NOW - timedelta(days=4), NOW - timedelta(days=4, hours=1)),         # completed before it started
    (NOW - timedelta(days=4), NOW + timedelta(days=2)),                  # completed in the future
])
def test_a_corrupt_complete_row_cannot_make_an_old_gap_look_recent(capsys, started, done):
    bad = ['bad', started.isoformat(), done.isoformat(), 1, 1, 'complete']
    old = row('old', NOW - timedelta(days=6))
    code, out = run('daily', log(old, bad), capsys)
    assert code == 3 and 'window_days' not in out


def test_a_row_a_few_minutes_ahead_of_this_machines_clock_is_still_believed(capsys):
    started = NOW - timedelta(hours=1)
    ahead = ['r', started.isoformat(), (NOW + timedelta(minutes=2)).isoformat(), 1, 1, 'complete']  # small clock skew
    code, out = run('daily', log(ahead), capsys)
    assert code == 0 and 'window_days=3' in out
