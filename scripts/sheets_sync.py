"""Deliver validated M0 records or failed-source evidence in the cloud only."""

import argparse
import re

from jobhunter.artifacts import read_artifact
from jobhunter.google_auth import open_workbook
from jobhunter.sheet_io import GspreadStore
from jobhunter.sheets import prepare_payload, sync_jobs

SAFE_ERRORS = frozenset('''invalid_sync_input invalid_pending_payload invalid_source_records
invalid_source_counts invalid_source_coverage invalid_source_error invalid_job_batch
invalid_job_fields invalid_job_value invalid_job_id invalid_preliminary_rank invalid_run_id
invalid_chunk_size invalid_pending_journal invalid_journal_timestamp invalid_journal_payload
journal_payload_too_large journal_write_unconfirmed missing_pending_journal run_id_payload_conflict
job_source_not_successful ambiguous_headers missing_headers invalid_existing_row unkeyed_existing_row
duplicate_existing_id writer_locked lock_acquisition_unconfirmed lock_identity_collision invalid_lock_owner
lock_release_unconfirmed lock_ownership_lost lock_acquisition_already_attempted too_many_pending_runs
completed_run_changed sheet_write_verification_failed sheet_retry_delay_exceeds_budget sheet_write_too_large
sheet_request_failed sheet_tls_error sheet_transport_error invalid_sheet_response unapproved_tab
invalid_google_configuration google_workbook_unavailable google_proxy_auth_missing google_workbook_not_found
google_workbook_forbidden google_tls_error google_timeout google_transport_error invalid_json
artifact_too_large invalid_extraction_delivery'''.split())


def main(argv=None, *, store=None):
    parser = argparse.ArgumentParser(description='M0 Python Sheet writer; no source collection.')
    parser.add_argument('--input', required=True)
    parser.add_argument('--run-id')
    parser.add_argument('--chunk-size', type=int, choices=range(1, 101), default=100)
    args = parser.parse_args(argv)
    try:
        payload = read_artifact(args.input)
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
        if code not in SAFE_ERRORS and not re.fullmatch('(sheet|google)_http_[1-5][0-9]{2}', code):
            code = 'invalid_sync_input'
        print(f'sync_failed: {code}; check pending state and lock before another run')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
