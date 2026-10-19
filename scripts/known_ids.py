"""List the Job IDs already in the Jobs tab, so detail-page sources skip pages they already delivered.

  uv run --locked python -m scripts.known_ids --output <new file outside checkout>
  uv run --locked python -m scripts.source_probe ... --known-ids <file> --known-ids-sha256 <digest>

Read-only: it reads the Jobs tab once and keeps only the Job ID column. It writes nothing to the Sheet and
needs no lock. A skipped job is not refreshed on later runs (its details are unchanged); that is the price of
not reopening hundreds of pages every day.
"""

import argparse
import re

from jobhunter.artifacts import safe_error_code, write_artifact
from jobhunter.google_auth import open_workbook
from jobhunter.sheet_io import GspreadStore
from jobhunter.sheet_records import table_index


def known_job_ids(rows):
    _, identities = table_index(rows, ('Job ID',), 'Job ID')
    return sorted(identities)


def main(argv=None, *, store=None) -> int:
    parser = argparse.ArgumentParser(description='Job IDs already delivered; reads one tab, writes no Sheet.')
    parser.add_argument('--output', required=True, help='New artifact path outside the checkout')
    args = parser.parse_args(argv)
    try:
        backend = GspreadStore(open_workbook()) if store is None else store
        ids = known_job_ids(backend.read('Jobs'))
        digest = write_artifact(args.output, {'schema_version': 1, 'job_ids': ids})
        print(f'known_job_ids={len(ids)}')
        print(f'known_ids_sha256={digest}')
        return 0
    except Exception as exc:
        code = str(exc)
        if not re.fullmatch(r'(sheet|google)_http_[1-5][0-9]{2}|ambiguous_headers|missing_headers|duplicate_existing_id'
                            r'|unkeyed_existing_row|invalid_existing_row|google_[a-z_]+|sheet_[a-z_]+|invalid_google_configuration', code):
            code = safe_error_code(exc)
        print(f'known_ids_failed: {code}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
