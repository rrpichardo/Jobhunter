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


def test_unconfirmed_mutation_retains_lock_and_stops_all_later_writes():
    backend = MemoryStore()
    original = backend.write
    def unresolved(title, writes):
        if title == 'Jobs':
            backend.mutation_unknown = True
            raise ValueError('sheet_mutation_unconfirmed')
        original(title, writes)
    backend.write = unresolved
    with pytest.raises(ValueError, match='sheet_mutation_unconfirmed'): sync(backend, [job()], 'unknown')
    assert backend.owner is not None
    assert len([1 for title, _ in backend.writes if title == 'Sources']) == 0


def test_original_error_is_not_masked_by_lock_cleanup_failure():
    from jobhunter.sheet_io import SheetIOError
    backend = MemoryStore()
    original = backend.write
    def fail(title, writes):
        if title == 'Jobs': raise SheetIOError('sheet_http_429', transient=True)
        original(title, writes)
    backend.write = fail
    backend.drop_lock = lambda: (_ for _ in ()).throw(RuntimeError('cleanup failed'))
    with pytest.raises(SheetIOError, match='sheet_http_429') as caught:
        sync(backend, [job()], 'failed')
    assert 'lock_cleanup_failed' in caught.value.__notes__


def test_verified_write_with_failed_release_reports_that_writes_are_verified():
    backend = MemoryStore()
    backend.drop_lock = lambda: (_ for _ in ()).throw(RuntimeError('cleanup failed'))
    with pytest.raises(ValueError, match='writes_verified_lock_release_unconfirmed'):
        sync(backend, [job()], 'verified')
    assert len(backend.tables['Jobs']) == 2


def test_recovery_after_crash_before_journal_finish_keeps_completed_run_log_row():
    from jobhunter.sheet_journal import SheetJournal
    backend = MemoryStore()
    original = SheetJournal.finish
    def crash(self, identity, finished): raise KeyboardInterrupt()
    SheetJournal.finish = crash
    try:
        with pytest.raises(KeyboardInterrupt): sync(backend, [job()], 'crashed')
    finally:
        SheetJournal.finish = original
    assert backend.tables['Run Log'][1][-1] == 'complete'
    backend.writes.clear()
    sync(backend, [job(2)], 'next')
    statuses = [w.values[0][0] for title, ws in backend.writes if title == 'Run Log'
                for w in ws if w.column == 6 and w.row == 2]
    assert 'pending' not in statuses
    assert backend.tables['Run Log'][1][-1] == 'complete'
    assert backend.tables['Run Log'][1][2] != ''


def poison(backend, identity='poison'):
    from jobhunter.sheet_journal import SheetJournal
    SheetJournal(backend).prepare(identity, {'jobs': [], 'sources': [], 'input_count': 0}, STAMP)
    rows = backend.tables['_State']
    for row in rows[1:]:
        if row[0].endswith('/chunk/0'): row[1] = '{not json'


def test_poisoned_journal_blocks_sync_until_operator_quarantines_it_without_data_loss():
    from jobhunter.sheets import quarantine_run
    backend = MemoryStore()
    sync(backend, [job()], 'first')
    poison(backend)
    with pytest.raises(ValueError, match='invalid_pending_journal'): sync(backend, [job(2)], 'blocked')
    before = [list(r) for r in backend.tables['_State'] if 'poison' in r[0]]
    result = quarantine_run(backend, 'poison', now=lambda: STAMP)
    assert result == {'run_id': 'poison', 'cells_moved': len(before)}
    after = [list(r) for r in backend.tables['_State'] if 'poison' in r[0]]
    assert sorted(v for _, v in after) == sorted(v for _, v in before)  # nothing discarded
    assert all(k.startswith('m0/quarantined/poison/') for k, _ in after)
    assert backend.owner is None
    assert sync(backend, [job(2)], 'unblocked')['recovered_runs'] == 0
    with pytest.raises(ValueError, match='run_id_quarantined'): sync(backend, [], 'poison')


def test_quarantine_requires_an_existing_run_and_the_lock():
    from jobhunter.sheets import quarantine_run
    backend = MemoryStore()
    sync(backend, [job()], 'first')
    with pytest.raises(ValueError, match='missing_pending_journal'):
        quarantine_run(backend, 'nope', now=lambda: STAMP)
    with pytest.raises(ValueError, match='invalid_run_id'):
        quarantine_run(backend, '../x', now=lambda: STAMP)
    backend.owner = 'someone-else'
    with pytest.raises(ValueError, match='writer_locked'):
        quarantine_run(backend, 'first', now=lambda: STAMP)


def test_interrupt_during_job_write_through_the_engine_retains_the_lock():
    # Interrupt the first Jobs write after the lock exists; owner must remain.
    backend = MemoryStore()
    original = backend.write
    def interrupted(title, writes):
        if title == 'Jobs':
            backend.mutation_unknown = True
            raise KeyboardInterrupt()
        original(title, writes)
    backend.write = interrupted
    with pytest.raises(KeyboardInterrupt) as caught: sync(backend, [job()], 'interrupt')
    assert backend.owner is not None
    assert 'lock_retained_unconfirmed_mutation' in caught.value.__notes__
