"""Is a blank cell blank because the source has nothing, or because our system lost it?

  uv run --locked python -m scripts.field_audit                         # fill rates per source from the Jobs tab, with flags
  uv run --locked python -m scripts.field_audit --cross-check           # also ask the live boards whether they publish what a blank cell lacks
  uv run --locked python -m scripts.field_audit --rows-json saved.json  # a saved Sheets API reply instead of the live tab

Read-only: it reads the Jobs tab (and, with --cross-check, the public board APIs the probe already uses) and writes
nothing. It prints counts and fixed words only. A FLAG line means a source fills a column far less often than that
source is known to publish it, which points at our reader, not at the employer. The expected rates come from real board
data read on October 21, 2026 and are deliberately lower than what was measured.
"""

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import re

import httpx
import yaml

from jobhunter.postings import PARSERS
from scripts.source_probe import URLS

ALWAYS = ('Job ID', 'Job title', 'Company', 'Apply link', 'Brief description')
ATS = ('greenhouse', 'lever', 'ashby')
# Lowest share of rows that should carry the column, per source family (measured on real boards, then lowered).
EXPECTED = {
    'greenhouse': {'Salary': 0.35, 'Location': 0.95},
    'ashby': {'Salary': 0.45, 'Location': 0.9},
    'lever': {'Location': 0.9},
    'waas-product': {'Salary': 0.6, 'Location': 0.9}, 'waas-operations': {'Salary': 0.6, 'Location': 0.9},
    'yc-product': {'Salary': 0.6, 'Location': 0.9}, 'builtin-product': {'Salary': 0.6, 'Location': 0.9},
}
# States whose pay-transparency laws make employers publish a range; boards in these places should show pay.
PAY_TRANSPARENCY_PLACE = re.compile(r'(?:,\s*(?:CA|NY|CO|WA)\b|\b(?:California|New York|Colorado|Washington)\b|'
                                    r'\b(?:San Francisco|Los Angeles|San Diego|Seattle|Denver|New York City|NYC|Bay Area)\b)')
PAY_TRANSPARENCY_MIN = 0.5


REGISTRY = Path(__file__).resolve().parent.parent / 'sources' / 'v0_sources.yaml'
# Sources written by collectors that are not in the registry's job-board lists.
FIXED_SOURCES = frozenset({'x-twscrape', 'linkedin-login', 'linkedin-jobs', 'alirohde-rss', 'hn-who-is-hiring'})


def known_sources(registry=REGISTRY):
    """Every Source value this program can write: registry boards as kind:board, other registry ids, fixed collector ids."""
    with open(registry, encoding='utf-8') as handle:
        data = yaml.safe_load(handle)
    known = set(FIXED_SOURCES)
    for kind, boards in (data.get('boards') or {}).items():
        known.update(f'{kind}:{board["board"]}' for board in boards)
    for group in ('aggregators', 'keyed_apis', 'detail_sources', 'listing_only', 'needs_setup'):
        known.update(entry['id'] for entry in data.get(group) or [])
    return frozenset(known)


def family(source, known):
    """The source family for a Source cell, or the fixed word `unknown`: a cell value is never printed or used as a key."""
    if not isinstance(source, str) or source not in known:
        return 'unknown'
    kind = source.split(':')[0]
    return kind if kind in ATS else source


def to_records(rows):
    header = rows[0]
    return [dict(zip(header, list(row) + [''] * (len(header) - len(row)))) for row in rows[1:] if any(row)]


def audit(records, known=None):
    """({family: {'rows': n, column: filled}}, [flag text]) from Jobs rows."""
    known = known_sources() if known is None else known
    table = defaultdict(Counter)
    place_pay = defaultdict(Counter)
    for record in records:
        fam = family(record.get('Source', ''), known)
        table[fam]['rows'] += 1
        for column in ALWAYS + ('Salary', 'Location'):
            if str(record.get(column, '')).strip():
                table[fam][column] += 1
        if fam in ATS and PAY_TRANSPARENCY_PLACE.search(record.get('Location', '')):
            place_pay[fam]['rows'] += 1
            place_pay[fam]['paid'] += bool(str(record.get('Salary', '')).strip())
    flags = []
    for fam, counts in sorted(table.items()):
        total = counts['rows']
        for column in ALWAYS:
            if counts[column] < total:
                flags.append(f'flag: {fam} {column} blank in {total - counts[column]} of {total} rows (always expected)')
        for column, minimum in EXPECTED.get(fam, {}).items():
            if total >= 3 and counts[column] / total < minimum:
                flags.append(f'flag: {fam} {column} filled {counts[column]}/{total} ({counts[column] * 100 // total}%), '
                             f'expected at least {int(minimum * 100)}%')
    for fam, counts in sorted(place_pay.items()):
        if counts['rows'] >= 3 and counts['paid'] / counts['rows'] < PAY_TRANSPARENCY_MIN:
            flags.append(f'flag: {fam} Salary filled {counts["paid"]}/{counts["rows"]} for CA/NY/CO/WA places, '
                         f'where employers must publish pay (expected at least {int(PAY_TRANSPARENCY_MIN * 100)}%)')
    return table, flags


def cross_check(records, client, *, now=None, known=None):
    """Compare blank Salary cells with what the live boards publish now.

    Returns Counter: has_pay_we_left_blank (our gap), source_also_blank (nothing to read), no_longer_listed,
    board_unreadable, filled_already. The board data is parsed by the same parsers the probe uses.
    """
    known = known_sources() if known is None else known
    stamp = (now or (lambda: datetime.now(timezone.utc).isoformat(timespec='seconds')))()
    wanted = defaultdict(list)
    for record in records:
        source = record.get('Source', '')
        if source in known and family(source, known) in ATS:  # only registry boards: a cell value never builds a URL
            wanted[source].append(record)
    result = Counter()
    for source, rows in sorted(wanted.items()):
        kind, board = source.split(':', 1)
        try:
            response = client.get(URLS[kind].format(board=board), headers={'Accept': 'application/json'}, timeout=60)
            response.raise_for_status()
            postings, _, _ = PARSERS[kind](response.json(), {'board': board, 'company': board, 'tag': 'other',
                                                             'source_id': source, 'captured_at': stamp})
        except (httpx.HTTPError, ValueError, TypeError, KeyError, AttributeError):
            result['board_unreadable'] += len(rows)
            continue
        live = {posting.job_id: posting.salary for posting in postings}
        for record in rows:
            if str(record.get('Salary', '')).strip():
                result['filled_already'] += 1
            elif record['Job ID'] not in live:
                result['no_longer_listed'] += 1
            elif live[record['Job ID']]:
                result['has_pay_we_left_blank'] += 1
            else:
                result['source_also_blank'] += 1
    return result


def report(table, flags, crossed=None):
    lines = [f'{"source":28s} rows  salary  location']
    for fam, counts in sorted(table.items(), key=lambda item: -item[1]['rows']):
        lines.append(f'{fam:28s} {counts["rows"]:4d}  {counts["Salary"]:6d}  {counts["Location"]:8d}')
    lines += flags or ['no flags']
    if crossed is not None:
        lines.append('cross_check: ' + ' '.join(f'{name}={crossed[name]}' for name in
                                                ('has_pay_we_left_blank', 'source_also_blank', 'no_longer_listed',
                                                 'board_unreadable', 'filled_already')))
    lines.append(f'field_audit_flags={len(flags)}')
    return '\n'.join(lines)


def main(argv=None, *, store=None, client=None) -> int:
    parser = argparse.ArgumentParser(description='Blank-cell audit of the Jobs tab; read-only.')
    parser.add_argument('--rows-json', help='A saved Sheets API reply ({"values": [...]}) instead of the live Jobs tab')
    parser.add_argument('--cross-check', action='store_true', help='Ask the live public boards what they publish')
    args = parser.parse_args(argv)
    try:
        if args.rows_json:
            with open(args.rows_json, encoding='utf-8') as handle:
                rows = json.load(handle)['values']
        else:
            from jobhunter.google_auth import open_workbook
            from jobhunter.sheet_io import GspreadStore
            rows = (GspreadStore(open_workbook()) if store is None else store).read('Jobs')
        records = to_records(rows)
        table, flags = audit(records)
        crossed = None
        if args.cross_check:
            with (client or httpx.Client(follow_redirects=True)) as http:
                crossed = cross_check(records, http)
        print(report(table, flags, crossed))
        return 0
    except Exception as exc:  # noqa: BLE001 - say a fixed word, never a cell value
        print(f'field_audit_failed: {type(exc).__name__}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
