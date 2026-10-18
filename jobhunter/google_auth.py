"""Sheets client for a GCP network secret injected outside the cloud VM.

The environment's proxy authenticates outbound Sheets requests. AnonymousCredentials
here means Python holds no key/token; the private workbook still requires Google's
normal authorization. This route must be proven in the real JobHunterEnv.
"""

import os
import re

from google.auth.credentials import AnonymousCredentials
from google.auth.exceptions import InvalidOperation
import gspread
from gspread.exceptions import APIError, SpreadsheetNotFound
from requests.exceptions import SSLError, Timeout, ConnectionError


class GoogleSetupError(ValueError):
    """Operator-safe setup failure; never include provider response bodies."""


def open_workbook(environ=None):
    """Open the explicitly configured workbook; never discover via Drive."""
    config = os.environ if environ is None else environ
    workbook_id = config.get('JOBHUNTER_SPREADSHEET_ID', '')
    if (config.get('JOBHUNTER_GOOGLE_AUTH_MODE') != 'network-secret'
            or not isinstance(workbook_id, str)
            or re.fullmatch(r'[A-Za-z0-9_-]{20,200}', workbook_id) is None):
        raise GoogleSetupError('invalid_google_configuration')
    try:
        client = gspread.Client(auth=AnonymousCredentials())
        client.set_timeout(20)
        return client.open_by_key(workbook_id)
    except Exception as exc:
        # Provider errors can embed request/response content. Keep them out of
        # command output, including exception chaining printed by a traceback.
        code = 'google_workbook_unavailable'
        if isinstance(exc, InvalidOperation):
            code = 'google_proxy_auth_missing'
        elif isinstance(exc, SpreadsheetNotFound):
            code = 'google_workbook_not_found'
        elif isinstance(exc, PermissionError):
            code = 'google_workbook_forbidden'
        elif isinstance(exc, SSLError):
            code = 'google_tls_error'
        elif isinstance(exc, Timeout):
            code = 'google_timeout'
        elif isinstance(exc, ConnectionError):
            code = 'google_transport_error'
        elif isinstance(exc, APIError):
            status = exc.response.status_code
            if type(status) is int and 100 <= status <= 599:
                code = f'google_http_{status}'
        raise GoogleSetupError(code) from None
