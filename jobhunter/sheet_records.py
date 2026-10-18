"""Deterministic Sheet plans; no network calls or AI-selected cell updates."""

from dataclasses import dataclass
from datetime import date
import re

from jobhunter.job_identity import canonical_key
from jobhunter.records import https_url

JOB_HEADERS = ('Job ID', 'Date found', 'Job title', 'Company', 'Salary', 'Location',
               'Brief description', 'Apply link', 'Source', 'Rank (prelim)', 'Fit',
               'Next step', 'Status', 'Notes', 'My rating', 'More details')
USER_COLUMNS = frozenset({'Status', 'Notes', 'My rating'})


@dataclass(frozen=True)
class CellWrite:
    row: int
    column: int
    values: list[list]


def normalize_jobs(records):
    if not isinstance(records, list) or len(records) > 150:
        raise ValueError('invalid_job_batch')
    unique = {}
    for record in records:
        if not isinstance(record, dict) or set(record) != set(JOB_HEADERS):
            raise ValueError('invalid_job_fields')
        record = record.copy()
        for header, value in record.items():
            if header == 'Rank (prelim)':
                if type(value) is not int or value not in {1, 2, 3}:
                    raise ValueError('invalid_preliminary_rank')
            elif not isinstance(value, str) or len(value) > 40000:
                raise ValueError('invalid_job_value')
            else:
                if re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', value):
                    raise ValueError('invalid_job_value')
                try:
                    value.encode('utf-8')
                except UnicodeError:
                    raise ValueError('invalid_job_value') from None
                record[header] = value.replace('\r\n', '\n').replace('\r', '\n')
        identity = record['Job ID']
        if not identity.strip() or len(identity) > 512 or any(c.isspace() for c in identity):
            raise ValueError('invalid_job_id')
        unique[identity] = record | {'Status': 'New', 'Notes': '', 'My rating': ''}
    return list(unique.values())


def table_index(rows, required_headers, key):
    if not rows or not isinstance(rows[0], list):
        raise ValueError('missing_headers')
    headers = rows[0]
    if (any(not isinstance(h, str) or not h.strip() or h != h.strip() for h in headers)
            or len(set(headers)) != len(headers) or not set(required_headers) <= set(headers)):
        raise ValueError('ambiguous_headers')
    mapping, identities = {h: i for i, h in enumerate(headers)}, {}
    for number, values in enumerate(rows[1:], 2):
        if not isinstance(values, list) or len(values) > len(headers):
            raise ValueError('invalid_existing_row')
        if not any(v not in ('', None) for v in values):
            continue
        identity = values[mapping[key]] if mapping[key] < len(values) else ''
        if not isinstance(identity, str) or not identity.strip() or identity != identity.strip():
            raise ValueError('unkeyed_existing_row')
        if identity in identities:
            raise ValueError('duplicate_existing_id')
        identities[identity] = (number, values)
    return mapping, identities


def plan_table(rows, records, headers, key, *, preserved=frozenset()):
    mapping, existing = table_index(rows, headers, key)
    writes, next_row = [], len(rows) + 1
    for record in records:
        identity = record[key]
        if identity in existing:
            number, old = existing[identity]
            for header in headers:
                if header in preserved or header == key:
                    continue
                column = mapping[header]
                previous = old[column] if column < len(old) and old[column] is not None else ''
                if previous != record[header]:
                    writes.append(CellWrite(number, column + 1, [[record[header]]]))
        else:
            values = [''] * len(mapping)
            for header in headers:
                values[mapping[header]] = record[header]
            writes.append(CellWrite(next_row, 1, [values]))
            next_row += 1
    return writes


def _discovery_details(record, previous):
    """Retain first-seen dates for reconciled sources without growing on each replay."""
    history = {}
    for item in (previous, record):
        if item is None:
            continue
        for line in str(item.get('More details', '')).splitlines():
            match = re.fullmatch(r'First seen by ([A-Za-z][A-Za-z0-9_.:-]{0,159}): (\d{4}-\d{2}-\d{2})', line)
            if match:
                source, stamp = match.groups()
                try:
                    date.fromisoformat(stamp)
                except ValueError:
                    continue
                history[source] = min(history.get(source, stamp), stamp)
    if not history and (previous is None or previous['Source'] == record['Source']):
        return record['More details']
    for item in (previous, record):
        if item is None or item['Source'] in history:
            continue
        stamp = item['Date found']
        try:
            date.fromisoformat(stamp)
        except (TypeError, ValueError):
            continue
        history[item['Source']] = stamp
    lines = [line for line in record['More details'].splitlines() if not line.startswith('First seen by ')]
    return '\n'.join([*lines, *(f'First seen by {source}: {stamp}' for source, stamp in sorted(history.items()))])


def reconcile_jobs(rows, records):
    mapping, identities = table_index(rows, JOB_HEADERS, 'Job ID')
    known = {identity: {h: values[mapping[h]] if mapping[h] < len(values) else '' for h in JOB_HEADERS}
             for identity, (_, values) in identities.items()}
    by_link = {}
    for identity, old in known.items():
        if https_url(old['Apply link']):
            by_link.setdefault(canonical_key(old['Apply link']), set()).add(identity)
    planned = {}
    for record in normalize_jobs(records):
        identity = record['Job ID']
        key = canonical_key(record['Apply link']) if https_url(record['Apply link']) else None
        if identity not in known and identity not in planned and key is not None:
            matches = [candidate for candidate in by_link.get(key, ())
                       if (planned.get(candidate) or known[candidate])['Source'] != record['Source']]
            if len(matches) > 1:
                # Never choose between rows whose user-owned cells may disagree.
                raise ValueError('ambiguous_existing_job_identity')
            if matches:
                identity = matches[0]
        previous = planned.get(identity) or known.get(identity)
        record = record | {'Job ID': identity, 'More details': _discovery_details(record, previous),
                           'Source': previous['Source'] if previous else record['Source']}
        planned[identity] = record
        if key is not None:
            by_link.setdefault(key, set()).add(identity)
    return normalize_jobs(list(planned.values()))


def plan_jobs(rows, records):
    return plan_table(rows, reconcile_jobs(rows, records), JOB_HEADERS, 'Job ID',
                      preserved=USER_COLUMNS | {'Date found'})
