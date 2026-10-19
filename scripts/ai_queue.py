"""Tell the routine which free-text items still need the AI, and remember which it has read.

  uv run --locked python -m scripts.ai_queue pull --source hn-who-is-hiring --candidates <file>
      --candidates-sha256 <digest> --output <new file outside checkout>
  (Claude reads the items in that output and writes its extractions; scripts.hn_hiring validate checks them)
  (scripts.sheets_sync delivers the jobs)
  uv run --locked python -m scripts.ai_queue commit --source hn-who-is-hiring --result <file> --result-sha256 <digest>

Cloud-only like the Sheet writer: it needs the workbook and takes the same structural writer lock.
It stores item IDs and times only, never item text, and it never reads any other Sheet tab.
"""

import argparse
import re

from jobhunter.ai_queue import WORK_SAFETY_STOP, commit, pull
from jobhunter.artifacts import read_artifact, safe_error_code, write_artifact
from jobhunter.google_auth import open_workbook
from jobhunter.sheet_io import GspreadStore
from scripts.sheets_sync import SAFE_ERRORS

QUEUE_ERRORS = frozenset('''invalid_queue_source invalid_queue_item invalid_queue_state invalid_queue_limit
invalid_work_artifact'''.split())


def main(argv=None, *, store=None) -> int:
    parser = argparse.ArgumentParser(description='AI read-queue memory in the _State tab; no job writes.')
    commands = parser.add_subparsers(dest='command', required=True)
    first = commands.add_parser('pull')
    first.add_argument('--source', required=True)
    first.add_argument('--candidates', required=True)
    first.add_argument('--candidates-sha256', required=True)
    first.add_argument('--output', required=True, help='New artifact path outside the checkout')
    first.add_argument('--id-field', default='comment_id')
    first.add_argument('--limit', type=int, default=WORK_SAFETY_STOP)
    second = commands.add_parser('commit')
    second.add_argument('--source', required=True)
    second.add_argument('--result', required=True)
    second.add_argument('--result-sha256', required=True)
    args = parser.parse_args(argv)
    try:
        backend = GspreadStore(open_workbook()) if store is None else store
        if args.command == 'pull':
            data = read_artifact(args.candidates, expected_sha256=args.candidates_sha256)
            if not isinstance(data, dict) or not isinstance(data.get('candidates'), list):
                raise ValueError('invalid_work_artifact')
            work, summary = pull(backend, args.source, data['candidates'], id_field=args.id_field, limit=args.limit)
            digest = write_artifact(args.output, {**data, 'candidates': work, 'queue': summary})
            print('queue: ' + ' '.join(f'{k}={v}' for k, v in summary.items()))
            print(f'work_sha256={digest}')
            return 0
        data = read_artifact(args.result, expected_sha256=args.result_sha256)
        if not isinstance(data, dict) or not isinstance(data.get('processed_ids'), list):
            raise ValueError('invalid_work_artifact')
        summary = commit(backend, args.source, data['processed_ids'])
        print('queue: ' + ' '.join(f'{k}={v}' for k, v in summary.items()))
        return 0
    except Exception as exc:
        code = str(exc)
        if code not in SAFE_ERRORS | QUEUE_ERRORS and not re.fullmatch('(sheet|google)_http_[1-5][0-9]{2}', code):
            code = safe_error_code(exc)
        print(f'queue_failed: {code}; check the writer lock before another run')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
