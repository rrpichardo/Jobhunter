"""Fetch a public job-newsletter feed and write its recent editions as candidates for the AI read step.

  uv run --locked python -m scripts.newsletter_collect --source alirohde-rss --output <new file outside checkout>
      [--lookback-days 28]

Then, exactly as for X and LinkedIn posts (docs/ROUTINE_PROMPT.md): `ai_queue pull --source alirohde-rss --id-field
item_id`, Claude reads each edition, `social_posts validate --source alirohde-rss`, `source_probe --social-result`,
delivery, and only after delivery `ai_queue commit`. Public feed only: no login, no secret, no Sheet write.
"""

import argparse
from datetime import datetime, timezone
import urllib.error
import urllib.request

from jobhunter.artifacts import new_artifact_path, safe_error_code, write_artifact
from jobhunter.newsletter import FEEDS, edition_candidates
from jobhunter.social_collect import candidate_artifact

USER_AGENT = 'JobHunterBot/0.1 (personal job search; polite single requests)'
MAX_FEED_BYTES = 5 * 1024 * 1024


def fetch_feed(url):
    """(status, text). The standard-library client is used on purpose: the site's bot filter answers HTTP 403 to httpx
    but serves the same public feed to this one. One attempt, no redirects followed, size capped."""
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    opener = urllib.request.build_opener(NoRedirect)
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT,
                                                   'Accept': 'application/rss+xml, application/xml, */*'})
    try:
        with opener.open(request, timeout=30) as response:
            body = response.read(MAX_FEED_BYTES + 1)
            if len(body) > MAX_FEED_BYTES:
                raise ValueError('invalid_board_response')
            return response.status, body.decode('utf-8', errors='replace')
    except urllib.error.HTTPError as exc:
        return exc.code, ''


def main(argv=None, *, fetch=fetch_feed, now=lambda: datetime.now(timezone.utc)) -> int:
    parser = argparse.ArgumentParser(description='Job newsletter editions; never writes a Sheet.')
    parser.add_argument('--source', required=True, choices=sorted(FEEDS))
    parser.add_argument('--output', required=True, help='New artifact path outside the checkout')
    parser.add_argument('--lookback-days', type=int, default=28)
    args = parser.parse_args(argv)
    try:
        if not 1 <= args.lookback_days <= 365:
            raise ValueError('invalid_lookback_days')
        new_artifact_path(args.output)
        status, text = fetch(FEEDS[args.source]['url'])
        if status != 200:
            raise ValueError(f'http_{status}')
        moment = now()
        candidates, stats = edition_candidates(args.source, text, moment, args.lookback_days)
        artifact = candidate_artifact(args.source, candidates, moment.isoformat(), queries_run=1)
        cleaned_out = artifact['stats']['unreadable']  # editions the shared cleaning step refused (size, address form)
        artifact['stats'] = {**artifact['stats'], **stats, 'unreadable': stats['unreadable'] + cleaned_out}
        digest = write_artifact(args.output, artifact)
        print(f"newsletter_collected: editions={stats['editions']} in_window={stats['in_window']} "
              f"candidates={len(artifact['candidates'])} unreadable={artifact['stats']['unreadable']}")
        print(f'newsletter_candidates_sha256={digest}')
        return 0
    except (ValueError, TypeError, KeyError, OSError) as exc:  # OSError includes timeouts and connection errors
        code = str(exc)
        print(f"newsletter_failed: {code if code.startswith('http_') else safe_error_code(exc)}")
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
