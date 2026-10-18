"""Small gspread adapter. No hidden retries and no raw provider errors in output."""

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import math

from gspread.exceptions import APIError
from gspread.utils import rowcol_to_a1
from requests.exceptions import ConnectionError, SSLError, Timeout

from jobhunter.sheet_records import CellWrite

LOCK_ID = 1874202601
LOCK_TITLE = '_JobHunterLock'
TABS = frozenset({'Jobs', 'Sources', 'Run Log', '_State'})


class SheetIOError(ValueError):
    def __init__(self, code, *, transient=False, retry_after=None):
        super().__init__(code)
        self.transient, self.retry_after = transient, retry_after


def _call(function, *args, **kwargs):
    try:
        return function(*args, **kwargs)
    except Exception as exc:
        code, transient, wait = 'sheet_request_failed', False, None
        if isinstance(exc, APIError):
            status = exc.response.status_code
            if type(status) is int and 100 <= status <= 599:
                code, transient = f'sheet_http_{status}', status in {429, 500, 502, 503, 504}
            raw = exc.response.headers.get('Retry-After', '')
            try:
                wait = float(raw)
            except (TypeError, ValueError):
                try:
                    stamp = parsedate_to_datetime(raw)
                    wait = (stamp - datetime.now(timezone.utc)).total_seconds()
                except (TypeError, ValueError, OverflowError):
                    wait = None
            if wait is not None and (not math.isfinite(wait) or wait < 0):
                wait = None
        elif isinstance(exc, SSLError):
            code = 'sheet_tls_error'
        elif isinstance(exc, (Timeout, ConnectionError)):
            code, transient = 'sheet_transport_error', True
        raise SheetIOError(code, transient=transient, retry_after=wait) from None


class GspreadStore:
    def __init__(self, workbook):
        self.workbook = workbook
        self.refresh()

    def refresh(self):
        data = _call(self.workbook.fetch_sheet_metadata)
        self.tabs = {sheet['properties']['title']: sheet['properties'] for sheet in data['sheets']}

    def create_lock(self, owner, started):
        _call(self.workbook.batch_update, {'requests': [
            {'addSheet': {'properties': {'sheetId': LOCK_ID, 'title': LOCK_TITLE, 'hidden': True,
                'gridProperties': {'rowCount': 1, 'columnCount': 2}}}},
            {'updateCells': {'start': {'sheetId': LOCK_ID, 'rowIndex': 0, 'columnIndex': 0},
                'rows': [{'values': [{'userEnteredValue': {'stringValue': owner}},
                                     {'userEnteredValue': {'stringValue': started}}]}],
                'fields': 'userEnteredValue'}}]})

    def lock_owner(self):
        self.refresh()
        by_title = self.tabs.get(LOCK_TITLE)
        by_id = [props for props in self.tabs.values() if props['sheetId'] == LOCK_ID]
        if by_title is None and not by_id:
            return None
        if by_title is None or by_title['sheetId'] != LOCK_ID or len(by_id) != 1:
            raise ValueError('lock_identity_collision')
        data = _call(self.workbook.values_get, f"'{LOCK_TITLE}'!A1:B1")
        values = data.get('values', [])
        if not values or not values[0] or not isinstance(values[0][0], str):
            raise ValueError('invalid_lock_owner')
        return values[0][0]

    def drop_lock(self):
        _call(self.workbook.batch_update, {'requests': [{'deleteSheet': {'sheetId': LOCK_ID}}]})

    def read(self, title):
        if title not in TABS:
            raise ValueError('unapproved_tab')
        data = _call(self.workbook.values_get, f"'{title}'",
                     params={'valueRenderOption': 'UNFORMATTED_VALUE'})
        values = data.get('values', [])
        if not isinstance(values, list):
            raise ValueError('invalid_sheet_response')
        return values

    def ensure_tab(self, title, headers, *, hidden=False):
        if title not in TABS:
            raise ValueError('unapproved_tab')
        if title not in self.tabs:
            _call(self.workbook.batch_update, {'requests': [{'addSheet': {'properties': {
                'title': title, 'hidden': hidden,
                'gridProperties': {'rowCount': 1000, 'columnCount': max(16, len(headers))}}}}]})
            self.refresh()
        if not self.read(title):
            self.write(title, [CellWrite(1, 1, [list(headers)])])

    def write(self, title, writes):
        if title not in TABS or title not in self.tabs:
            raise ValueError('unapproved_tab')
        if not writes:
            return
        properties = self.tabs[title]
        grid = properties['gridProperties']
        max_row = max(w.row + len(w.values) - 1 for w in writes)
        max_column = max(w.column + max(map(len, w.values)) - 1 for w in writes)
        growth = []
        for dimension, count, required in [('ROWS', grid['rowCount'], max_row),
                                            ('COLUMNS', grid['columnCount'], max_column)]:
            if required > count:
                growth.append({'appendDimension': {'sheetId': properties['sheetId'],
                    'dimension': dimension, 'length': required - count}})
        if growth:
            _call(self.workbook.batch_update, {'requests': growth})
            # Append-only growth cannot truncate cells even with stale metadata.
            grid['rowCount'] = max(grid['rowCount'], max_row)
            grid['columnCount'] = max(grid['columnCount'], max_column)
        _call(self.workbook.values_batch_update, {'valueInputOption': 'RAW', 'data': [
            {'range': f"'{title}'!{rowcol_to_a1(w.row, w.column)}", 'values': w.values} for w in writes]})
