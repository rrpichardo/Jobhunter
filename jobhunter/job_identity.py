"""Employer-link identity shared by collectors and existing-Sheet reconciliation."""

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

ATS_LINKS = [(re.compile(r"^https://(?:job-boards|boards)\.greenhouse\.io/([^/]+)/jobs/(\d+)(?:[/?#]|$)", re.I), "greenhouse"),
             (re.compile(r"^https://jobs\.lever\.co/([^/]+)/([0-9a-f-]{36})(?:[/?#]|$)", re.I), "lever"),
             (re.compile(r"^https://jobs\.ashbyhq\.com/([^/]+)/([0-9a-f-]{36})(?:[/?#]|$)", re.I), "ashby")]
TRACKING_PARAMS = re.compile(r"^(utm_.*|ref|referrer|source|src|gh_src|lever-source|lever-origin|fbclid|gclid|"
                             r"campaign|medium|trk|tracking.*)$", re.I)


def canonical_key(url: str) -> str:
    """Keep employer requisitions and case-sensitive URL components; remove tracking."""
    for pattern, kind in ATS_LINKS:
        match = pattern.match(url)
        if match:
            return f"{kind}:{match.group(1).lower()}:{match.group(2).lower()}"
    parts = urlsplit(url)
    pairs = sorted((k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
                   if not TRACKING_PARAMS.match(k))
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip('/'), urlencode(pairs), ''))
