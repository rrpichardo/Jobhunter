import pytest
from requests import Response
from gspread.exceptions import APIError


class Workbook:
    def __init__(self):
        self.calls = []
        self.metadata = {'sheets': [{'properties': {'title': 'Jobs', 'sheetId': 1,
                         'gridProperties': {'rowCount': 2, 'columnCount': 16}}}]}
    def fetch_sheet_metadata(self): return self.metadata
    def batch_update(self, body): self.calls.append(('structural', body)); return {}
    def values_batch_update(self, body): self.calls.append(('values', body)); return {}
    def values_get(self, name, params=None):
        self.calls.append(('get', name, params))
        return {'values': [['literal']]}


def test_lock_creation_is_one_atomic_structural_batch_with_owner():
    from jobhunter.sheet_io import GspreadStore, LOCK_ID
    workbook = Workbook()
    store = GspreadStore(workbook)
    store.create_lock('owner', '2026-10-17T00:00:00Z')
    assert len(workbook.calls) == 1
    requests = workbook.calls[0][1]['requests']
    assert requests[0]['addSheet']['properties'] == {
        'sheetId': LOCK_ID, 'title': '_JobHunterLock', 'hidden': True,
        'gridProperties': {'rowCount': 1, 'columnCount': 3}}
    assert requests[1]['updateCells']['start']['sheetId'] == LOCK_ID
    assert requests[1]['updateCells']['rows'][0]['values'][0]['userEnteredValue'] == {'stringValue': 'owner'}


def test_write_uses_raw_and_only_increases_grid_without_replacing_rows():
    from jobhunter.sheet_io import GspreadStore
    from jobhunter.sheet_records import CellWrite
    workbook = Workbook()
    store = GspreadStore(workbook)
    store.activate_owner('owner')
    store.write('Jobs', [CellWrite(4, 2, [['=literal']])])
    assert workbook.calls[0][0] == 'structural'
    assert workbook.calls[0][1]['requests'][0] == {'appendDimension': {'sheetId': 1, 'dimension': 'ROWS', 'length': 2}}
    assert len(workbook.calls[0][1]['requests']) == 2
    assert workbook.calls[0][1]['requests'][1]['updateCells']['start']['columnIndex'] == 2
    assert workbook.calls[1][0] == 'values'
    body = workbook.calls[1][1]
    assert body['valueInputOption'] == 'RAW'
    assert body['data'][0] == {'range': "'Jobs'!B4", 'values': [['=literal']]}
    assert len(body['data']) == 2 and body['data'][1]['range'] == "'_JobHunterLock'!C1"
    assert len(body['data'][1]['values'][0][0]) == 32


def test_api_failures_do_not_leak_bodies_and_retain_finite_retry_delay():
    from jobhunter.sheet_io import GspreadStore, SheetIOError
    workbook = Workbook()
    response = Response()
    response.status_code = 429
    response.headers['Retry-After'] = '12'
    response._content = b'{"error":{"code":429,"message":"private-provider-body"}}'
    def fail(body): raise APIError(response)
    workbook.values_batch_update = fail
    from jobhunter.sheet_records import CellWrite
    store = GspreadStore(workbook)
    store.activate_owner('owner')
    with pytest.raises(SheetIOError) as caught:
        store.write('Jobs', [CellWrite(2, 2, [['hello']])])
    assert str(caught.value) == 'sheet_http_429'
    assert caught.value.transient and caught.value.retry_after == 12
    assert caught.value.__suppress_context__


def test_nonfinite_retry_header_is_ignored_and_collision_fails_closed():
    from jobhunter.sheet_io import GspreadStore, LOCK_ID
    workbook = Workbook()
    workbook.metadata['sheets'].append({'properties': {'title': '_JobHunterLock', 'sheetId': LOCK_ID + 1}})
    store = GspreadStore(workbook)
    with pytest.raises(ValueError, match='lock_identity_collision'): store.lock_owner()
    assert not workbook.calls


@pytest.mark.parametrize('header', ['inf', '1e999', 'nan', '-2'])
def test_invalid_retry_after_is_not_retained_in_runtime_evidence(header):
    from jobhunter.sheet_io import GspreadStore, SheetIOError
    from jobhunter.sheet_records import CellWrite
    workbook = Workbook()
    response = Response()
    response.status_code = 429
    response.headers['Retry-After'] = header
    response._content = b'{"error":{"code":429,"message":"private"}}'
    def fail(body): raise APIError(response)
    workbook.values_batch_update = fail
    store = GspreadStore(workbook)
    store.activate_owner('owner')
    with pytest.raises(SheetIOError) as caught:
        store.write('Jobs', [CellWrite(2, 2, [['hello']])])
    assert caught.value.retry_after is None


def test_uncertain_write_before_apply_retains_lock_and_never_resubmits():
    from jobhunter.sheet_io import GspreadStore
    from jobhunter.sheet_records import CellWrite
    from requests.exceptions import Timeout
    workbook = Workbook()
    calls = []
    def late_write(body):
        calls.append(body)
        raise Timeout('not yet applied')
    workbook.values_batch_update = late_write
    store = GspreadStore(workbook)
    store.activate_owner('owner')
    with pytest.raises(ValueError, match='sheet_mutation_unconfirmed'):
        store.write('Jobs', [CellWrite(2, 2, [['new']])])
    assert store.mutation_unknown
    with pytest.raises(ValueError, match='sheet_mutation_unconfirmed'): store.drop_lock()
    assert len(calls) == 1


def test_receipt_proves_applied_timeout_without_repeating_or_overwriting_notes():
    from jobhunter.sheet_io import GspreadStore
    from jobhunter.sheet_records import CellWrite
    from requests.exceptions import Timeout
    workbook = Workbook()
    receipt, calls = [], []
    def applied_write(body):
        calls.append(body)
        receipt[:] = body['data'][-1]['values'][0]
        raise Timeout('applied but response lost')
    def read_receipt(name, params=None):
        return {'values': [['owner', 'stamp', receipt[0]]]}
    workbook.values_batch_update, workbook.values_get = applied_write, read_receipt
    store = GspreadStore(workbook)
    store.activate_owner('owner')
    store.write('Jobs', [CellWrite(2, 2, [['new']])])
    assert not store.mutation_unknown and len(calls) == 1
    assert calls[0]['data'][-1]['range'] == "'_JobHunterLock'!C1"


@pytest.mark.parametrize('stage', ['tab_creation', 'grid_growth', 'values'])
def test_unknown_mutation_at_any_stage_stops_before_later_writes(stage):
    from jobhunter.sheet_io import GspreadStore
    from jobhunter.sheet_records import CellWrite
    from requests.exceptions import Timeout
    workbook = Workbook()
    submitted = []
    def uncertain(body):
        submitted.append(body)
        raise Timeout('unknown')
    if stage == 'values': workbook.values_batch_update = uncertain
    else: workbook.batch_update = uncertain
    store = GspreadStore(workbook)
    store.activate_owner('owner')
    with pytest.raises(ValueError, match='sheet_mutation_unconfirmed'):
        if stage == 'tab_creation': store.ensure_tab('_State', ['Key', 'Value'], hidden=True)
        else: store.write('Jobs', [CellWrite(4 if stage == 'grid_growth' else 2, 2, [['new']])])
    assert store.mutation_unknown and len(submitted) == 1
    assert not any(call[0] == 'values' for call in workbook.calls)


def test_matching_old_values_without_a_unique_receipt_never_confirms_a_write():
    from jobhunter.sheet_io import GspreadStore
    from jobhunter.sheet_records import CellWrite
    from requests.exceptions import Timeout
    workbook = Workbook()
    workbook.values_get = lambda *a, **kw: {'values': [['owner', 'stamp', 'old-receipt']]}
    workbook.values_batch_update = lambda body: (_ for _ in ()).throw(Timeout())
    store = GspreadStore(workbook)
    store.activate_owner('owner')
    with pytest.raises(ValueError, match='sheet_mutation_unconfirmed'):
        store.write('Jobs', [CellWrite(2, 2, [['already-present']])])
    assert store.mutation_unknown


def test_keyboard_interrupt_during_mutation_remains_an_interrupt_and_retains_unknown_state():
    from jobhunter.sheet_io import GspreadStore
    from jobhunter.sheet_records import CellWrite
    workbook = Workbook()
    workbook.values_batch_update = lambda body: (_ for _ in ()).throw(KeyboardInterrupt())
    store = GspreadStore(workbook)
    store.activate_owner('owner')
    with pytest.raises(KeyboardInterrupt): store.write('Jobs', [CellWrite(2, 2, [['new']])])
    assert store.mutation_unknown


def test_test_namespace_isolated_data_tabs_still_use_global_lock_receipts():
    from jobhunter.sheet_io import GspreadStore
    from jobhunter.sheet_records import CellWrite
    workbook = Workbook()
    workbook.metadata['sheets'][0]['properties']['title'] = '_M0Test_abcd1234_Jobs'
    store = GspreadStore(workbook, namespace='_M0Test_abcd1234')
    store.activate_owner('owner')
    store.write('Jobs', [CellWrite(2, 2, [['fixture']])])
    body = workbook.calls[-1][1]
    assert body['data'][0]['range'] == "'_M0Test_abcd1234_Jobs'!B2"
    assert body['data'][-1]['range'] == "'_JobHunterLock'!C1"
    with pytest.raises(ValueError, match='invalid_test_namespace'): GspreadStore(workbook, namespace='Jobs')
