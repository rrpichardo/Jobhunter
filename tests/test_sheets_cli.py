import pytest
import json

from sheet_fakes import MemoryStore
from test_sheet_records import job
from test_sheets import sources


def normalized():
    return {'schema_version': 1, 'source': sources()[0] | {'selected_for_m0': 1}, 'jobs': [job()],
            'extraction': {'selected': 1, 'validated': 1, 'status': 'complete'}}


def test_cli_delivers_validated_records_and_repeated_run_is_idempotent(tmp_path):
    from scripts.sheets_sync import main
    path = tmp_path / 'records.json'
    path.write_text(json.dumps(normalized()))
    backend = MemoryStore()
    args = ['--input', str(path), '--run-id', 'example']
    assert main(args, store=backend) == 0
    assert main(args, store=backend) == 0
    assert len(backend.tables['Jobs']) == 2
    assert len(backend.tables['Run Log']) == 2


def test_invalid_or_partial_input_does_not_open_google(tmp_path, monkeypatch, capsys):
    from scripts import sheets_sync
    monkeypatch.setattr(sheets_sync, 'open_workbook', lambda: (_ for _ in ()).throw(AssertionError('Google called')))
    path = tmp_path / 'bad.json'
    for content in ['private / malformed JSON', json.dumps(normalized() | {
            'extraction': {'selected': 2, 'validated': 1, 'status': 'partial-or-empty'}})]:
        path.write_text(content)
        assert sheets_sync.main(['--input', str(path)]) == 2
    assert 'private /' not in capsys.readouterr().out


def test_failed_harvest_records_failure_and_returns_nonzero(tmp_path):
    from scripts.sheets_sync import main
    path = tmp_path / 'failed.json'
    path.write_text(json.dumps({'schema_version': 1, 'source': sources('failed')[0], 'jobs': []}))
    backend = MemoryStore()
    assert main(['--input', str(path), '--run-id', 'failed'], store=backend) == 2
    assert backend.tables['Sources'][1][1] == 'failed'


def test_cli_quarantine_moves_a_poisoned_run_and_unblocks_later_syncs(tmp_path, capsys):
    from scripts.sheets_sync import main
    from test_sheets import poison
    path = tmp_path / 'records.json'
    path.write_text(json.dumps(normalized()))
    backend = MemoryStore()
    assert main(['--input', str(path), '--run-id', 'first'], store=backend) == 0
    poison(backend)
    assert main(['--input', str(path), '--run-id', 'blocked'], store=backend) == 2
    assert main(['--quarantine-run', 'poison'], store=backend) == 0
    assert 'quarantined: run_id=poison' in capsys.readouterr().out
    assert main(['--input', str(path), '--run-id', 'unblocked'], store=backend) == 0


def test_cli_quarantine_of_unknown_run_fails_safely_and_input_is_required_otherwise(tmp_path, capsys):
    from scripts.sheets_sync import main
    backend = MemoryStore()
    assert main(['--quarantine-run', 'missing'], store=backend) == 2
    assert 'missing_pending_journal' in capsys.readouterr().out
    import pytest
    with pytest.raises(SystemExit): main([], store=backend)
    with pytest.raises(SystemExit): main(['--quarantine-run', 'x', '--input', 'y'], store=backend)


def test_completed_run_quarantine_reports_the_actionable_reason(tmp_path, capsys):
    from scripts.sheets_sync import main
    path = tmp_path / 'records.json'
    path.write_text(json.dumps(normalized()))
    backend = MemoryStore()
    assert main(['--input', str(path), '--run-id', 'done'], store=backend) == 0
    capsys.readouterr()
    assert main(['--quarantine-run', 'done'], store=backend) == 2
    assert 'sync_failed: run_not_pending' in capsys.readouterr().out
    assert len(backend.tables['Jobs']) == 2


def test_unexpected_writer_failure_is_distinct_from_bad_input_and_sanitized(tmp_path, capsys):
    from scripts.sheets_sync import main
    path = tmp_path / 'records.json'
    path.write_text(json.dumps(normalized()))
    backend = MemoryStore()
    def fail_after_jobs_write(title):
        if title == 'Jobs':
            raise RuntimeError('private workbook detail / unexpected failure')
    backend.after_write = fail_after_jobs_write
    assert main(['--input', str(path), '--run-id', 'unexpected'], store=backend) == 2
    output = capsys.readouterr().out
    assert 'sync_failed: unexpected_sync_error' in output
    assert 'check pending state and lock before another run' in output
    assert 'invalid_sync_input' not in output and 'private workbook' not in output
    assert len(backend.tables['Jobs']) == 2  # failure can follow an applied mutation


def test_missing_input_file_is_reported_before_google_access(tmp_path, monkeypatch, capsys):
    from scripts import sheets_sync
    def unexpected_google_access():
        raise AssertionError('Google must not open for missing input')
    monkeypatch.setattr(sheets_sync, 'open_workbook', unexpected_google_access)
    assert sheets_sync.main(['--input', str(tmp_path / 'missing-private.json')]) == 2
    output = capsys.readouterr().out
    assert 'sync_failed: invalid_sync_input' in output
    assert 'unexpected_sync_error' not in output and 'missing-private' not in output


@pytest.mark.parametrize('error', [ValueError('embedded null byte'), RuntimeError('private user lookup')])
def test_invalid_input_path_resolution_is_sanitized_before_google(
        tmp_path, monkeypatch, capsys, error):
    from pathlib import Path
    from scripts import sheets_sync
    path = str(tmp_path / 'private-input.json')
    original = Path.expanduser
    def invalid_expansion(value):
        if str(value) == path:
            raise error
        return original(value)
    monkeypatch.setattr(Path, 'expanduser', invalid_expansion)
    calls = []
    monkeypatch.setattr(sheets_sync, 'open_workbook', lambda: calls.append('Google'))
    assert sheets_sync.main(['--input', path]) == 2
    output = capsys.readouterr().out
    assert 'sync_failed: invalid_sync_input' in output
    assert 'private' not in output and 'embedded null' not in output
    assert calls == []
