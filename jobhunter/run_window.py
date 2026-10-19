"""How far back a run looks: 28 days for a manual first run or catch-up, 3 days for the daily routine.

One simple rule. The daily routine always looks back 3 days, and it refuses to run (a manual 28-day catch-up must
come first) when the last complete run started more than about two days ago, or when there has never been one.
Three days against a two-day limit leaves a full extra day of room for scheduler drift and run time, so one missed
day is still covered and no posting can fall between two runs. Nothing here writes anything.
"""

from datetime import datetime, timedelta, timezone

from jobhunter.sheet_records import table_index

MANUAL_DAYS = 28
DAILY_DAYS = 3
MAX_GAP = timedelta(days=2, hours=6)  # two days, plus a little for the scheduler's drift
CLOCK_SKEW = timedelta(minutes=5)  # a recorded time further in the future than this cannot be real
RUN_LOG_HEADERS = ('Run ID', 'Started', 'Completed', 'Status')
COMPLETE = {'complete', 'complete-with-source-failure'}


class CatchUpNeeded(Exception):
    """The daily window would leave a gap; a manual 28-day run must come first."""

    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def _moment(value):
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip())
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def last_complete_start(rows, now):
    """Start time of the most recent complete run in the Run Log rows, or None.

    A row only counts if its times make sense: started before it completed, and neither in the future. A corrupt
    row therefore cannot make an old gap look recent.
    """
    if not rows:
        return None
    headers, identities = table_index(rows, RUN_LOG_HEADERS, 'Run ID')
    best = None
    for _, values in identities.values():
        status = values[headers['Status']] if headers['Status'] < len(values) else ''
        started = _moment(values[headers['Started']] if headers['Started'] < len(values) else '')
        done = _moment(values[headers['Completed']] if headers['Completed'] < len(values) else '')
        if (status in COMPLETE and started and done and started <= done <= now + CLOCK_SKEW
                and (best is None or started > best)):
            best = started
    return best


def window_days(mode, rows, now):
    """(days, note). Raises CatchUpNeeded for the daily mode when the gap would lose postings."""
    if mode == 'manual':
        return MANUAL_DAYS, 'manual run: full 28-day window'
    if mode != 'daily':
        raise ValueError('invalid_run_mode')
    last = last_complete_start(rows, now)
    if last is None:
        raise CatchUpNeeded('no_complete_run')
    if now - last > MAX_GAP:
        raise CatchUpNeeded('last_run_too_old')
    return DAILY_DAYS, f'daily run: {DAILY_DAYS}-day window; last complete run started {last.isoformat()}'
