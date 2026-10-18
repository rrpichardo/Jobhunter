"""Conservative structural lock for compliant writers of one workbook.

No lease expiry or lock stealing. Manual recovery requires stopping every previous
writer; a hidden Sheet cannot protect against editors deleting or changing it.
"""

class SheetLock:
    def __init__(self, store, owner, started):
        self.store, self.owner, self.started = store, owner, started
        self.attempted = self.held = False

    def acquire(self):
        if self.attempted:
            raise ValueError('lock_acquisition_already_attempted')
        self.attempted = True
        try:
            self.store.create_lock(self.owner, self.started)
        except Exception:
            # Even an apparently rejected request may have reached the server.
            # Ownership is the only acceptable confirmation; never retry create.
            pass
        try:
            owner = self.store.lock_owner()
        except Exception:
            raise ValueError('lock_acquisition_unconfirmed') from None
        if owner != self.owner:
            raise ValueError('writer_locked' if owner is not None else 'lock_acquisition_unconfirmed')
        self.held = True
        if hasattr(self.store, 'activate_owner'):
            self.store.activate_owner(self.owner)

    def release(self):
        if not self.held:
            return
        self.held = False
        if hasattr(self.store, 'deactivate_owner'):
            self.store.deactivate_owner(self.owner)
        try:
            owner = self.store.lock_owner()
        except Exception:
            raise ValueError('lock_release_unconfirmed') from None
        if owner != self.owner:
            raise ValueError('lock_ownership_lost')
        try:
            self.store.drop_lock()
        except Exception:
            # No repeated delete: a delayed response may mean a later owner
            # already acquired the same sheet ID. Reading never deletes it.
            try:
                if self.store.lock_owner() != self.owner:
                    return
            except Exception:
                pass
            raise ValueError('lock_release_unconfirmed') from None
