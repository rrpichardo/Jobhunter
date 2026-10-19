"""Reserve, close out or look up the daily live-collection allowance for LinkedIn or X.

  uv run --locked python -m scripts.allowance reserve --source linkedin-login --run-id <run>
  uv run --locked python -m scripts.allowance finish  --source linkedin-login --run-id <run> --outcome ok
  uv run --locked python -m scripts.allowance status  --source linkedin-login

`reserve` must succeed (exit 0) before any live request to that site. Exit 3 means today's allowance is already
spent: collect nothing and say so in the report. Any other non-zero exit means the reservation is unknown:
also collect nothing. Cloud-only, like the Sheet writer.
"""

import argparse
import re

from jobhunter.allowance import AllowanceSpent, OUTCOMES, SOURCES, finish, reserve, status
from jobhunter.artifacts import safe_error_code
from jobhunter.google_auth import open_workbook
from jobhunter.sheet_io import GspreadStore
from scripts.sheets_sync import SAFE_ERRORS

ALLOWANCE_ERRORS = frozenset('''invalid_allowance_source invalid_allowance_outcome invalid_allowance_state
invalid_allowance_time allowance_not_reserved invalid_run_id'''.split())
EXIT_SPENT = 3


def main(argv=None, *, store=None) -> int:
    parser = argparse.ArgumentParser(description='Daily social allowance in the _State tab; no job writes.')
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('reserve', 'finish', 'status'):
        sub = commands.add_parser(name)
        sub.add_argument('--source', required=True, choices=sorted(SOURCES))
        if name != 'status':
            sub.add_argument('--run-id', required=True)
        if name == 'finish':
            sub.add_argument('--outcome', required=True, choices=sorted(OUTCOMES))
    args = parser.parse_args(argv)
    try:
        backend = GspreadStore(open_workbook()) if store is None else store
        if args.command == 'reserve':
            print(f'allowance_reserved: source={args.source} day={reserve(backend, args.source, args.run_id)}')
        elif args.command == 'finish':
            print(f'allowance_closed: source={args.source} day={finish(backend, args.source, args.run_id, args.outcome)} '
                  f'outcome={args.outcome}')
        else:
            day, state = status(backend, args.source)
            print(f'allowance_status: source={args.source} day={day} '
                  + ('available' if state is None else f"spent state={state['state']} run={state['run']}"))
        return 0
    except AllowanceSpent:
        print(f'allowance_spent: {args.source} already used today (America/New_York); collect nothing')
        return EXIT_SPENT
    except Exception as exc:
        code = str(exc)
        if code not in SAFE_ERRORS | ALLOWANCE_ERRORS and not re.fullmatch('(sheet|google)_http_[1-5][0-9]{2}', code):
            code = safe_error_code(exc)
        print(f'allowance_failed: {code}; treat the allowance as spent and collect nothing')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
