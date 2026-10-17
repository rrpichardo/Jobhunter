"""Bounded public HTTP fetching; never use this retry policy for social lanes."""

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import math
import random
import time

import httpx


class FetchError(ValueError):
    """Sanitized failure code; never retain response bodies, URLs or credentials."""

    def __init__(self, code, *, attempts=0, status=None, retry_after=None):
        super().__init__(code)
        self.attempts, self.status, self.retry_after = attempts, status, retry_after


class JsonFetcher:
    def __init__(self, client: httpx.Client, *, sleep=time.sleep,
                 now=lambda: datetime.now(timezone.utc), jitter=random.random):
        self.client, self.sleep, self.now, self.jitter = client, sleep, now, jitter
        self.last_attempts = 0

    def get_json(self, url: str) -> object:
        for attempt in range(3):
            self.last_attempts = attempt + 1
            response = None
            try:
                response = self.client.get(url, timeout=20, follow_redirects=False)
            except httpx.HTTPError as exc:
                error = ("timeout" if isinstance(exc, httpx.TimeoutException)
                         else "transport_error")
                if isinstance(exc, (httpx.UnsupportedProtocol, httpx.DecodingError)):
                    raise FetchError("protocol_or_decode_error", attempts=attempt + 1) from None
            else:
                if response.status_code == 200:
                    try:
                        return response.json()
                    except (ValueError, RecursionError):
                        raise FetchError("invalid_json", attempts=attempt + 1, status=200) from None
                error = f"http_{response.status_code}"
                if response.status_code not in {429, 500, 502, 503, 504}:
                    raise FetchError(error, attempts=attempt + 1, status=response.status_code)
            if attempt == 2:
                raise FetchError(error, attempts=attempt + 1,
                                 status=response.status_code if response is not None else None)
            delay = (2 ** attempt) + self.jitter()
            if response is not None and (raw := response.headers.get("Retry-After")):
                try:
                    requested = float(raw)
                except ValueError:
                    try:
                        stamp = parsedate_to_datetime(raw)
                        if stamp.utcoffset() is None:
                            raise ValueError
                        requested = (stamp - self.now()).total_seconds()
                    except (ValueError, TypeError, OverflowError):
                        requested = delay
                if math.isfinite(requested) and requested >= 0:
                    delay = max(delay, requested)
            if delay > 60:
                raise FetchError("retry_delay_exceeds_budget", attempts=attempt + 1,
                                 status=response.status_code, retry_after=delay)
            self.sleep(delay)
        raise AssertionError("unreachable")
