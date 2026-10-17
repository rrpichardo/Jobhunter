import pytest


def test_proxy_auth_opens_only_configured_workbook_without_local_credentials(monkeypatch):
    from google.auth.credentials import AnonymousCredentials
    from jobhunter.google_auth import open_workbook
    import gspread
    seen = []
    class Client:
        def __init__(self, auth):
            assert isinstance(auth, AnonymousCredentials)
        def set_timeout(self, timeout):
            assert timeout == 20
        def open_by_key(self, key):
            seen.append(key)
            return 'workbook'
    monkeypatch.setattr(gspread, 'Client', Client)
    assert open_workbook({'JOBHUNTER_SPREADSHEET_ID': 'A' * 44,
                          'JOBHUNTER_GOOGLE_AUTH_MODE': 'network-secret'}) == 'workbook'
    assert seen == ['A' * 44]


@pytest.mark.parametrize('config', [{}, {'JOBHUNTER_SPREADSHEET_ID': '../bad'},
    {'JOBHUNTER_SPREADSHEET_ID': 'A' * 44, 'JOBHUNTER_GOOGLE_AUTH_MODE': 'unknown'}])
def test_invalid_auth_config_aborts_before_network(config, monkeypatch):
    from jobhunter.google_auth import open_workbook, GoogleSetupError
    import gspread
    monkeypatch.setattr(gspread, 'Client', lambda **kwargs: pytest.fail('network setup attempted'))
    with pytest.raises(GoogleSetupError, match='invalid_google_configuration'):
        open_workbook(config)


def test_google_error_is_sanitized(monkeypatch):
    from jobhunter.google_auth import open_workbook, GoogleSetupError
    import gspread
    class Client:
        def __init__(self, **kwargs): pass
        def set_timeout(self, timeout): pass
        def open_by_key(self, key):
            raise RuntimeError('private provider response must not escape')
    monkeypatch.setattr(gspread, 'Client', Client)
    with pytest.raises(GoogleSetupError, match='google_workbook_unavailable') as raised:
        open_workbook({'JOBHUNTER_SPREADSHEET_ID': 'A' * 44,
                       'JOBHUNTER_GOOGLE_AUTH_MODE': 'network-secret'})
    assert raised.value.__suppress_context__
    assert 'private' not in str(raised.value)
