"""One live collection per social source per America/New_York day, reserved BEFORE any live request.

LinkedIn and X can restrict a dedicated account, so the plan allows at most one live collection per source per
New York calendar day. A manual "Run now" uses that day's allowance too. The reservation is a row in the hidden
`_State` tab, written under the structural writer lock and read back, before the collector touches the site:

    allowance/<source>/<YYYY-MM-DD>   {"state": "reserved|ok|zero|failed|blocked", "at": <iso>, "run": <run id>}

`_State` is recovery state, not an atomic lock. Two safeguards stand in for atomicity: the writer lock around the
read-check-write, and failing closed. If the reservation write has an unknown outcome the caller must treat the
day's allowance as spent and must not collect. A failed, blocked or empty attempt still counts; only the next
New York day restores the allowance. Rows hold a source id, a day, a run id and an outcome word. Never a cookie,
a query, a post or an account name.

The New York day comes from US daylight-saving rules (second Sunday in March to first Sunday in November, switching
at 02:00 local) so no time-zone database is needed on any platform.
"""

from datetime import datetime, timedelta, timezone
import json
import random
import re
import time
import uuid

from jobhunter.sheet_journal import STATE_HEADERS, _stamp
from jobhunter.sheet_lock import SheetLock
from jobhunter.sheet_records import plan_table, table_index
from jobhunter.sheets import _release, _retry, _table

PREFIX = 'allowance/'
SOURCES = frozenset({'linkedin-login', 'x-twscrape'})
OUTCOMES = frozenset({'ok', 'zero', 'failed', 'blocked'})
RUN_ID = re.compile(r'[A-Za-z0-9_-]{1,80}')


class AllowanceSpent(ValueError):
    """Today's allowance for this source is already reserved or used."""


def _nth_sunday(year, month, n):
    first = datetime(year, month, 1)
    return first + timedelta(days=(6 - first.weekday()) % 7 + 7 * (n - 1))


def new_york_day(moment):
    """The America/New_York calendar date (YYYY-MM-DD) of an aware datetime."""
    if moment.tzinfo is None:
        raise ValueError('invalid_allowance_time')
    utc = moment.astimezone(timezone.utc).replace(tzinfo=None)
    starts = _nth_sunday(utc.year, 3, 2) + timedelta(hours=7)    # 02:00 EST
    ends = _nth_sunday(utc.year, 11, 1) + timedelta(hours=6)     # 02:00 EDT
    offset = -4 if starts <= utc < ends else -5
    return (utc + timedelta(hours=offset)).date().isoformat()


def _key(source, day):
    return f'{PREFIX}{source}/{day}'


def _check(source, run_id):
    if source not in SOURCES:
        raise ValueError('invalid_allowance_source')
    if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
        raise ValueError('invalid_run_id')


def _state(rows, key):
    headers, identities = table_index(rows, STATE_HEADERS, 'Key')
    if key not in identities:
        return None
    values = identities[key][1]
    value = values[headers['Value']] if headers['Value'] < len(values) else ''
    if value == '':
        return None
    try:
        data = json.loads(value)
        if (set(data) != {'state', 'at', 'run'} or data['state'] not in OUTCOMES | {'reserved'}
                or not RUN_ID.fullmatch(data['run'])):
            raise ValueError
        _stamp(data['at'])
    except (ValueError, TypeError, KeyError):
        raise ValueError('invalid_allowance_state') from None
    return data


def _record(source, day, state, at, run):
    return {'Key': _key(source, day), 'Value': json.dumps({'state': state, 'at': at, 'run': run}, sort_keys=True)}


def _locked(store, operation, now, sleep, jitter):
    started = now()
    _stamp(started)
    lock = SheetLock(store, uuid.uuid4().hex, started)
    lock.acquire()
    failure = None
    try:
        _retry(lambda: (store.refresh(), store.ensure_tab('_State', ('Key', 'Value'), hidden=True)), sleep, jitter)
        return operation(started)
    except BaseException as exc:
        failure = exc
        raise
    finally:
        _release(store, lock, failure)


def _write(store, record, sleep, jitter):
    _table(store, '_State', lambda rows: plan_table(rows, [record], STATE_HEADERS, 'Key'), 100, sleep, jitter)


def reserve(store, source, run_id, *, now=lambda: datetime.now(timezone.utc).isoformat(),
            sleep=time.sleep, jitter=random.random):
    """Spend today's allowance. Raises AllowanceSpent if it is gone. Returns the New York day."""
    _check(source, run_id)

    def operation(stamp):
        day = new_york_day(datetime.fromisoformat(stamp))
        existing = _state(store.read('_State'), _key(source, day))
        if existing is not None:
            raise AllowanceSpent('allowance_spent')
        _write(store, _record(source, day, 'reserved', stamp, run_id), sleep, jitter)
        return day
    return _locked(store, operation, now, sleep, jitter)


def finish(store, source, run_id, outcome, *, now=lambda: datetime.now(timezone.utc).isoformat(),
           sleep=time.sleep, jitter=random.random):
    """Record how the reserved attempt ended. The allowance stays spent whatever the outcome."""
    _check(source, run_id)
    if outcome not in OUTCOMES:
        raise ValueError('invalid_allowance_outcome')

    def operation(stamp):
        day = new_york_day(datetime.fromisoformat(stamp))
        existing = _state(store.read('_State'), _key(source, day))
        if existing is None or existing['run'] != run_id:
            raise ValueError('allowance_not_reserved')
        _write(store, _record(source, day, outcome, stamp, run_id), sleep, jitter)
        return day
    return _locked(store, operation, now, sleep, jitter)


def status(store, source, *, now=lambda: datetime.now(timezone.utc)):
    """Read-only: (day, state dict or None). Takes no lock and writes nothing."""
    if source not in SOURCES:
        raise ValueError('invalid_allowance_source')
    day = new_york_day(now())
    return day, _state(store.read('_State'), _key(source, day))
