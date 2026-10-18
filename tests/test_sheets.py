import pytest
from sheet_fakes import MemoryStore
from test_sheet_records import job

STAMP = '2026-10-17T00:00:00+00:00'


def sources(status='OK'):
    return [{'source_id': 'greenhouse:example', 'status': status, 'captured_at': STAMP,
             'jobs_fetched': 10, 'selected_for_m0': 7, 'error': ''}]


def sync(backend, records, identity, **kwargs):
    from jobhunter.sheets import sync_jobs
    return sync_jobs(backend, records, sources(), run_id=identity, now=lambda: STAMP,
                     sleep=lambda delay: None, jitter=lambda: 0, **kwargs)


def test_multiple_chunks_repeat_sync_preserves_notes_and_sorted_rows():
    backend = MemoryStore()
    records = [job(i) for i in range(1, 8)]
    assert sync(backend, records, 'run1', chunk_size=2)['unique_jobs'] == 7
    headers = backend.tables['Jobs'][0]
    for row in backend.tables['Jobs'][1:]:
        row[headers.index('Notes')] = 'keep note'
        row[headers.index('Status')] = 'Applied'
        row[headers.index('My rating')] = '5'
    backend.tables['Jobs'][1:] = list(reversed(backend.tables['Jobs'][1:]))
    sync(backend, [r | {'Job title': '=literal'} for r in records], 'run2', chunk_size=2)
    sync(backend, [r | {'Job title': '=literal'} for r in records], 'run2', chunk_size=2)
    assert len(backend.tables['Jobs']) == 8
    for row in backend.tables['Jobs'][1:]:
        assert row[headers.index('Notes')] == 'keep note'
        assert row[headers.index('Status')] == 'Applied'
        assert row[headers.index('My rating')] == '5'
        assert row[headers.index('Job title')] == '=literal'
    assert len(backend.tables['Run Log']) == 3
    assert backend.owner is None
    assert len([w for tab, w in backend.writes if tab == 'Jobs']) >= 4


def test_insert_succeeds_but_reports_timeout_reconciles_before_any_retry():
    from jobhunter.sheet_io import SheetIOError
    backend = MemoryStore()
    fired = []
    def timeout_after_success(title):
        if title == 'Jobs' and not fired:
            fired.append(len(backend.reads))
            raise SheetIOError('sheet_transport_error', transient=True)
    backend.after_write = timeout_after_success
    sync(backend, [job(1), job(2)], 'run1')
    assert len(backend.tables['Jobs']) == 3
    assert len([w for tab, w in backend.writes if tab == 'Jobs']) == 1
    assert backend.reads[fired[0]:].count('Jobs') >= 1


@pytest.mark.parametrize('stop_table', ['_State', 'Jobs', 'Run Log'])
def test_interruption_replays_pending_work_and_does_not_duplicate(stop_table):
    from jobhunter.sheet_journal import SheetJournal
    backend = MemoryStore()
    fired = []
    def interrupt(title):
        if title == stop_table and not fired:
            fired.append(True)
            raise KeyboardInterrupt()
    backend.after_write = interrupt
    with pytest.raises(KeyboardInterrupt): sync(backend, [job()], 'interrupted')
    assert backend.owner is None
    backend.after_write = None
    result = sync(backend, [job(2)], 'next')
    assert len(backend.tables['Jobs']) == 3
    assert SheetJournal(backend).pending() == []
    assert result['recovered_runs'] == 1


def test_failed_source_is_recorded_without_becoming_closed_or_zero_success():
    from jobhunter.sheets import sync_jobs
    backend = MemoryStore()
    sync_jobs(backend, [], sources('failed'), run_id='failed', now=lambda: STAMP)
    assert backend.tables['Sources'][1][1] == 'failed'
    assert 'complete-with-source-failure' in backend.tables['Run Log'][1]
    assert backend.tables['Jobs'] == [backend.tables['Jobs'][0]]


def test_invalid_existing_jobs_abort_before_journal_or_job_mutation():
    from jobhunter.sheet_records import JOB_HEADERS
    backend = MemoryStore()
    backend.tables['Jobs'] = [list(JOB_HEADERS), list(job().values()), list(job().values())]
    with pytest.raises(ValueError, match='duplicate_existing_id'): sync(backend, [job(2)], 'bad')
    assert all(tab != 'Jobs' for tab, _ in backend.writes)
    assert backend.owner is None


def test_transient_failure_is_capped_and_keeps_pending_recovery_data():
    from jobhunter.sheets import sync_jobs
    from jobhunter.sheet_io import SheetIOError
    from jobhunter.sheet_journal import SheetJournal
    backend = MemoryStore()
    writes, waits = [], []
    original = backend.write
    def failed_write(title, data):
        if title == 'Jobs':
            writes.append(title)
            raise SheetIOError('sheet_http_503', transient=True, retry_after=4)
        original(title, data)
    backend.write = failed_write
    with pytest.raises(SheetIOError):
        sync_jobs(backend, [job()], sources(), run_id='failed', now=lambda: STAMP,
                  sleep=waits.append, jitter=lambda: 0)
    assert writes == ['Jobs'] * 3 and waits == [4, 4]
    assert len(SheetJournal(backend).pending()) == 1 and backend.owner is None


def test_long_server_delay_stops_instead_of_retrying_early():
    from jobhunter.sheets import sync_jobs
    from jobhunter.sheet_io import SheetIOError
    backend = MemoryStore()
    original = backend.write
    writes, waits = [], []
    def failed_write(title, data):
        if title == 'Jobs':
            writes.append(title)
            raise SheetIOError('sheet_http_429', transient=True, retry_after=61)
        original(title, data)
    backend.write = failed_write
    with pytest.raises(ValueError, match='sheet_retry_delay_exceeds_budget'):
        sync_jobs(backend, [job()], sources(), run_id='failed', now=lambda: STAMP, sleep=waits.append)
    assert writes == ['Jobs'] and waits == []


def test_empty_source_inventory_is_not_reported_as_success():
    from jobhunter.sheets import sync_jobs
    with pytest.raises(ValueError, match='invalid_source_records'):
        sync_jobs(MemoryStore(), [], [], run_id='empty', now=lambda: STAMP)


def test_a_failed_write_leaves_an_explicit_pending_run_log():
    from jobhunter.sheet_io import SheetIOError
    backend = MemoryStore()
    original = backend.write
    def fail(title, writes):
        if title == 'Jobs': raise SheetIOError('sheet_http_503', transient=True)
        original(title, writes)
    backend.write = fail
    with pytest.raises(SheetIOError): sync(backend, [job()], 'pending')
    assert len(backend.tables['Run Log']) == 2
    assert backend.tables['Run Log'][1][-1] == 'pending'
    assert backend.tables['Run Log'][1][2] == ''
