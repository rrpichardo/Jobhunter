import pytest
from sheet_fakes import MemoryStore


def store():
    result = MemoryStore()
    result.ensure_tab('_State', ['Key', 'Value'])
    return result


def test_journal_roundtrip_spans_cells_and_completion_removes_payload_only():
    from jobhunter.sheet_journal import SheetJournal
    backend = store()
    backend.tables['_State'].append(['social/x/2026-10-17', 'attempted'])
    journal = SheetJournal(backend)
    payload = {'jobs': [{'title': 'x' * 45000}], 'sources': []}
    journal.prepare('run1', payload, '2026-10-17T00:00:00Z')
    pending = journal.pending()
    assert len(pending) == 1 and pending[0][1] == payload
    assert len(backend.writes) == 1
    assert all(len(str(cell)) <= 40000 for row in backend.tables['_State'] for cell in row)
    journal.finish('run1', '2026-10-17T00:01:00Z')
    assert journal.pending() == []
    assert backend.tables['_State'][1] == ['social/x/2026-10-17', 'attempted']
    assert not any('x' * 100 in str(row) for row in backend.tables['_State'])
    assert journal.prepare('run1', payload, '2026-10-18T00:00:00Z')['state'] == 'done'
    with pytest.raises(ValueError, match='run_id_payload_conflict'):
        journal.prepare('run1', {'jobs': []}, '2026-10-18T00:00:00Z')


def test_corrupt_pending_journal_fails_closed_before_jobs_write():
    from jobhunter.sheet_journal import SheetJournal
    backend = store()
    journal = SheetJournal(backend)
    journal.prepare('run1', {'jobs': []}, '2026-10-17T00:00:00Z')
    chunk = next(row for row in backend.tables['_State'] if row[0].endswith('/chunk/0'))
    chunk[1] = 'changed'
    with pytest.raises(ValueError, match='invalid_pending_journal'): journal.pending()
    assert all(title == '_State' for title, _ in backend.writes)


def test_journal_rejects_oversized_payload_and_invalid_run_id():
    from jobhunter.sheet_journal import SheetJournal
    backend = store()
    for identity, payload in [('bad/id', {}), ('good', {'huge': 'x' * (1024 * 1024)})]:
        with pytest.raises(ValueError):
            SheetJournal(backend).prepare(identity, payload, '2026-10-17T00:00:00Z')
    assert not backend.writes


def test_unrelated_numeric_allowance_state_does_not_block_writer_recovery():
    from jobhunter.sheet_journal import SheetJournal
    backend = store()
    backend.tables['_State'].append(['social/x/2026-10-17/count', 1])
    SheetJournal(backend).prepare('run1', {'jobs': []}, '2026-10-17T00:00:00Z')
    assert SheetJournal(backend).pending()[0][0] == 'run1'
    assert backend.tables['_State'][1][1] == 1
