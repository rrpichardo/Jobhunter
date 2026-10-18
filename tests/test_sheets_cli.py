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
