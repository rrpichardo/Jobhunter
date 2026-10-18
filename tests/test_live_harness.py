import pytest

from fake_workbook import FakeWorkbook
from jobhunter.sheet_io import LOCK_ID, LOCK_TITLE
from scripts import live_harness as harness


def run(names, workbook=None):
    workbook = workbook or FakeWorkbook()
    args = ['--interval', '0'] + [a for n in names for a in ('--scenario', n)]
    return harness.main(args, workbook=workbook, sleep=lambda seconds: None), workbook


@pytest.mark.parametrize('name', [n for n in harness.DEFAULT_SUITE if n != 'overlap'])
def test_every_clean_scenario_passes_against_the_fake_workbook(name, capsys):
    code, workbook = run([name])
    out = capsys.readouterr().out
    assert code == 0, out
    assert 'FAIL' not in out
    assert LOCK_TITLE not in workbook.sheets  # the lock was released by the writer itself


def test_scenarios_never_touch_the_real_tabs():
    code, workbook = run(['preserve', 'chunks'])
    assert code == 0
    assert not {'Jobs', 'Sources', 'Run Log', '_State'} & set(workbook.sheets)
    assert all(title.startswith('_M0Test_') or title == LOCK_TITLE for title in workbook.sheets)


@pytest.mark.parametrize('name', ['timeout_before_apply', 'interrupt_before_apply'])
def test_lock_retaining_scenarios_stop_and_never_unlock(name, capsys):
    code, workbook = run([name])
    assert code == harness.EXIT_LOCK_RETAINED, capsys.readouterr().out
    assert LOCK_TITLE in workbook.sheets
    assert 'overlap' in harness.DEFAULT_SUITE and name not in harness.DEFAULT_SUITE


def test_guard_blocks_real_tab_access_and_records_it():
    wb = harness.GuardedWorkbook(FakeWorkbook(), '_M0Test_abcdef123456', interval=0)
    with pytest.raises(AssertionError):
        wb.values_get("'Jobs'")
    with pytest.raises(AssertionError):
        wb.values_batch_update({'data': [{'range': "'Jobs'!A1", 'values': [['x']]}]})
    with pytest.raises(AssertionError):
        wb.batch_update({'requests': [{'deleteSheet': {'sheetId': 99}}]})
    assert len(wb.violations) == 3


def test_a_locked_workbook_stops_the_harness_untouched(capsys):
    workbook = FakeWorkbook()
    workbook.batch_update({'requests': [{'addSheet': {'properties': {
        'sheetId': LOCK_ID, 'title': LOCK_TITLE, 'gridProperties': {'rowCount': 1, 'columnCount': 3}}}},
        {'updateCells': {'start': {'sheetId': LOCK_ID, 'rowIndex': 0, 'columnIndex': 0},
                         'rows': [{'values': [{'userEnteredValue': {'stringValue': 'someone'}}]}],
                         'fields': 'userEnteredValue'}}]})
    code, _ = run(['chunks'], workbook)
    assert code == 2 and 'writer lock already exists' in capsys.readouterr().out
    assert LOCK_TITLE in workbook.sheets


def test_harness_source_has_no_unlock_path():
    text = open(harness.__file__).read()
    assert 'drop_lock' not in text and 'deleteSheet' not in text


def test_only_fixture_text_is_ever_generated():
    job = harness.fixture_job('_M0Test_abcdef123456', 1)
    assert job['Apply link'].startswith('https://example.invalid/')


def test_worker_reports_json_and_second_worker_is_refused_while_lock_is_held(tmp_path, capsys):
    import json
    workbook = FakeWorkbook()
    namespace = harness.fresh_namespace(workbook)
    path = tmp_path / 'jobs.json'
    path.write_text(json.dumps([harness.fixture_job(namespace, 1)]))
    args = ['--worker', namespace, '--worker-input', str(path), '--interval', '0', '--worker-tag', 'A']
    assert harness.main(args, workbook=workbook) == 0
    assert json.loads(capsys.readouterr().out.splitlines()[-1]) == {'tag': 'A', 'error': None}
    # A second writer arriving while a lock exists must lose without touching it.
    context = harness.Context(namespace, harness.GuardedWorkbook(workbook, namespace, interval=0))
    store = context.store()
    store.create_lock('other-writer', '2026-10-17T00:00:00+00:00')
    assert harness.main(args + ['--worker-tag', 'B'], workbook=workbook) == 0
    assert json.loads(capsys.readouterr().out.splitlines()[-1]) == {'tag': 'B', 'error': 'writer_locked'}
    assert store.lock_owner() == 'other-writer'
