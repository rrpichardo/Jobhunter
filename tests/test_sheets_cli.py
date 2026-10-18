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
