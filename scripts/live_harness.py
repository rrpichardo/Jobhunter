"""Paced live test harness for the M0 Sheet writer, run only in JobHunterEnv.

Every scenario uses a fresh hidden `_M0Test_<random>` namespace, so the real
Jobs, Sources, Run Log and _State tabs are never read or written. Only the shared
global lock tab is touched. The harness makes no source or social fetches and never
removes a lock: a scenario that leaves the lock in place stops the run and waits
for an operator decision. Fixture tabs are kept, since cleanup is not proven safe.
"""

import argparse
from dataclasses import dataclass, field
import json
import re
import secrets
import subprocess
import sys
import tempfile
import time

from requests.exceptions import Timeout

from jobhunter.google_auth import open_workbook
from jobhunter.sheet_io import LOCK_ID, LOCK_TITLE, GspreadStore
from jobhunter.sheet_records import JOB_HEADERS
from jobhunter.sheets import RUN_HEADERS, sync_jobs

SOURCE_ID = 'harness:fixture'
EXIT_LOCK_RETAINED = 3


class InjectedInterrupt(KeyboardInterrupt):
    """Stands in for Ctrl-C or a killed process at an exact request boundary."""


@dataclass
class Fault:
    """One-shot misbehaviour on the first matching request."""
    mode: str  # timeout_after, timeout_before, interrupt_after, interrupt_before, hold
    tab: str
    kind: str = 'values'  # 'values' for cell writes, 'structural' for addSheet
    hold: float = 0
    fired: bool = False


def _titles(ranges):
    return {m.group(1) for m in (re.match(r"'([^']+)'", r) for r in ranges) if m}


class GuardedWorkbook:
    """Wraps a gspread Spreadsheet: pacing, namespace guard, call log and faults."""

    def __init__(self, inner, namespace, *, interval=1.5, sleep=time.sleep, clock=time.monotonic):
        self.inner, self.namespace = inner, namespace
        self.interval, self._sleep, self._clock, self._last = interval, sleep, clock, None
        self.ids = {LOCK_ID}
        self.fault = None
        self.violations, self.mutations, self.calls = [], [], 0

    def _pace(self):
        if self._last is not None:
            wait = self.interval - (self._clock() - self._last)
            if wait > 0:
                self._sleep(wait)
        self._last = self._clock()
        self.calls += 1

    def _allowed(self, title):
        return title == LOCK_TITLE or title.startswith(self.namespace + '_')

    def _reject(self, reason):
        self.violations.append(reason)
        raise AssertionError('harness_guard_' + reason)

    def fetch_sheet_metadata(self):
        self._pace()
        data = self.inner.fetch_sheet_metadata()
        for sheet in data['sheets']:
            if self._allowed(sheet['properties']['title']):
                self.ids.add(sheet['properties']['sheetId'])
        return data

    def values_get(self, name, params=None):
        self._pace()
        if not _titles([name]) or not all(map(self._allowed, _titles([name]))):
            self._reject('read_outside_namespace')
        return self.inner.values_get(name, params=params)

    def _faulty(self, kind, tabs):
        fault = self.fault
        return (fault is not None and not fault.fired and fault.kind == kind
                and f'{self.namespace}_{fault.tab}' in tabs)

    def _run(self, call, body, kind, tabs):
        fault = self.fault
        if not self._faulty(kind, tabs):
            return call(body)
        fault.fired = True
        if fault.mode == 'hold':
            self._sleep(fault.hold)
            return call(body)
        if fault.mode == 'timeout_before':
            raise Timeout('injected')
        if fault.mode == 'interrupt_before':
            raise InjectedInterrupt()
        result = call(body)  # the request really reached Google and was applied
        raise Timeout('injected') if fault.mode == 'timeout_after' else InjectedInterrupt()

    def batch_update(self, body):
        self._pace()
        titles = set()
        for request in body['requests']:
            if 'addSheet' in request:
                title = request['addSheet']['properties']['title']
                titles.add(title)
                if not self._allowed(title):
                    self._reject('structure_outside_namespace')
            else:
                args = next(iter(request.values()))
                sheet_id = args.get('sheetId') or args.get('start', {}).get('sheetId')
                if sheet_id not in self.ids:
                    self._reject('structure_outside_namespace')
        titles -= {LOCK_TITLE}
        self.mutations.append(('structural', sorted(titles)))
        return self._run(self.inner.batch_update, body, 'structural', titles)

    def values_batch_update(self, body, *, as_user=False):
        self._pace()
        ranges = [item['range'] for item in body['data']]
        titles = _titles(ranges)
        if len(titles) < 1 or not all(map(self._allowed, titles)):
            self._reject('write_outside_namespace')
        tabs = titles - {LOCK_TITLE}
        if not as_user:
            self.mutations.append(('values', sorted(tabs)))
        call = self.inner.values_batch_update
        # Faults target real data writes, never the header row written at tab creation.
        data_tabs = tabs if any(not r.endswith('!A1') for r in ranges if LOCK_TITLE not in r) else set()
        return call(body) if as_user else self._run(call, body, 'values', data_tabs)

    def data_mutations(self):
        """Requests that changed fixture tabs; lock create/release is not counted."""
        return sum(1 for _, tabs in self.mutations if tabs)

    def jobs_writes(self):
        return sum(1 for kind, tabs in self.mutations if kind == 'values' and f'{self.namespace}_Jobs' in tabs)


@dataclass
class Context:
    namespace: str
    wb: GuardedWorkbook
    checks: list = field(default_factory=list)

    def check(self, name, ok, detail=''):
        self.checks.append((name, bool(ok), detail))
        print(f"{'PASS' if ok else 'FAIL'} {name}" + (f': {detail}' if detail else ''), flush=True)

    def store(self):
        return GspreadStore(self.wb, namespace=self.namespace)

    def table(self, title):
        rows = self.wb.values_get(f"'{self.namespace}_{title}'",
                                  params={'valueRenderOption': 'UNFORMATTED_VALUE'}).get('values', [])
        if not rows:
            return []
        return [dict(zip(rows[0], row + [''] * (len(rows[0]) - len(row)))) for row in rows[1:]]

    def user_edit(self, row, header, value):
        """A person editing a Jobs cell by hand; goes straight to the sheet, no lock."""
        column = JOB_HEADERS.index(header) + 1
        a1 = f'{chr(64 + column)}{row}'
        self.wb.values_batch_update({'valueInputOption': 'RAW', 'data': [
            {'range': f"'{self.namespace}_Jobs'!{a1}", 'values': [[value]]}]}, as_user=True)

    def lock_owner(self):
        return self.store().lock_owner()


FIXTURE_TIME = '2026-10-17T00:00:00+00:00'  # fixed, so repeating a run ID repeats identical input


def fixture_job(namespace, number, **changes):
    suffix = namespace.rsplit('_', 1)[1]
    row = {header: f'{header} {number}' for header in JOB_HEADERS}
    row |= {'Job ID': f'{SOURCE_ID}:{suffix}:{number:03d}', 'Date found': '2026-10-17',
            'Source': SOURCE_ID, 'Rank (prelim)': 1 + number % 3, 'Status': 'New',
            'Notes': '', 'My rating': '', 'Apply link': f'https://example.invalid/{suffix}/{number}'}
    return row | changes


def source_records(count):
    return [{'source_id': SOURCE_ID, 'status': 'OK', 'captured_at': FIXTURE_TIME, 'jobs_fetched': count,
             'valid_jobs': count, 'rejected_items': 0, 'pm_candidates': count, 'selected_for_m0': count,
             'attempts': 1, 'http_status': 200, 'coverage': 'complete-response', 'error': ''}]


def safe_code(exc):
    text = str(exc)
    return text if re.fullmatch('[a-z0-9_]{3,80}', text) else f'unexpected:{type(exc).__name__}'


def run_sync(ctx, jobs, run_id, *, chunk_size=100):
    """Returns (result, error_code); an injected interrupt is reported, not raised."""
    try:
        return sync_jobs(ctx.store(), jobs, source_records(len(jobs)), run_id=run_id,
                         chunk_size=chunk_size), None
    except InjectedInterrupt:
        return None, 'injected_interrupt'
    except Exception as exc:
        return None, safe_code(exc)


def no_duplicates(ctx, expected):
    ids = [row['Job ID'] for row in ctx.table('Jobs')]
    ctx.check('jobs_match_expected_ids_without_duplicates', sorted(ids) == sorted(expected),
              f'rows={len(ids)} unique={len(set(ids))} expected={len(expected)}')


def finish(ctx):
    ctx.check('no_writes_outside_namespace', not ctx.wb.violations, ','.join(ctx.wb.violations))
    ctx.check('lock_released', ctx.lock_owner() is None)


def scenario_chunks(ctx):
    jobs = [fixture_job(ctx.namespace, n) for n in range(1, 41)]
    result, error = run_sync(ctx, jobs, 'chunks1', chunk_size=5)
    ctx.check('sync_ok', error is None, error or '')
    ctx.check('several_job_write_requests', ctx.wb.jobs_writes() >= 8, f'requests={ctx.wb.jobs_writes()}')
    no_duplicates(ctx, [j['Job ID'] for j in jobs])
    runs = ctx.table('Run Log')
    ctx.check('run_log_complete', [r['Status'] for r in runs] == ['complete'], str([r['Status'] for r in runs]))
    finish(ctx)


def scenario_repeat(ctx):
    jobs = [fixture_job(ctx.namespace, n) for n in range(1, 6)]
    ids = [j['Job ID'] for j in jobs]
    _, error = run_sync(ctx, jobs, 'repeat1')
    ctx.check('first_run_ok', error is None, error or '')
    before = ctx.wb.data_mutations()
    _, error = run_sync(ctx, jobs, 'repeat1')
    ctx.check('same_run_id_ok_and_writes_nothing', error is None and ctx.wb.data_mutations() == before,
              f'error={error} new_writes={ctx.wb.data_mutations() - before}')
    _, error = run_sync(ctx, jobs, 'repeat2')
    ctx.check('new_run_id_same_data_adds_no_job_rows', error is None, error or '')
    _, error = run_sync(ctx, [fixture_job(ctx.namespace, 1, **{'Job title': 'changed'})], 'repeat1')
    ctx.check('changed_data_under_old_run_id_refused', error == 'run_id_payload_conflict', str(error))
    no_duplicates(ctx, ids)
    ctx.check('two_run_log_rows', len(ctx.table('Run Log')) == 2, f'rows={len(ctx.table("Run Log"))}')
    finish(ctx)


def scenario_preserve(ctx):
    jobs = [fixture_job(ctx.namespace, n) for n in range(1, 5)]
    _, error = run_sync(ctx, jobs, 'keep1')
    ctx.check('first_run_ok', error is None, error or '')
    for header, value in [('Status', 'Applied'), ('Notes', 'my own note'), ('My rating', '5'),
                          ('Date found', '2020-01-01')]:
        ctx.user_edit(4, header, value)  # row 4 holds job 3 (row 1 is the header)
    update = [fixture_job(ctx.namespace, 1),
              fixture_job(ctx.namespace, 2, **{'Job title': 'new title', 'Brief description': '=1+1'}),
              fixture_job(ctx.namespace, 3, **{'Job title': 'renamed by feed', 'Date found': '2026-10-18'}),
              fixture_job(ctx.namespace, 4, **{'Brief description': '+cmd|calc'})]
    _, error = run_sync(ctx, update, 'keep2')
    ctx.check('second_run_ok', error is None, error or '')
    rows = {r['Job ID']: r for r in ctx.table('Jobs')}
    kept = rows[update[2]['Job ID']]
    ctx.check('user_cells_preserved',
              (kept['Status'], kept['Notes'], kept['My rating'], kept['Date found'])
              == ('Applied', 'my own note', '5', '2020-01-01'), 'status/notes/rating/date found')
    ctx.check('machine_fields_updated', kept['Job title'] == 'renamed by feed')
    ctx.check('formula_text_stored_literally',
              rows[update[1]['Job ID']]['Brief description'] == '=1+1'
              and rows[update[3]['Job ID']]['Brief description'] == '+cmd|calc')
    no_duplicates(ctx, [j['Job ID'] for j in jobs])
    finish(ctx)


def scenario_sorted(ctx):
    jobs = [fixture_job(ctx.namespace, n) for n in range(1, 6)]
    _, error = run_sync(ctx, jobs, 'sort1')
    ctx.check('first_run_ok', error is None, error or '')
    ctx.user_edit(3, 'Notes', 'follows its job')  # row 3 holds job 2
    ctx.user_edit(3, 'Status', 'Interested')
    table = ctx.wb.values_get(f"'{ctx.namespace}_Jobs'", params={'valueRenderOption': 'UNFORMATTED_VALUE'})['values']
    body, width = table[1:], len(table[0])
    flipped = [row + [''] * (width - len(row)) for row in reversed(body)]
    ctx.wb.values_batch_update({'valueInputOption': 'RAW', 'data': [
        {'range': f"'{ctx.namespace}_Jobs'!A2", 'values': flipped}]}, as_user=True)  # a user sorting the sheet
    update = [fixture_job(ctx.namespace, n, **{'Job title': f'sorted {n}'}) for n in range(1, 6)]
    _, error = run_sync(ctx, update, 'sort2')
    ctx.check('run_after_sorting_ok', error is None, error or '')
    rows = {r['Job ID']: r for r in ctx.table('Jobs')}
    ctx.check('titles_updated_by_id', all(rows[j['Job ID']]['Job title'] == j['Job title'] for j in update))
    moved = rows[update[1]['Job ID']]
    ctx.check('notes_follow_their_job', (moved['Notes'], moved['Status']) == ('follows its job', 'Interested'))
    no_duplicates(ctx, [j['Job ID'] for j in jobs])
    finish(ctx)


def _timeout_after(tab, kind):
    def scenario(ctx):
        jobs = [fixture_job(ctx.namespace, n) for n in range(1, 7)]
        ctx.wb.fault = Fault('timeout_after', tab, kind)
        _, error = run_sync(ctx, jobs, 'timeout1', chunk_size=3)
        ctx.check('fault_fired', ctx.wb.fault.fired)
        ctx.check('applied_request_confirmed_by_receipt_and_sync_ok', error is None, error or '')
        no_duplicates(ctx, [j['Job ID'] for j in jobs])
        ctx.check('run_log_complete', [r['Status'] for r in ctx.table('Run Log')] == ['complete'])
        finish(ctx)
    return scenario


def scenario_interrupt_after(ctx):
    jobs = [fixture_job(ctx.namespace, n) for n in range(1, 7)]
    ctx.wb.fault = Fault('interrupt_after', 'Jobs')
    _, error = run_sync(ctx, jobs, 'interrupt1', chunk_size=3)
    ctx.check('interrupted', error == 'injected_interrupt', str(error))
    ctx.check('lock_released_after_confirmed_write', ctx.lock_owner() is None)
    states = [r['Value'] for r in ctx.table('_State') if r['Key'].endswith('/manifest')]
    ctx.check('pending_journal_kept', len(states) == 1 and '"state": "pending"' in states[0])
    ctx.wb.fault = None
    result, error = run_sync(ctx, jobs, 'interrupt1', chunk_size=3)
    ctx.check('rerun_recovers_pending_run', error is None and result['recovered_runs'] == 1,
              error or f"recovered={result['recovered_runs']}")
    no_duplicates(ctx, [j['Job ID'] for j in jobs])
    ctx.check('run_log_complete', [r['Status'] for r in ctx.table('Run Log')] == ['complete'])
    finish(ctx)


def _lock_retaining(mode, expected):
    def scenario(ctx):
        jobs = [fixture_job(ctx.namespace, n) for n in range(1, 4)]
        ctx.wb.fault = Fault(mode, 'Jobs')
        _, error = run_sync(ctx, jobs, 'retain1')
        ctx.check('fault_fired', ctx.wb.fault.fired)
        ctx.check('outcome_reported_unknown', error == expected, str(error))
        ctx.check('lock_retained_not_released', ctx.lock_owner() is not None)
        ctx.check('no_writes_outside_namespace', not ctx.wb.violations)
        print('LOCK RETAINED on purpose. The harness never unlocks; an operator must decide.')
    scenario.leaves_lock = True
    return scenario


def scenario_overlap(ctx):
    jobs = [fixture_job(ctx.namespace, n) for n in range(1, 4)]
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as stream:
        json.dump(jobs, stream)  # sanitized fixture rows only
        path = stream.name
    command = [sys.executable, '-m', 'scripts.live_harness', '--worker', ctx.namespace,
               '--worker-input', path, '--interval', str(ctx.wb.interval)]
    procs = [subprocess.Popen(command + ['--worker-tag', tag, '--worker-hold', '15'],
                              stdout=subprocess.PIPE, text=True) for tag in ('A', 'B')]
    results = [json.loads(proc.communicate(timeout=600)[0].strip().splitlines()[-1]) for proc in procs]
    codes = sorted(str(r['error']) for r in results)
    ctx.check('exactly_one_writer_won', codes == ['None', 'writer_locked'], str(codes))
    no_duplicates(ctx, [j['Job ID'] for j in jobs])
    ctx.check('one_run_log_row', len(ctx.table('Run Log')) == 1)
    finish(ctx)


SCENARIOS = {
    'chunks': scenario_chunks, 'repeat': scenario_repeat, 'preserve': scenario_preserve,
    'sorted': scenario_sorted,
    'timeout_after_apply': _timeout_after('Jobs', 'values'),
    'timeout_after_apply_structural': _timeout_after('Jobs', 'structural'),
    'interrupt_after_apply': scenario_interrupt_after, 'overlap': scenario_overlap,
    'timeout_before_apply': _lock_retaining('timeout_before', 'sheet_mutation_unconfirmed'),
    'interrupt_before_apply': _lock_retaining('interrupt_before', 'injected_interrupt'),
}
DEFAULT_SUITE = [name for name, fn in SCENARIOS.items() if not getattr(fn, 'leaves_lock', False)]


def fresh_namespace(workbook):
    titles = {sheet['properties']['title'] for sheet in workbook.fetch_sheet_metadata()['sheets']}
    namespace = '_M0Test_' + secrets.token_hex(6)
    if any(title.startswith(namespace) for title in titles):
        raise ValueError('test_namespace_exists')
    return namespace


def run_worker(args, workbook):
    wb = GuardedWorkbook(workbook, args.worker, interval=args.interval)
    wb.fault = Fault('hold', 'Jobs', hold=args.worker_hold)
    ctx = Context(args.worker, wb)
    jobs = json.load(open(args.worker_input))
    _, error = run_sync(ctx, jobs, 'overlap1')
    print(json.dumps({'tag': args.worker_tag, 'error': error}))
    return 0


def main(argv=None, *, workbook=None, sleep=time.sleep):
    parser = argparse.ArgumentParser(description='Live Sheet writer harness; hidden test namespaces only.')
    parser.add_argument('--scenario', action='append', choices=sorted(SCENARIOS))
    parser.add_argument('--interval', type=float, default=1.5, help='minimum seconds between Sheets calls')
    parser.add_argument('--worker'), parser.add_argument('--worker-input')
    parser.add_argument('--worker-tag', default='?'), parser.add_argument('--worker-hold', type=float, default=0)
    args = parser.parse_args(argv)
    try:
        workbook = open_workbook() if workbook is None else workbook
        if args.worker:
            return run_worker(args, workbook)
        names = args.scenario or DEFAULT_SUITE
        failures = 0
        for name in names:
            namespace = fresh_namespace(workbook)
            wb = GuardedWorkbook(workbook, namespace, interval=args.interval, sleep=sleep)
            ctx = Context(namespace, wb)
            print(f'--- {name} (namespace {namespace})', flush=True)
            preflight = ctx.store()
            if preflight.lock_owner() is not None:
                print('FAIL preflight: a writer lock already exists; harness stops without touching it')
                return 2
            SCENARIOS[name](ctx)
            failures += sum(1 for _, ok, _ in ctx.checks if not ok)
            if getattr(SCENARIOS[name], 'leaves_lock', False):
                print(f'summary: failures={failures}; stopped because the lock is retained')
                return EXIT_LOCK_RETAINED if not failures else 2
        print(f'summary: scenarios={len(names)} failures={failures} (fixture tabs kept hidden)')
        return 0 if not failures else 2
    except Exception as exc:
        print(f'harness_failed: {safe_code(exc)}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
