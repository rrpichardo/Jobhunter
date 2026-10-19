"""Remember which free-text items the AI has already read, so each daily run reads only NEW ones.

Hacker News comments, alert emails, newsletters and social posts are messy text that Claude must read.
The same item reappears every day while it stays inside the lookback window, so without a memory the
routine would re-read it daily. This module keeps that memory in the hidden `_State` tab:

    queue/<source>/pending/<item id>   {"at": <first seen>}   seen, not yet read
    queue/<source>/done/<item id>      {"at": <read at>}      read; skipped from now on

A cleared (empty) Value means the row no longer applies; rows are never deleted. Rows live under their own
`queue/` prefix, which the delivery journal ignores. All writes hold the structural writer lock, are written
in bounded chunks and are verified by reading back. This is recovery state, not a second database and not
an atomic lock. Item text is never stored here, only IDs and times.

Order of a run: pull (what is left to read) -> Claude reads -> validate -> deliver jobs -> commit (mark read).
Committing last means a crash re-reads some items next run; duplicate jobs collapse by Job ID, so an item is
never lost, only possibly read twice.
"""

from datetime import datetime, timezone
import json
import random
import re
import time
import uuid

from jobhunter.sheet_journal import STATE_HEADERS, _stamp
from jobhunter.sheet_lock import SheetLock
from jobhunter.sheet_records import plan_table, table_index
from jobhunter.sheets import _release, _retry, _table

PREFIX = 'queue/'
SOURCE = re.compile(r'[a-z][a-z0-9-]{0,60}')
ITEM = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,119}')
# Generous safety stop on items handed to the AI in one run: our own guess, not an Anthropic limit.
# Items past it stay pending (oldest first) and are counted in the summary; tune after measuring volume.
WORK_SAFETY_STOP = 1000


def _check(source, items):
    if not isinstance(source, str) or not SOURCE.fullmatch(source):
        raise ValueError('invalid_queue_source')
    if not isinstance(items, list) or any(not isinstance(i, str) or not ITEM.fullmatch(i) for i in items):
        raise ValueError('invalid_queue_item')
    if len(set(items)) != len(items):
        raise ValueError('invalid_queue_item')


def _key(source, kind, item):
    return f'{PREFIX}{source}/{kind}/{item}'


def _read(rows, source):
    """({pending id: first seen}, {done id: read at}) for one source from the _State rows."""
    headers, identities = table_index(rows, STATE_HEADERS, 'Key')
    pending, done = {}, {}
    start = f'{PREFIX}{source}/'
    for key, (_, values) in identities.items():
        if not key.startswith(start):
            continue
        value = values[headers['Value']] if headers['Value'] < len(values) else ''
        if value == '':
            continue  # cleared
        parts = key[len(start):].split('/')
        try:
            stamp = json.loads(value)['at']
        except (ValueError, TypeError, KeyError):
            raise ValueError('invalid_queue_state') from None
        if len(parts) != 2 or parts[0] not in {'pending', 'done'} or not ITEM.fullmatch(parts[1]):
            raise ValueError('invalid_queue_state')
        _stamp(stamp)
        (pending if parts[0] == 'pending' else done)[parts[1]] = stamp
    return pending, done


def _row(source, kind, item, stamp):
    return {'Key': _key(source, kind, item), 'Value': json.dumps({'at': stamp}, sort_keys=True)}


def _cleared(source, kind, item):
    return {'Key': _key(source, kind, item), 'Value': ''}


def plan_pull(rows, source, candidates, now, *, id_field='comment_id', limit=WORK_SAFETY_STOP):
    """Pure plan: (items to read now, records to write, summary). Candidates are today's fetched items."""
    ids = [c[id_field] for c in candidates]
    _check(source, ids)
    pending, done = _read(rows, source)
    unread = [c for c in candidates if c[id_field] not in done]
    unread.sort(key=lambda c: (pending.get(c[id_field], now), c.get('created_at', ''), c[id_field]))  # oldest waiting first
    work, held = unread[:limit], unread[limit:]
    today = set(ids)
    records = [_row(source, 'pending', c[id_field], now) for c in unread if c[id_field] not in pending]
    expired = [i for i in pending if i not in today and i not in done]
    records += [_cleared(source, 'pending', i) for i in expired]  # the item left the window or vanished
    oldest = min((pending.get(c[id_field], now) for c in unread), default=None)
    age_days = (datetime.fromisoformat(now) - datetime.fromisoformat(oldest)).days if oldest else 0
    summary = {'source_id': source, 'candidates_today': len(candidates), 'already_read': len(candidates) - len(unread),
               'new_today': sum(c[id_field] not in pending for c in unread), 'to_read_now': len(work),
               'held_by_safety_stop': len(held), 'expired_unread': len(expired), 'oldest_unread_age_days': age_days}
    return work, records, summary


def plan_commit(rows, source, processed, now):
    """Pure plan: mark processed items read and clear their pending rows."""
    _check(source, processed)
    pending, done = _read(rows, source)
    records = []
    for item in processed:
        if item not in done:
            records.append(_row(source, 'done', item, now))
        if item in pending:
            records.append(_cleared(source, 'pending', item))
    return records, {'source_id': source, 'marked_read': sum(i not in done for i in processed)}


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


def pull(store, source, candidates, *, id_field='comment_id', limit=WORK_SAFETY_STOP,
         now=lambda: datetime.now(timezone.utc).isoformat(), sleep=time.sleep, jitter=random.random):
    if type(limit) is not int or limit < 1:
        raise ValueError('invalid_queue_limit')

    def operation(stamp):
        work, records, summary = plan_pull(store.read('_State'), source, candidates, stamp, id_field=id_field, limit=limit)
        _table(store, '_State', lambda rows: plan_table(rows, records, STATE_HEADERS, 'Key'), 100, sleep, jitter)
        return work, summary
    return _locked(store, operation, now, sleep, jitter)


def commit(store, source, processed, *, now=lambda: datetime.now(timezone.utc).isoformat(),
           sleep=time.sleep, jitter=random.random):
    def operation(stamp):
        records, summary = plan_commit(store.read('_State'), source, processed, stamp)
        _table(store, '_State', lambda rows: plan_table(rows, records, STATE_HEADERS, 'Key'), 100, sleep, jitter)
        return summary
    return _locked(store, operation, now, sleep, jitter)
