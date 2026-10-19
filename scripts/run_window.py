"""Print how many days back this run should look, and refuse a daily run that would leave a gap.

  uv run --locked python -m scripts.run_window --mode manual   # first run or catch-up: window_days=28
  uv run --locked python -m scripts.run_window --mode daily    # routine: window_days=2, or exit 3

Use the printed number as `--lookback-days` for `hn_hiring candidates` and `source_probe`. Exit 3 means the last
complete run (Run Log) started more than two days ago, or there has never been one: stop and tell the user a manual
28-day run is needed first. Read-only: it reads the Run Log tab, writes nothing and needs no lock.
"""

import argparse
from datetime import datetime, timezone
import re

from jobhunter.artifacts import safe_error_code
from jobhunter.google_auth import open_workbook
from jobhunter.run_window import CatchUpNeeded, window_days
from jobhunter.sheet_io import GspreadStore

EXIT_CATCH_UP = 3


def main(argv=None, *, store=None, now=None) -> int:
    parser = argparse.ArgumentParser(description='Look-back window for this run; reads the Run Log only.')
    parser.add_argument('--mode', required=True, choices=('manual', 'daily'))
    args = parser.parse_args(argv)
    try:
        moment = now() if now else datetime.now(timezone.utc)
        rows = []
        if args.mode == 'daily':  # a manual run never needs the Sheet to choose its window
            backend = GspreadStore(open_workbook()) if store is None else store
            try:
                rows = backend.read('Run Log')
            except KeyError:
                rows = []  # no Run Log tab yet means no run yet
        days, note = window_days(args.mode, rows, moment)
        print(f'window_days={days}')
        print(note)
        return 0
    except CatchUpNeeded as exc:
        print(f'catch_up_needed: {exc.reason}; run by hand with --mode manual (28 days) before the daily routine')
        return EXIT_CATCH_UP
    except Exception as exc:
        code = str(exc)
        if not re.fullmatch(r'(sheet|google)_http_[1-5][0-9]{2}|ambiguous_headers|missing_headers|duplicate_existing_id'
                            r'|unkeyed_existing_row|invalid_existing_row|invalid_run_mode|google_[a-z_]+|sheet_[a-z_]+'
                            r'|invalid_google_configuration', code):
            code = safe_error_code(exc)
        print(f'run_window_failed: {code}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
