"""Bounded public HTTP fetching; never use this retry policy for social lanes."""

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import random
import time

import httpx


class FetchError(ValueError):
    """Sanitized failure code; never retain response bodies, URLs or credentials."""


class JsonFetcher:
    def __init__(self, client: httpx.Client, *, sleep=time.sleep,
                 now=lambda: datetime.now(timezone.utc), jitter=random.random):
        self.client, self.sleep, self.now, self.jitter = client, sleep, now, jitter

    def get_json(self, url: str) -> object:
        for attempt in range(3):
            response = None
            try:
                response = self.client.get(url, timeout=20, follow_redirects=False)
            except (httpx.TimeoutException, httpx.NetworkError):
                error = "network_or_timeout"
            else:
                if response.status_code == 200:
                    try:
                        return response.json()
                    except ValueError:
                        raise FetchError("invalid_json") from None
                error = f"http_{response.status_code}"
                if response.status_code not in {429, 500, 502, 503, 504}:
                    raise FetchError(error)
            if attempt == 2:
                raise FetchError(error)
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
                delay = max(delay, requested)
            if delay > 60:
                raise FetchError("retry_delay_exceeds_budget")
            self.sleep(delay)
        raise AssertionError("unreachable")
