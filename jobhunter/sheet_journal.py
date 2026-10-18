"""Bounded non-secret pending writes in the workbook, never a second database."""

from datetime import datetime
import hashlib
import json
import re

from jobhunter.sheet_io import SheetIOError
from jobhunter.sheet_records import CellWrite, plan_table, table_index

STATE_HEADERS = ('Key', 'Value')
MAX_BYTES = 1024 * 1024
CHUNK_SIZE = 40000
PREFIX = 'm0/run/'
QUARANTINE = 'm0/quarantined/'


def _stamp(value):
    if not isinstance(value, str) or len(value) > 100:
        raise ValueError('invalid_journal_timestamp')
    try:
        if datetime.fromisoformat(value).utcoffset() is None:
            raise ValueError
    except ValueError:
        raise ValueError('invalid_journal_timestamp') from None


def _json(value):
    try:
        return json.loads(value)
    except (ValueError, TypeError, RecursionError):
        raise ValueError('invalid_pending_journal') from None


class SheetJournal:
    def __init__(self, store):
        self.store = store

    def _entries(self):
        rows = self.store.read('_State')
        headers, identities = table_index(rows, STATE_HEADERS, 'Key')
        entries = {}
        for key, (_, values) in identities.items():
            value = values[headers['Value']] if headers['Value'] < len(values) else ''
            if key.startswith(PREFIX) and (not isinstance(value, str) or len(value) > CHUNK_SIZE):
                raise ValueError('invalid_pending_journal')
            entries[key] = value
        return rows, entries

    def _manifest(self, value):
        data = _json(value)
        if (not isinstance(data, dict) or set(data) != {'state', 'sha256', 'chunks', 'started', 'finished'}
                or data['state'] not in {'pending', 'done'}
                or not isinstance(data['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', data['sha256'])
                or type(data['chunks']) is not int or not 1 <= data['chunks'] <= 27):
            raise ValueError('invalid_pending_journal')
        _stamp(data['started'])
        if data['state'] == 'done':
            _stamp(data['finished'])
        elif data['finished'] != '':
            raise ValueError('invalid_pending_journal')
        return data

    def _payload(self, identity, manifest, entries):
        try:
            raw = ''.join(entries[f'{PREFIX}{identity}/chunk/{i}'] for i in range(manifest['chunks']))
            encoded = raw.encode('ascii')
        except (KeyError, UnicodeError):
            raise ValueError('invalid_pending_journal') from None
        if len(encoded) > MAX_BYTES or hashlib.sha256(encoded).hexdigest() != manifest['sha256']:
            raise ValueError('invalid_pending_journal')
        payload = _json(raw)
        if not isinstance(payload, dict):
            raise ValueError('invalid_pending_journal')
        return payload

    def _save(self, records):
        rows, _ = self._entries()
        # One atomic values batch commits every chunk and manifest together.
        self.store.write('_State', plan_table(rows, records, STATE_HEADERS, 'Key'))
        _, actual = self._entries()
        if any(actual.get(record['Key']) != record['Value'] for record in records):
            raise ValueError('journal_write_unconfirmed')

    def prepare(self, identity, payload, started):
        if not isinstance(identity, str) or not re.fullmatch('[A-Za-z0-9_-]{1,80}', identity):
            raise ValueError('invalid_run_id')
        _stamp(started)
        try:
            raw = json.dumps(payload, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(',', ':'))
        except (ValueError, TypeError, RecursionError):
            raise ValueError('invalid_journal_payload') from None
        if not isinstance(payload, dict) or len(raw) > MAX_BYTES:
            raise ValueError('journal_payload_too_large')
        digest = hashlib.sha256(raw.encode('ascii')).hexdigest()
        _, entries = self._entries()
        if any(key.startswith(f'{QUARANTINE}{identity}/') for key in entries):
            raise ValueError('run_id_quarantined')
        manifest_key = f'{PREFIX}{identity}/manifest'
        if manifest_key in entries:
            manifest = self._manifest(entries[manifest_key])
            if manifest['sha256'] != digest:
                raise ValueError('run_id_payload_conflict')
            if manifest['state'] == 'pending':
                self._payload(identity, manifest, entries)
            return manifest
        chunks = [raw[i:i + CHUNK_SIZE] for i in range(0, len(raw), CHUNK_SIZE)]
        manifest = {'state': 'pending', 'sha256': digest, 'chunks': len(chunks),
                    'started': started, 'finished': ''}
        records = [{'Key': f'{PREFIX}{identity}/chunk/{i}', 'Value': value} for i, value in enumerate(chunks)]
        records.append({'Key': manifest_key, 'Value': json.dumps(manifest, sort_keys=True)})
        self._save(records)
        return manifest

    def pending(self):
        _, entries = self._entries()
        output = []
        for key, value in entries.items():
            if key.startswith(PREFIX) and key.endswith('/manifest'):
                identity = key[len(PREFIX):-len('/manifest')]
                if not re.fullmatch('[A-Za-z0-9_-]{1,80}', identity):
                    raise ValueError('invalid_pending_journal')
                manifest = self._manifest(value)
                if manifest['state'] == 'pending':
                    output.append((identity, self._payload(identity, manifest, entries), manifest))
        return output

    def finish(self, identity, finished):
        _stamp(finished)
        _, entries = self._entries()
        key = f'{PREFIX}{identity}/manifest'
        if key not in entries:
            raise ValueError('missing_pending_journal')
        manifest = self._manifest(entries[key])
        if manifest['state'] == 'done':
            return
        manifest |= {'state': 'done', 'finished': finished}
        records = [{'Key': f'{PREFIX}{identity}/chunk/{i}', 'Value': ''} for i in range(manifest['chunks'])]
        records.append({'Key': key, 'Value': json.dumps(manifest, sort_keys=True)})
        self._save(records)

    def quarantine(self, identity):
        """Manual operator action: move a run's cells out of recovery, never delete them.

        Works even when the manifest or chunks are unreadable, because it only
        renames the Key cells; Values are untouched and stay available for audit.
        """
        if not isinstance(identity, str) or not re.fullmatch('[A-Za-z0-9_-]{1,80}', identity):
            raise ValueError('invalid_run_id')
        try:
            rows = self.store.read('_State')
        except (KeyError, SheetIOError) as exc:
            # A missing tab means no journal; transient or unknown failures stay failures.
            if isinstance(exc, SheetIOError) and not exc.rejected:
                raise
            raise ValueError('missing_pending_journal') from None
        headers, identities = table_index(rows, STATE_HEADERS, 'Key')
        old = f'{PREFIX}{identity}/'
        moved = [(key, number) for key, (number, _) in identities.items() if key.startswith(old)]
        if not moved:
            raise ValueError('missing_pending_journal')
        if len(moved) > 28:  # 27 chunks plus the manifest, the most a valid run can have
            raise ValueError('invalid_pending_journal')
        manifest = identities.get(f'{old}manifest')
        if manifest is not None:
            try:
                value = manifest[1][headers['Value']]
                if _json(value).get('state') == 'done':
                    raise ValueError('run_not_pending')
            except (IndexError, AttributeError, ValueError) as exc:
                if str(exc) == 'run_not_pending':
                    raise
                # Unreadable manifest is exactly what quarantine is for.
        if any(key.startswith(f'{QUARANTINE}{identity}/') for key in identities):
            raise ValueError('run_id_quarantined')
        self.store.write('_State', [CellWrite(number, headers['Key'] + 1,
                                              [[f'{QUARANTINE}{identity}/{key[len(old):]}']])
                                    for key, number in moved])
        _, actual = self._entries()
        if any(key in actual for key, _ in moved):
            raise ValueError('journal_write_unconfirmed')
        return len(moved)
