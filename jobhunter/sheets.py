"""One-writer RAW upserts, bounded reconciliation and durable pending recovery."""

from datetime import datetime, timezone
import json
import random
import re
import time
import uuid

from jobhunter.sheet_io import SheetIOError
from jobhunter.sheet_journal import SheetJournal, _stamp
from jobhunter.sheet_lock import SheetLock
from jobhunter.sheet_records import JOB_BATCH_SIZE, JOB_HEADERS, normalize_jobs, plan_jobs, plan_table, reconcile_jobs, table_index

SOURCE_FIELDS = {'Jobs fetched': 'jobs_fetched', 'Valid jobs': 'valid_jobs',
                 'Rejected items': 'rejected_items', 'PM candidates': 'pm_candidates',
                 'Selected': 'selected_for_m0', 'Attempts': 'attempts',
                 'HTTP status': 'http_status', 'Retry after seconds': 'retry_after_seconds'}
SOURCE_HEADERS = ('Source ID', 'Status', 'Last checked', *SOURCE_FIELDS, 'Coverage', 'Error')
RUN_HEADERS = ('Run ID', 'Started', 'Completed', 'Jobs input', 'Jobs unique', 'Status')
SOURCE_STATUSES = {'OK', 'OK-zero-jobs', 'failed', 'blocked', 'needs setup'}
SOURCE_ERRORS = {'', 'timeout', 'transport_error', 'protocol_or_decode_error', 'invalid_json',
                 'retry_delay_exceeds_budget', 'invalid_items_quarantined', 'inconsistent_empty_response',
                 'duplicate_source_id', 'invalid_board_response'}


def _sources(records):
    if not isinstance(records, list) or not records or len(records) > 100:
        raise ValueError('invalid_source_records')
    output = {}
    for item in records:
        if not isinstance(item, dict):
            raise ValueError('invalid_source_records')
        identity, status, stamp = item.get('source_id'), item.get('status'), item.get('captured_at')
        if (not isinstance(identity, str) or not re.fullmatch('[A-Za-z][A-Za-z0-9_.:-]{0,159}', identity)
                or not isinstance(status, str) or status not in SOURCE_STATUSES):
            raise ValueError('invalid_source_records')
        _stamp(stamp)
        record = {'Source ID': identity, 'Status': status, 'Last checked': stamp}
        for header, field in SOURCE_FIELDS.items():
            value = item.get(field)
            if value is None:
                value = ''  # Missing counts remain unknown, never inferred zero.
            elif type(value) is not int or value < 0:
                if header != 'Retry after seconds' or type(value) not in (int, float) or not 0 <= value <= 1e12:
                    raise ValueError('invalid_source_counts')
            record[header] = value
        coverage, error = item.get('coverage', ''), item.get('error') or ''
        if not isinstance(coverage, str) or coverage not in {'', 'unknown', 'complete-response',
                'partial-response', 'unknown-with-rejections', 'complete-response-with-rejections',
                'partial-response-with-rejections'}:
            raise ValueError('invalid_source_coverage')
        if not isinstance(error, str) or (error not in SOURCE_ERRORS and not re.fullmatch('http_[1-5][0-9]{2}', error)):
            raise ValueError('invalid_source_error')
        output[identity] = record | {'Coverage': coverage, 'Error': error}
    return list(output.values())


def _payload(payload):
    if (not isinstance(payload, dict) or set(payload) != {'jobs', 'sources', 'input_count'}
            or type(payload['input_count']) is not int or not 0 <= payload['input_count'] <= JOB_BATCH_SIZE):
        raise ValueError('invalid_pending_payload')
    jobs = normalize_jobs(payload['jobs'])
    if jobs != payload['jobs'] or len(jobs) > payload['input_count']:
        raise ValueError('invalid_pending_payload')
    sources = payload['sources']
    if (not isinstance(sources, list) or len(sources) > 100
            or any(not isinstance(row, dict) or set(row) != set(SOURCE_HEADERS) for row in sources)):
        raise ValueError('invalid_pending_payload')
    raw_sources = []
    for row in sources:
        raw_sources.append({'source_id': row['Source ID'], 'status': row['Status'],
            'captured_at': row['Last checked'], 'coverage': row['Coverage'], 'error': row['Error'],
            **{field: (None if row[header] == '' else row[header]) for header, field in SOURCE_FIELDS.items()}})
    if _sources(raw_sources) != sources:
        raise ValueError('invalid_pending_payload')
    healthy = {s['Source ID'] for s in sources if s['Status'] == 'OK'}
    partial = {s['Source ID'] for s in sources
               if s['Status'] in {'failed', 'blocked'} and s['Error']
               and type(s['Selected']) is int and s['Selected'] > 0
               and type(s['Valid jobs']) is int and s['Valid jobs'] >= s['Selected']
               # A run split into batches carries every source's full Selected total in each batch.
               and sum(job['Source'] == s['Source ID'] for job in jobs) <= s['Selected']}
    if any(job['Source'] not in healthy | partial for job in jobs):
        raise ValueError('job_source_not_successful')
    return payload


def _completed_time(rows, run):
    """Original completion time of a run whose final Run Log row already landed."""
    headers, known = table_index(rows, RUN_HEADERS, 'Run ID')
    if run not in known:
        return None
    values = known[run][1]
    status, done = (values[headers[h]] if headers[h] < len(values) else '' for h in ('Status', 'Completed'))
    return done if status not in ('', 'pending') and isinstance(done, str) and done else None


def _retry(operation, sleep, jitter):
    for attempt in range(3):
        try:
            return operation()
        except SheetIOError as exc:
            if not exc.transient or attempt == 2:
                raise
            delay = max(2 ** attempt + jitter(), exc.retry_after or 0)
            if delay > 60:
                raise ValueError('sheet_retry_delay_exceeds_budget') from None
            sleep(delay)


def prepare_payload(records, source_records):
    return _payload({'jobs': normalize_jobs(records), 'sources': _sources(source_records),
                     'input_count': len(records)})


def _chunks(writes, size):
    batch, weight = [], 0
    for write in writes:
        amount = len(json.dumps(write.values, ensure_ascii=True, allow_nan=False)) + 100
        if amount > 1024 * 1024:
            raise ValueError('sheet_write_too_large')
        if batch and (len(batch) >= size or weight + amount > 1024 * 1024):
            yield batch
            batch, weight = [], 0
        batch.append(write)
        weight += amount
    if batch:
        yield batch


def _table(store, title, planner, size, sleep, jitter, *, verify_only=False):
    def attempt():
        # Every attempt, including uncertain insertion, starts from fresh IDs.
        writes = planner(store.read(title))
        if verify_only and writes:
            raise ValueError('completed_run_changed')
        for batch in _chunks(writes, size):
            store.write(title, batch)
        if planner(store.read(title)):
            raise ValueError('sheet_write_verification_failed')
    _retry(attempt, sleep, jitter)


def sync_jobs(store, records, source_records, *, run_id=None, chunk_size=100,
              now=lambda: datetime.now(timezone.utc).isoformat(), sleep=time.sleep,
              jitter=random.random):
    if type(chunk_size) is not int or not 1 <= chunk_size <= 100:
        raise ValueError('invalid_chunk_size')
    identity = uuid.uuid4().hex if run_id is None else run_id
    if not isinstance(identity, str) or not re.fullmatch('[A-Za-z0-9_-]{1,80}', identity):
        raise ValueError('invalid_run_id')
    payload = prepare_payload(records, source_records)
    started = now()
    _stamp(started)
    lock = SheetLock(store, uuid.uuid4().hex, started)
    lock.acquire()
    failure = None
    try:
        def ensure():
            store.refresh()
            for title, headers in [('Jobs', JOB_HEADERS), ('Sources', SOURCE_HEADERS),
                                   ('Run Log', RUN_HEADERS), ('_State', ('Key', 'Value'))]:
                store.ensure_tab(title, headers, hidden=title == '_State')
        _retry(ensure, sleep, jitter)
        # Reject ambiguous existing tables before journaling or changing jobs.
        plan_jobs(store.read('Jobs'), payload['jobs'])
        plan_table(store.read('Sources'), payload['sources'], SOURCE_HEADERS, 'Source ID')
        table_index(store.read('Run Log'), RUN_HEADERS, 'Run ID')
        journal = SheetJournal(store)

        def deliver(run, data, manifest, verify_only=False):
            _payload(data)
            unique_count = len(reconcile_jobs(store.read('Jobs'), data['jobs']))
            finished = manifest['finished'] if verify_only else _completed_time(store.read('Run Log'), run) or now()
            _stamp(finished)
            status = ('complete' if all(s['Status'] in {'OK', 'OK-zero-jobs'} for s in data['sources'])
                      else 'complete-with-source-failure')
            run_row = {'Run ID': run, 'Started': manifest['started'], 'Completed': finished,
                'Jobs input': data['input_count'], 'Jobs unique': unique_count, 'Status': status}
            if not verify_only:
                # Persist explicit incomplete-run evidence before job mutation.
                # If Google later becomes unavailable, never invent a completed
                # row or make unbounded extra logging attempts after exhaustion.
                # A recovered run whose final row already landed stays completed.
                pending_row = run_row | {'Completed': '', 'Status': 'pending'}
                def plan_pending(rows):
                    headers, known = table_index(rows, RUN_HEADERS, 'Run ID')
                    if run in known:
                        _, values = known[run]
                        column = headers['Status']
                        if column < len(values) and values[column] not in ('', 'pending'):
                            return []
                    return plan_table(rows, [pending_row], RUN_HEADERS, 'Run ID')
                _table(store, 'Run Log', plan_pending, chunk_size, sleep, jitter)
            plans = [('Jobs', lambda rows: plan_jobs(rows, data['jobs'])),
                ('Sources', lambda rows: plan_table(rows, data['sources'], SOURCE_HEADERS, 'Source ID')),
                ('Run Log', lambda rows: plan_table(rows, [run_row], RUN_HEADERS, 'Run ID'))]
            for title, planner in plans:
                _table(store, title, planner, chunk_size, sleep, jitter, verify_only=verify_only)
            if not verify_only:
                _retry(lambda: journal.finish(run, finished), sleep, jitter)
            return unique_count

        pending = _retry(journal.pending, sleep, jitter)
        if len(pending) > 10:
            raise ValueError('too_many_pending_runs')
        for run, data, manifest in pending:
            deliver(run, data, manifest)
        manifest = _retry(lambda: journal.prepare(identity, payload, started), sleep, jitter)
        unique_count = deliver(identity, payload, manifest, verify_only=manifest['state'] == 'done')
        return {'run_id': identity, 'input_jobs': len(records), 'unique_jobs': unique_count,
                'recovered_runs': len(pending)}
    except BaseException as exc:
        failure = exc
        raise
    finally:
        _release(store, lock, failure)


def _release(store, lock, failure):
    if getattr(store, 'mutation_unknown', False):
        if failure is not None:
            failure.add_note('lock_retained_unconfirmed_mutation')
        return
    try:
        lock.release()
    except Exception:
        if failure is not None:
            failure.add_note('lock_cleanup_failed')
        else:
            raise ValueError('writes_verified_lock_release_unconfirmed') from None


def quarantine_run(store, identity, *, now=lambda: datetime.now(timezone.utc).isoformat()):
    """Operator-only: stop a poisoned pending run from blocking later syncs. Keeps all data."""
    if not isinstance(identity, str) or not re.fullmatch('[A-Za-z0-9_-]{1,80}', identity):
        raise ValueError('invalid_run_id')
    started = now()
    _stamp(started)
    lock = SheetLock(store, uuid.uuid4().hex, started)
    lock.acquire()
    failure = None
    try:
        store.refresh()
        moved = SheetJournal(store).quarantine(identity)
        return {'run_id': identity, 'cells_moved': moved}
    except BaseException as exc:
        failure = exc
        raise
    finally:
        _release(store, lock, failure)
