import pytest


def test_proxy_auth_opens_only_configured_workbook_without_local_credentials(monkeypatch):
    from google.auth.credentials import AnonymousCredentials
    from jobhunter.google_auth import open_workbook
    import gspread
    seen = []
    class Client:
        def __init__(self, auth, session=None):
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


def test_expected_google_failures_have_safe_actionable_codes(monkeypatch):
    from google.auth.exceptions import InvalidOperation
    from requests.exceptions import SSLError, Timeout, ConnectionError
    from gspread.exceptions import SpreadsheetNotFound, APIError
    from jobhunter.google_auth import open_workbook, GoogleSetupError
    import gspread
    from requests import Response
    response = Response()
    response.status_code = 429
    response._content = b'{"error":{"code":429,"message":"provider-private-detail"}}'
    cases = [(InvalidOperation('provider-private-detail'), 'google_proxy_auth_missing'),
             (SpreadsheetNotFound('provider-private-detail'), 'google_workbook_not_found'),
             (PermissionError('provider-private-detail'), 'google_workbook_forbidden'),
             (SSLError('provider-private-detail'), 'google_tls_error'),
             (Timeout('provider-private-detail'), 'google_timeout'),
             (ConnectionError('provider-private-detail'), 'google_transport_error'),
             (APIError(response), 'google_http_429')]
    class Client:
        def __init__(self, **kwargs): pass
        def set_timeout(self, timeout): pass
        def open_by_key(self, key): raise current_error
    monkeypatch.setattr(gspread, 'Client', Client)
    for current_error, expected in cases:
        with pytest.raises(GoogleSetupError) as raised:
            open_workbook({'JOBHUNTER_SPREADSHEET_ID': 'A' * 44,
                           'JOBHUNTER_GOOGLE_AUTH_MODE': 'network-secret'})
        assert str(raised.value) == expected
        assert raised.value.__suppress_context__


def test_auth_transport_cannot_silently_resubmit_a_mutation(monkeypatch):
    import gspread
    from jobhunter.google_auth import open_workbook
    captured = []
    class Client(gspread.Client):
        def open_by_key(self, key):
            captured.append(self.http_client.session)
            return 'workbook'
    monkeypatch.setattr(gspread, 'Client', Client)
    assert open_workbook({'JOBHUNTER_SPREADSHEET_ID': 'A' * 44,
                          'JOBHUNTER_GOOGLE_AUTH_MODE': 'network-secret'}) == 'workbook'
    assert captured[0]._max_refresh_attempts == 0
    assert captured[0].get_adapter('https://').max_retries.total == 0


def test_auth_transport_does_not_follow_mutation_redirects(monkeypatch):
    import gspread
    from google.auth.transport.requests import AuthorizedSession
    from jobhunter.google_auth import open_workbook
    captured = []
    class Client(gspread.Client):
        def open_by_key(self, key):
            captured.append(self.http_client.session)
            return 'workbook'
    monkeypatch.setattr(gspread, 'Client', Client)
    open_workbook({'JOBHUNTER_SPREADSHEET_ID': 'A' * 44,
                   'JOBHUNTER_GOOGLE_AUTH_MODE': 'network-secret'})
    observed = []
    monkeypatch.setattr(AuthorizedSession, 'request', lambda self, *a, **kw: observed.append(kw))
    captured[0].request('POST', 'https://sheets.googleapis.com/', allow_redirects=True)
    assert observed[0]['allow_redirects'] is False
