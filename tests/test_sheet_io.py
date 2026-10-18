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
        'gridProperties': {'rowCount': 1, 'columnCount': 2}}
    assert requests[1]['updateCells']['start']['sheetId'] == LOCK_ID
    assert requests[1]['updateCells']['rows'][0]['values'][0]['userEnteredValue'] == {'stringValue': 'owner'}


def test_write_uses_raw_and_only_increases_grid_without_replacing_rows():
    from jobhunter.sheet_io import GspreadStore
    from jobhunter.sheet_records import CellWrite
    workbook = Workbook()
    GspreadStore(workbook).write('Jobs', [CellWrite(4, 2, [['=literal']])])
    assert workbook.calls[0][0] == 'structural'
    assert workbook.calls[0][1]['requests'] == [{'appendDimension': {'sheetId': 1, 'dimension': 'ROWS', 'length': 2}}]
    assert workbook.calls[1] == ('values', {'valueInputOption': 'RAW', 'data': [
        {'range': "'Jobs'!B4", 'values': [['=literal']]}]})


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
    with pytest.raises(SheetIOError) as caught:
        GspreadStore(workbook).write('Jobs', [CellWrite(2, 2, [['hello']])])
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
    with pytest.raises(SheetIOError) as caught:
        GspreadStore(workbook).write('Jobs', [CellWrite(2, 2, [['hello']])])
    assert caught.value.retry_after is None
