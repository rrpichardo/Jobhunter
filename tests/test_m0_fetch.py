from datetime import datetime, timezone
from email.utils import format_datetime

import httpx
import pytest


def fetcher(handler, delays=None):
    from jobhunter.fetch import JsonFetcher
    return JsonFetcher(httpx.Client(transport=httpx.MockTransport(handler)),
                       sleep=(delays if delays is not None else []).append,
                       now=lambda: datetime(2026, 10, 17, tzinfo=timezone.utc),
                       jitter=lambda: 0)


def test_transient_failures_stop_after_three_total_attempts():
    from jobhunter.fetch import FetchError
    calls = []
    def handler(request):
        calls.append(request)
        assert request.extensions["timeout"]["read"] == 20
        return httpx.Response(503)
    with pytest.raises(FetchError, match="http_503"):
        fetcher(handler).get_json("https://example.com/jobs")
    assert len(calls) == 3


@pytest.mark.parametrize("retry_after,expected", [("5", 5),
    (format_datetime(datetime(2026, 10, 17, 0, 0, 7, tzinfo=timezone.utc)), 7)])
def test_honors_retry_after_seconds_and_http_date(retry_after, expected):
    delays, calls = [], []
    def handler(request):
        calls.append(1)
        return (httpx.Response(429, headers={"Retry-After": retry_after}) if len(calls) == 1
                else httpx.Response(200, json={"jobs": []}))
    assert fetcher(handler, delays).get_json("https://example.com/jobs") == {"jobs": []}
    assert delays == [expected]


def test_does_not_retry_before_long_server_delay_or_retry_permanent_errors():
    from jobhunter.fetch import FetchError
    for status, headers in [(403, {}), (429, {"Retry-After": "3600"})]:
        calls, delays = [], []
        def handler(request):
            calls.append(1)
            return httpx.Response(status, headers=headers)
        with pytest.raises(FetchError):
            fetcher(handler, delays).get_json("https://example.com/jobs")
        assert len(calls) == 1
        assert delays == []


def test_timeout_retries_but_invalid_json_does_not():
    from jobhunter.fetch import FetchError
    calls = []
    def handler(request):
        calls.append(1)
        if len(calls) == 1:
            raise httpx.ReadTimeout("secret-bearing URL must not reach logs")
        return httpx.Response(200, text="not-json")
    with pytest.raises(FetchError, match="invalid_json") as error:
        fetcher(handler).get_json("https://example.com/jobs")
    assert len(calls) == 2
    assert "secret" not in str(error.value)
