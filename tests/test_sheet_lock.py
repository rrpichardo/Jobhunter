import pytest


class LockStore:
    owner = None
    deletes = 0
    ambiguous_create = False
    ambiguous_delete = False
    def create_lock(self, owner, started):
        if self.owner is not None: raise RuntimeError('collision')
        self.owner = owner
        if self.ambiguous_create: raise TimeoutError()
    def lock_owner(self): return self.owner
    def drop_lock(self):
        self.deletes += 1
        self.owner = None
        if self.ambiguous_delete: raise TimeoutError()


def test_overlap_blocks_second_writer_without_deleting_first_lock():
    from jobhunter.sheet_lock import SheetLock
    store = LockStore()
    first = SheetLock(store, 'a', '2026-10-17T00:00:00Z')
    first.acquire()
    with pytest.raises(ValueError, match='writer_locked'):
        SheetLock(store, 'b', '2026-10-17T00:00:01Z').acquire()
    assert store.owner == 'a' and store.deletes == 0
    first.release()
    assert store.owner is None


def test_ambiguous_acquire_requires_matching_owner_and_does_not_retry_create():
    from jobhunter.sheet_lock import SheetLock
    store = LockStore()
    store.ambiguous_create = True
    lock = SheetLock(store, 'a', '2026-10-17T00:00:00Z')
    lock.acquire()
    assert store.owner == 'a'
    store.owner = 'another-owner'
    with pytest.raises(ValueError, match='lock_ownership_lost'): lock.release()
    assert store.deletes == 0


def test_ambiguous_delete_is_never_repeated_even_if_another_owner_appears():
    from jobhunter.sheet_lock import SheetLock
    store = LockStore()
    lock = SheetLock(store, 'a', '2026-10-17T00:00:00Z')
    lock.acquire()
    store.ambiguous_delete = True
    def failed_delete():
        store.deletes += 1
        store.owner = 'new-owner'
        raise TimeoutError()
    store.drop_lock = failed_delete
    lock.release()
    lock.release()
    assert store.deletes == 1 and store.owner == 'new-owner'
