"""After the LinkedIn browser is started, a failure before or while reserving the day must still close it."""

import sys

import pytest

from scripts import linkedin_collect as li
from sheet_fakes import MemoryStore
from test_linkedin_collect import COOKIES, fetcher, ok

STAMP = '2026-10-19T16:00:00+00:00'


@pytest.mark.parametrize('failure', ['workbook', 'reservation'])
def test_startup_failure_disposes_of_the_authenticated_resource(tmp_path, monkeypatch, failure):
    # The external session is represented by a real temporary file: missing cleanup leaves it on disk.
    private = tmp_path / 'synthetic-session'
    private.write_text('synthetic fixture, no credentials')

    class Session:
        def close(self):
            private.unlink()

    session = Session()
    monkeypatch.setitem(sys.modules, 'playwright', object())
    monkeypatch.setattr(li, 'BrowserSession', lambda *a, **kw: session)
    if failure == 'workbook':
        from jobhunter import google_auth
        monkeypatch.setattr(google_auth, 'open_workbook', lambda: (_ for _ in ()).throw(ValueError('google_not_configured')))
        store = None
    else:
        monkeypatch.setattr(li, 'reserve', lambda *a, **kw: (_ for _ in ()).throw(ValueError('invalid_allowance_state')))
        store = object()
    output = tmp_path.parent / (tmp_path.name + '-output.json')
    code = li.main(['--run-id', 'repair-check', '--output', str(output)], store=store,
                   environ={'LINKEDIN_LI_AT': 'synthetic-only'}, now=lambda: STAMP)
    assert code == 2 and not output.exists()
    assert not private.exists(), 'the authenticated resource must be disposed of on every startup failure'


def test_the_day_is_reserved_with_the_collectors_own_clock(tmp_path):
    store = MemoryStore()
    out = tmp_path.parent / (tmp_path.name + '_li.json')
    code = li.main(['--run-id', 'r1', '--output', str(out)], store=store, fetcher=fetcher(ok()), environ=COOKIES,
                   now=lambda: '2031-03-04T16:00:00+00:00', sleep=lambda s: None, rng=lambda: 0.5)
    keys = [row[0] for row in store.tables['_State'][1:]]
    assert code == 0 and keys == ['allowance/linkedin-login/2031-03-04'], keys
