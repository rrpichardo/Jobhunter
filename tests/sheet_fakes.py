from copy import deepcopy


class MemoryStore:
    def __init__(self):
        self.tables, self.owner, self.writes = {}, None, []
        self.after_write = None
        self.reads = []
    def refresh(self): pass
    def ensure_tab(self, title, headers, **kwargs):
        self.tables.setdefault(title, [list(headers)])
    def read(self, title):
        self.reads.append(title)
        return deepcopy(self.tables[title])
    def write(self, title, writes):
        self.writes.append((title, deepcopy(writes)))
        rows = self.tables[title]
        for write in writes:
            for offset, values in enumerate(write.values):
                row = write.row + offset - 1
                while len(rows) <= row: rows.append([])
                while len(rows[row]) < write.column - 1 + len(values): rows[row].append('')
                rows[row][write.column - 1:write.column - 1 + len(values)] = values
        if self.after_write: self.after_write(title)
    def create_lock(self, owner, started):
        if self.owner is not None: raise ValueError('writer_locked')
        self.owner = owner
    def lock_owner(self): return self.owner
    def drop_lock(self): self.owner = None
