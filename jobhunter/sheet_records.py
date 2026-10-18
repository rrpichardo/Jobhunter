"""Deterministic Sheet plans; no network calls or AI-selected cell updates."""

from dataclasses import dataclass
import re

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


def plan_jobs(rows, records):
    return plan_table(rows, normalize_jobs(records), JOB_HEADERS, 'Job ID',
                      preserved=USER_COLUMNS | {'Date found'})
