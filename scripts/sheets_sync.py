"""Deliver validated M0 records or failed-source evidence in the cloud only."""

import argparse
import re
import time
import uuid

from jobhunter.artifacts import SYNC_MAX_BYTES, read_artifact
from jobhunter.google_auth import open_workbook
from jobhunter.sheet_io import GspreadStore
from jobhunter.sheet_records import JOB_BATCH_SIZE
from jobhunter.sheets import prepare_payload, quarantine_run, sync_jobs

# Each batch reads and writes several tabs; pausing between batches keeps a large backfill under the
# Sheets per-minute quota. A quota error is still retried and a rerun resumes at the first unfinished batch.
BATCH_PAUSE_SECONDS = 2.0

SAFE_ERRORS = frozenset('''invalid_sync_input invalid_pending_payload invalid_source_records
invalid_source_counts invalid_source_coverage invalid_source_error invalid_job_batch
invalid_job_fields invalid_job_value invalid_job_id invalid_preliminary_rank invalid_run_id
invalid_chunk_size invalid_pending_journal invalid_journal_timestamp invalid_journal_payload
journal_payload_too_large journal_write_unconfirmed missing_pending_journal run_id_payload_conflict
job_source_not_successful ambiguous_headers missing_headers invalid_existing_row unkeyed_existing_row
duplicate_existing_id writer_locked lock_acquisition_unconfirmed lock_identity_collision invalid_lock_owner
ambiguous_existing_job_identity
lock_release_unconfirmed lock_ownership_lost lock_acquisition_already_attempted too_many_pending_runs
completed_run_changed sheet_write_verification_failed sheet_retry_delay_exceeds_budget sheet_write_too_large
sheet_mutation_unconfirmed writer_lock_required writes_verified_lock_release_unconfirmed
sheet_request_failed sheet_tls_error sheet_transport_error invalid_sheet_response unapproved_tab
invalid_google_configuration google_workbook_unavailable google_proxy_auth_missing google_workbook_not_found
google_workbook_forbidden google_tls_error google_timeout google_transport_error invalid_json
artifact_too_large artifact_must_be_outside_checkout invalid_extraction_delivery run_id_quarantined run_not_pending'''.split())


def _deliver_many(args, payload, store):
    """Schema 2: many sources and their jobs in one locked run. Exit 0 once readback verifies;
    failed, blocked and needs-setup sources are recorded as evidence, not treated as sync failure."""
    sources, jobs = payload.get('sources'), payload.get('jobs')
    if not isinstance(sources, list) or not isinstance(jobs, list) or not sources:
        raise ValueError('invalid_sync_input')
    if args.run_id is not None and not re.fullmatch('[A-Za-z0-9_-]{1,80}', args.run_id):
        raise ValueError('invalid_run_id')
    delivered = {}
    for job in jobs:
        if not isinstance(job, dict) or not isinstance(job.get('Source'), str):
            raise ValueError('invalid_job_fields')
        delivered[job['Source']] = delivered.get(job['Source'], 0) + 1
    extraction = payload.get('extraction')
    if jobs and (not isinstance(extraction, dict) or extraction.get('status') != 'complete'
                 or extraction.get('selected') != len(jobs) or extraction.get('validated') != len(jobs)):
        raise ValueError('invalid_extraction_delivery')
    for source in sources:
        if not isinstance(source, dict) or not isinstance(source.get('source_id'), str):
            raise ValueError('invalid_source_records')
        if source.get('selected_for_m0') != delivered.pop(source['source_id'], 0):
            raise ValueError('invalid_extraction_delivery')
    if delivered:  # a job whose source has no record
        raise ValueError('invalid_extraction_delivery')
    # Every job is delivered. A large run is split into recoverable batches, each its own journaled run
    # (<run id>-b001, -b002, ...) carrying the full source totals; one batch keeps the plain run id.
    batches = [jobs[start:start + JOB_BATCH_SIZE] for start in range(0, len(jobs), JOB_BATCH_SIZE)] or [[]]
    base = args.run_id or uuid.uuid4().hex
    if len(batches) > 1 and len(base) > 75:  # leaves room for the -bNNN suffix within 80 characters
        raise ValueError('invalid_run_id')
    run_ids = [base] if len(batches) == 1 else [f'{base}-b{number:03d}' for number in range(1, len(batches) + 1)]
    for batch in batches:  # validate everything before opening a Google connection
        prepare_payload(batch, sources)
    backend = GspreadStore(open_workbook()) if store is None else store
    results = []
    for number, (batch, run_id) in enumerate(zip(batches, run_ids)):
        if number:
            time.sleep(BATCH_PAUSE_SECONDS)
        results.append(sync_jobs(backend, batch, sources, run_id=run_id, chunk_size=args.chunk_size))
    problems = sum(source['status'] in {'failed', 'blocked'} for source in sources)
    print(f"sync_verified: run_id={base} batches={len(batches)} "
          f"unique_jobs={sum(r['unique_jobs'] for r in results)} sources={len(sources)} "
          f"recovered_runs={sum(r['recovered_runs'] for r in results)}")
    print(f'source_problems_recorded={problems}')
    return 0


def main(argv=None, *, store=None):
    parser = argparse.ArgumentParser(description='M0 Python Sheet writer; no source collection.')
    parser.add_argument('--input')
    parser.add_argument('--quarantine-run', metavar='RUN_ID',
                        help='operator only: move a poisoned pending run out of recovery, keeping its data')
    parser.add_argument('--run-id')
    parser.add_argument('--chunk-size', type=int, choices=range(1, 101), default=100)
    args = parser.parse_args(argv)
    if (args.input is None) == (args.quarantine_run is None):
        parser.error('give exactly one of --input or --quarantine-run')
    try:
        if args.quarantine_run is not None:
            backend = GspreadStore(open_workbook()) if store is None else store
            result = quarantine_run(backend, args.quarantine_run)
            print(f"quarantined: run_id={result['run_id']} cells_moved={result['cells_moved']}; "
                  'data kept under m0/quarantined/ in _State')
            return 0
        try:
            payload = read_artifact(args.input, max_bytes=SYNC_MAX_BYTES)
        except (OSError, ValueError, RuntimeError) as exc:
            if isinstance(exc, ValueError) and str(exc) in SAFE_ERRORS:
                raise  # retain specific JSON, size and checkout-path diagnostics
            raise ValueError('invalid_sync_input') from None
        if isinstance(payload, dict) and payload.get('schema_version') == 2:
            return _deliver_many(args, payload, store)
        if (not isinstance(payload, dict) or type(payload.get('schema_version')) is not int
                or payload['schema_version'] != 1 or not isinstance(payload.get('source'), dict)
                or not isinstance(payload.get('jobs'), list)):
            raise ValueError('invalid_sync_input')
        source, jobs = payload['source'], payload['jobs']
        if jobs:
            extraction = payload.get('extraction')
            if (not isinstance(extraction, dict) or extraction.get('status') != 'complete'
                    or type(extraction.get('selected')) is not int
                    or type(extraction.get('validated')) is not int
                    or extraction['selected'] != len(jobs) or extraction['validated'] != len(jobs)
                    or source.get('selected_for_m0') != len(jobs)):
                raise ValueError('invalid_extraction_delivery')
        elif source.get('status') == 'OK':
            raise ValueError('invalid_extraction_delivery')
        if args.run_id is not None and not re.fullmatch('[A-Za-z0-9_-]{1,80}', args.run_id):
            raise ValueError('invalid_run_id')
        # Validate all proposed facts before opening a Google connection.
        prepare_payload(jobs, [source])
        backend = GspreadStore(open_workbook()) if store is None else store
        result = sync_jobs(backend, jobs, [source], run_id=args.run_id, chunk_size=args.chunk_size)
        print(f"sync_verified: run_id={result['run_id']} unique_jobs={result['unique_jobs']} recovered_runs={result['recovered_runs']}")
        if source['status'] not in {'OK', 'OK-zero-jobs'}:
            print('source_failure_recorded')
            return 2
        return 0
    except KeyboardInterrupt:
        print('sync_interrupted: pending work or a lock may require recovery')
        return 130
    except Exception as exc:
        code = str(exc)
        if code == 'writes_verified_lock_release_unconfirmed':
            print('writes_verified: lock_release_unconfirmed; operator recovery required')
            return 2
        if 'lock_cleanup_failed' in getattr(exc, '__notes__', []):
            print('lock_cleanup_failed: inspect lock before retry')
        if code not in SAFE_ERRORS and not re.fullmatch('(sheet|google)_http_[1-5][0-9]{2}', code):
            code = 'unexpected_sync_error'
        print(f'sync_failed: {code}; check pending state and lock before another run')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
