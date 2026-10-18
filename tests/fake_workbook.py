"""In-memory stand-in for the gspread Spreadsheet calls GspreadStore makes."""

from copy import deepcopy
import re

from gspread.exceptions import APIError
from requests import Response


def api_error(status):
    response = Response()
    response.status_code = status
    response._content = ('{"error": {"code": %d, "message": "private body"}}' % status).encode()
    return APIError(response)


def _column(letters):
    number = 0
    for letter in letters:
        number = number * 26 + ord(letter) - 64
    return number


class FakeWorkbook:
    def __init__(self):
        self.sheets = {}  # title -> {'props': {...}, 'rows': [[...]]}
        self.next_id = 1
        self.calls = []

    def fetch_sheet_metadata(self):
        return {'sheets': [{'properties': deepcopy(s['props'])} for s in self.sheets.values()]}

    def _by_id(self, sheet_id):
        return next(s for s in self.sheets.values() if s['props']['sheetId'] == sheet_id)

    def batch_update(self, body):
        self.calls.append('batch_update')
        # Validate every request first so a rejected batch changes nothing (atomic).
        titles = set(self.sheets)
        ids = {s['props']['sheetId'] for s in self.sheets.values()}
        for request in body['requests']:
            if 'addSheet' in request:
                props = request['addSheet']['properties']
                sheet_id = props.get('sheetId')
                if props['title'] in titles or sheet_id in ids:
                    raise api_error(400)
                titles.add(props['title'])
                ids.add(sheet_id)
        for request in body['requests']:
            if 'addSheet' in request:
                props = deepcopy(request['addSheet']['properties'])
                if 'sheetId' not in props:
                    props['sheetId'] = self.next_id
                    self.next_id += 1
                self.sheets[props['title']] = {'props': props, 'rows': []}
            elif 'appendDimension' in request:
                args = request['appendDimension']
                grid = self._by_id(args['sheetId'])['props']['gridProperties']
                key = 'rowCount' if args['dimension'] == 'ROWS' else 'columnCount'
                grid[key] += args['length']
            elif 'updateCells' in request:
                args = request['updateCells']
                sheet = self._by_id(args['start']['sheetId'])
                for r, row in enumerate(args['rows']):
                    values = [v['userEnteredValue']['stringValue'] for v in row['values']]
                    self._put(sheet, args['start']['rowIndex'] + r, args['start']['columnIndex'], values)
            elif 'deleteSheet' in request:
                sheet = self._by_id(request['deleteSheet']['sheetId'])
                del self.sheets[sheet['props']['title']]
            else:
                raise api_error(400)
        return {}

    @staticmethod
    def _put(sheet, row, column, values):
        rows = sheet['rows']
        while len(rows) <= row:
            rows.append([])
        while len(rows[row]) < column + len(values):
            rows[row].append('')
        rows[row][column:column + len(values)] = values

    def _parse(self, name):
        match = re.fullmatch(r"'(.+)'(?:!([A-Z]+)(\d+)(?::([A-Z]+)(\d+))?)?", name)
        if not match or match.group(1) not in self.sheets:
            raise api_error(400)
        return self.sheets[match.group(1)], match

    def values_batch_update(self, body):
        self.calls.append('values_batch_update')
        staged = []
        for item in body['data']:
            sheet, match = self._parse(item['range'])
            row, column = int(match.group(3)) - 1, _column(match.group(2)) - 1
            grid = sheet['props']['gridProperties']
            if (row + len(item['values']) > grid['rowCount']
                    or column + max(map(len, item['values'])) > grid['columnCount']):
                raise api_error(400)
            staged.append((sheet, row, column, item['values']))
        for sheet, row, column, values in staged:  # all-or-nothing
            for offset, line in enumerate(values):
                self._put(sheet, row + offset, column, list(line))
        return {}

    def values_get(self, name, params=None):
        self.calls.append('values_get')
        sheet, match = self._parse(name)
        rows = deepcopy(sheet['rows'])
        if match.group(2):
            r1, c1 = int(match.group(3)) - 1, _column(match.group(2)) - 1
            r2 = int(match.group(5)) - 1 if match.group(5) else r1
            c2 = _column(match.group(4)) - 1 if match.group(4) else c1
            rows = [(row + [''] * (c2 + 1))[c1:c2 + 1] for row in rows[r1:r2 + 1]]
        for row in rows:
            while row and row[-1] == '':
                row.pop()
        while rows and not rows[-1]:
            rows.pop()
        return {'values': rows} if rows else {}
