"""Deterministic Sheet plans; no network calls or AI-selected cell updates."""

from dataclasses import dataclass
from datetime import date, datetime, timezone
import re

from jobhunter.job_identity import canonical_key, verified_requisition
from jobhunter.records import https_url

JOB_HEADERS = ('Job ID', 'Date found', 'Job title', 'Company', 'Salary', 'Location',
               'Brief description', 'Apply link', 'Source', 'Rank (prelim)', 'Fit',
               'Next step', 'Status', 'Notes', 'My rating', 'More details')
USER_COLUMNS = frozenset({'Status', 'Notes', 'My rating'})
# Size of ONE recoverable writer batch (its journal entry must fit in _State). A run with more jobs is split into
# several batches by scripts.sheets_sync; this is a batch size, not a limit on how many jobs a run may deliver.
JOB_BATCH_SIZE = 150


@dataclass(frozen=True)
class CellWrite:
    row: int
    column: int
    values: list[list]


def normalize_jobs(records):
    if not isinstance(records, list) or len(records) > JOB_BATCH_SIZE:
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
    """Union discovery attribution and earliest observed times, including legacy dates."""
    history, also, fallback = {}, set(), []

    def remember(source, stamp):
        try:
            parsed = datetime.fromisoformat(stamp)
            if parsed.tzinfo is None:
                if len(stamp) != 10:
                    return False  # a timestamp without its timezone is ambiguous
                date.fromisoformat(stamp)
                parsed = parsed.replace(tzinfo=timezone.utc)  # order a legacy date, retain its date-only text
            key = parsed.astimezone(timezone.utc)
        except (TypeError, ValueError, OverflowError):
            return False
        if source not in history or key < history[source][0]:
            history[source] = (key, stamp)
        return True

    for item in (previous, record):
        if item is None:
            continue
        own_seen = False
        for line in item['More details'].splitlines():
            if line.startswith('Also listed by: '):
                also.update(source.strip() for source in line.removeprefix('Also listed by: ').split(',')
                            if re.fullmatch(r'[A-Za-z][A-Za-z0-9_.:-]{0,159}', source.strip()))
            match = re.fullmatch(r'First seen by ([A-Za-z][A-Za-z0-9_.:-]{0,159}): (.+)', line)
            if match and remember(*match.groups()) and match[1] == item['Source']:
                own_seen = True
        if not own_seen:
            fallback.append((item['Source'], item['Date found']))
    if history or (previous is not None and previous['Source'] != record['Source']):
        # Old rows may have only Date found; never invent a precise time for them.
        for source, stamp in fallback:
            remember(source, stamp)
    lines = [line for line in record['More details'].splitlines()
             if not line.startswith(('First seen by ', 'Also listed by: '))]
    if also:
        lines.append('Also listed by: ' + ', '.join(sorted(also)))
    lines.extend(f'First seen by {source}: {stamp}' for source, (_, stamp) in sorted(history.items()))
    return '\n'.join(lines)


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
            matches = sorted(candidate for candidate in by_link.get(key, ())
                             if (planned.get(candidate) or known[candidate])['Source'] != record['Source'])
            if len(matches) > 1 and verified_requisition(key):
                # Never choose between rows whose user-owned cells may disagree.
                # A shared generic/custom URL does not verify which requisition
                # from another source an existing row represents.
                raise ValueError('ambiguous_existing_job_identity')
            if matches and not verified_requisition(key):
                record = record | {'More details': record['More details'] +
                    f'\nPossible duplicate of {matches[0]} (shared application link; requisition identity unverified; needs review)'}
            elif matches:
                identity = matches[0]
            elif by_link.get(key):
                candidate = sorted(by_link[key])[0]
                record = record | {'More details': record['More details'] +
                    f'\nPossible duplicate of {candidate} (same source, shared link, different requisition; needs review)'}
        previous = planned.get(identity) or known.get(identity)
        if previous:
            details = record['More details'].splitlines()
            details.extend(line for line in previous['More details'].splitlines()
                           if line.startswith('Possible duplicate of ') and 'needs review' in line
                           and line not in details)
            record = record | {'More details': '\n'.join(details)}
        record = record | {'Job ID': identity, 'More details': _discovery_details(record, previous),
                           'Source': previous['Source'] if previous else record['Source']}
        planned[identity] = record
        if key is not None:
            by_link.setdefault(key, set()).add(identity)
    return normalize_jobs(list(planned.values()))


def plan_jobs(rows, records):
    return plan_table(rows, reconcile_jobs(rows, records), JOB_HEADERS, 'Job ID',
                      preserved=USER_COLUMNS | {'Date found'})
