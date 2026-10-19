"""Sheets read quota (HTTP 429) is per minute: wait it out, never repeat a create or delete, never lose the lock."""

import pytest

from jobhunter.sheet_io import SheetIOError
from jobhunter.sheet_lock import SheetLock
from jobhunter import sheets
from sheet_fakes import MemoryStore


def transient(code='sheet_http_429', **kwargs):
    return SheetIOError(code, transient=True, **kwargs)


class FlakyOwner(MemoryStore):
    """Fails the first N lock_owner reads with a quota error."""
    def __init__(self, failures):
        super().__init__()
        self.failures, self.reads_attempted, self.creates, self.deletes = failures, 0, 0, 0

    def create_lock(self, owner, started):
        self.creates += 1
        super().create_lock(owner, started)

    def drop_lock(self):
        self.deletes += 1
        super().drop_lock()

    def lock_owner(self):
        self.reads_attempted += 1
        if self.failures:
            self.failures -= 1
            raise transient()
        return super().lock_owner()


def test_acquire_waits_out_two_quota_errors_and_still_creates_the_lock_exactly_once():
    store, waits = FlakyOwner(2), []
    lock = SheetLock(store, 'me', 'now', sleep=waits.append)
    lock.acquire()
    assert lock.held and waits == [20, 40] and store.creates == 1


def test_release_waits_out_quota_errors_and_deletes_exactly_once():
    store, waits = FlakyOwner(0), []
    lock = SheetLock(store, 'me', 'now', sleep=waits.append)
    lock.acquire()
    store.failures = 2
    lock.release()
    assert waits == [20, 40] and store.deletes == 1 and store.owner is None


def test_a_third_quota_error_still_fails_closed_and_leaves_the_lock_in_place():
    store, waits = FlakyOwner(0), []
    lock = SheetLock(store, 'me', 'now', sleep=waits.append)
    lock.acquire()
    store.failures = 3
    with pytest.raises(ValueError, match='lock_release_unconfirmed'):
        lock.release()
    assert waits == [20, 40] and store.deletes == 0 and store.owner == 'me'


def test_a_non_transient_read_error_is_not_retried():
    store, waits = FlakyOwner(0), []

    def broken():
        store.reads_attempted += 1
        raise SheetIOError('sheet_http_403')
    store.lock_owner = broken
    with pytest.raises(ValueError, match='lock_acquisition_unconfirmed'):
        SheetLock(store, 'me', 'now', sleep=waits.append).acquire()
    assert waits == [] and store.reads_attempted == 1


def run_retry(errors, waits):
    pending = list(errors)

    def operation():
        if pending:
            raise pending.pop(0)
        return 'done'
    return sheets._retry(operation, waits.append, lambda: 0)


def test_a_429_without_retry_after_waits_twenty_then_forty_seconds_then_succeeds():
    waits = []
    assert run_retry([transient(), transient()], waits) == 'done'
    assert waits == [20, 40]


def test_a_429_with_a_longer_retry_after_obeys_it_and_over_budget_still_stops():
    waits = []
    assert run_retry([transient(retry_after=30)], waits) == 'done' and waits == [30]
    with pytest.raises(ValueError, match='sheet_retry_delay_exceeds_budget'):
        run_retry([transient(retry_after=61)], [])


def test_other_transient_errors_keep_the_short_backoff():
    waits = []
    assert run_retry([transient('sheet_http_503'), transient('sheet_http_503')], waits) == 'done'
    assert waits == [1, 2]


def test_a_third_429_is_raised_not_swallowed():
    with pytest.raises(SheetIOError, match='sheet_http_429'):
        run_retry([transient(), transient(), transient()], [])
