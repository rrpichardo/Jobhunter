"""Small gspread adapter. No hidden retries and no raw provider errors in output."""

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import math
import re
import uuid

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
        self.rejected = bool(code.startswith('sheet_http_4') and code != 'sheet_http_408')


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
    def __init__(self, workbook, *, namespace=None):
        if namespace is not None and not re.fullmatch(r'_M0Test_[a-z0-9]{8,32}', namespace):
            raise ValueError('invalid_test_namespace')
        self.namespace = namespace
        self.workbook = workbook
        self.owner_token = None
        self.mutation_unknown = False
        self.refresh()

    def _title(self, title):
        return f'{self.namespace}_{title}' if self.namespace else title

    def activate_owner(self, owner):
        if self.mutation_unknown:
            raise ValueError('sheet_mutation_unconfirmed')
        self.owner_token = owner

    def deactivate_owner(self, owner):
        if self.owner_token == owner:
            self.owner_token = None

    def _mutation(self, function, body, *, values=False):
        if self.mutation_unknown:
            raise ValueError('sheet_mutation_unconfirmed')
        if not self.owner_token:
            raise ValueError('writer_lock_required')
        receipt = uuid.uuid4().hex
        if values:
            body = body | {'data': [*body['data'], {
                'range': f"'{LOCK_TITLE}'!C1", 'values': [[receipt]]}]}
        else:
            body = body | {'requests': [*body['requests'], {'updateCells': {
                'start': {'sheetId': LOCK_ID, 'rowIndex': 0, 'columnIndex': 2},
                'rows': [{'values': [{'userEnteredValue': {'stringValue': receipt}}]}],
                'fields': 'userEnteredValue'}}]}
        self.mutation_unknown = True
        try:
            result = _call(function, body)
            self.mutation_unknown = False
            return result
        except BaseException as original:
            if isinstance(original, SheetIOError) and original.rejected:
                self.mutation_unknown = False
                raise
            try:
                data = _call(self.workbook.values_get, f"'{LOCK_TITLE}'!A1:C1")
                row = data.get('values', [[]])[0]
                confirmed = len(row) >= 3 and row[0] == self.owner_token and row[2] == receipt
            except BaseException:
                confirmed = False
            if confirmed:
                self.mutation_unknown = False
                if isinstance(original, (KeyboardInterrupt, SystemExit)):
                    raise original
                return {'confirmed_after_uncertainty': True}
            # Absent/stale readback does not prove rejection. No later mutation,
            # retry, error logging, or lock deletion may pass this sticky state.
            if isinstance(original, (KeyboardInterrupt, SystemExit)):
                original.add_note('sheet_mutation_unconfirmed; lock retained')
                raise original
            raise ValueError('sheet_mutation_unconfirmed') from None

    def refresh(self):
        data = _call(self.workbook.fetch_sheet_metadata)
        self.all_tabs = {sheet['properties']['title']: sheet['properties'] for sheet in data['sheets']}
        self.tabs = {title: self.all_tabs[self._title(title)] for title in TABS
                     if self._title(title) in self.all_tabs}

    def create_lock(self, owner, started):
        if self.mutation_unknown:
            raise ValueError('sheet_mutation_unconfirmed')
        _call(self.workbook.batch_update, {'requests': [
            {'addSheet': {'properties': {'sheetId': LOCK_ID, 'title': LOCK_TITLE, 'hidden': True,
                'gridProperties': {'rowCount': 1, 'columnCount': 3}}}},
            {'updateCells': {'start': {'sheetId': LOCK_ID, 'rowIndex': 0, 'columnIndex': 0},
                'rows': [{'values': [{'userEnteredValue': {'stringValue': owner}},
                                     {'userEnteredValue': {'stringValue': started}}]}],
                'fields': 'userEnteredValue'}}]})

    def lock_owner(self):
        self.refresh()
        by_title = self.all_tabs.get(LOCK_TITLE)
        by_id = [props for props in self.all_tabs.values() if props['sheetId'] == LOCK_ID]
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
        if self.mutation_unknown:
            raise ValueError('sheet_mutation_unconfirmed')
        _call(self.workbook.batch_update, {'requests': [{'deleteSheet': {'sheetId': LOCK_ID}}]})

    def read(self, title):
        if title not in TABS:
            raise ValueError('unapproved_tab')
        data = _call(self.workbook.values_get, f"'{self._title(title)}'",
                     params={'valueRenderOption': 'UNFORMATTED_VALUE'})
        values = data.get('values', [])
        if not isinstance(values, list):
            raise ValueError('invalid_sheet_response')
        return values

    def ensure_tab(self, title, headers, *, hidden=False):
        if title not in TABS:
            raise ValueError('unapproved_tab')
        if title not in self.tabs:
            self._mutation(self.workbook.batch_update, {'requests': [{'addSheet': {'properties': {
                'title': self._title(title), 'hidden': hidden or self.namespace is not None,
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
            self._mutation(self.workbook.batch_update, {'requests': growth})
            # Append-only growth cannot truncate cells even with stale metadata.
            grid['rowCount'] = max(grid['rowCount'], max_row)
            grid['columnCount'] = max(grid['columnCount'], max_column)
        self._mutation(self.workbook.values_batch_update, {'valueInputOption': 'RAW', 'data': [
            {'range': f"'{self._title(title)}'!{rowcol_to_a1(w.row, w.column)}", 'values': w.values} for w in writes]}, values=True)
