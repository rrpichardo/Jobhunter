"""Hacker News "Who is hiring?" in two code phases around one Claude extraction step.

  uv run --locked python -m scripts.hn_hiring candidates --output <new file outside checkout>
  (Claude proposes facts for each candidate comment and writes them to a new JSON file)
  uv run --locked python -m scripts.hn_hiring validate --candidates <file> --candidates-sha256 <digest>
      --extractions <file> --output <new file outside checkout>

Then pass the validated result and its digest to `scripts.source_probe --hn-result ... --hn-result-sha256 ...`.
Public Algolia endpoints only: no login, no secrets, no Sheet writes.
"""

import argparse
from datetime import datetime, timedelta, timezone
import time

import httpx

from jobhunter.artifacts import new_artifact_path, read_artifact, safe_error_code, write_artifact
from jobhunter.fetch import FetchError, JsonFetcher
from jobhunter.hn_hiring import (CANDIDATE_SAFETY_STOP, ITEM_URL, SEARCH_URL, SOURCE_ID, build_result,
                                 candidate_comments, select_threads)

LOOKBACK_DAYS = 28


def collect_candidates(fetcher, *, now, lookback_days, sleep=time.sleep):
    search = fetcher.get_json(SEARCH_URL)
    threads = select_threads(search, now, lookback_days)
    if not threads:
        raise ValueError('hn_no_threads')
    cutoff = now - timedelta(days=lookback_days)
    candidates, totals, truncated = [], {'top_level': 0, 'in_window': 0, 'role_mentions': 0, 'unreadable': 0}, False
    for thread in threads:
        sleep(1.0)
        found, stats = candidate_comments(thread, fetcher.get_json(ITEM_URL.format(id=thread['story_id'])), cutoff)
        for key, value in stats.items():
            totals[key] += value
        room = CANDIDATE_SAFETY_STOP - len(candidates)
        truncated = truncated or len(found) > room
        candidates.extend(found[:room])
    return {'schema_version': 1, 'source_id': SOURCE_ID, 'captured_at': now.isoformat(),
            'lookback_days': lookback_days, 'threads': threads, 'stats': totals,
            'truncated': truncated, 'candidates': candidates}


def main(argv=None, *, client=None, sleep=time.sleep, now=lambda: datetime.now(timezone.utc)) -> int:
    parser = argparse.ArgumentParser(description='Hacker News hiring comments; never writes a Sheet.')
    commands = parser.add_subparsers(dest='command', required=True)
    first = commands.add_parser('candidates')
    first.add_argument('--output', required=True, help='New artifact path outside the checkout')
    first.add_argument('--lookback-days', type=int, default=LOOKBACK_DAYS)
    second = commands.add_parser('validate')
    second.add_argument('--candidates', required=True)
    second.add_argument('--candidates-sha256', required=True)
    second.add_argument('--extractions', required=True)
    second.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    owned = client is None and args.command == 'candidates'
    client = httpx.Client() if owned else client
    try:
        if args.command == 'candidates':
            if not 1 <= args.lookback_days <= 365:
                raise ValueError('invalid_lookback_days')
            new_artifact_path(args.output)
            payload = collect_candidates(JsonFetcher(client, sleep=sleep), now=now(),
                                         lookback_days=args.lookback_days, sleep=sleep)
            digest = write_artifact(args.output, payload)
            stats = payload['stats']
            print(f"threads={len(payload['threads'])} comments_in_window={stats['in_window']} "
                  f"candidates={len(payload['candidates'])} unreadable={stats['unreadable']} "
                  f"truncated={payload['truncated']}")
            print(f'candidates_sha256={digest}')
            return 0
        data = read_artifact(args.candidates, expected_sha256=args.candidates_sha256)
        facts = read_artifact(args.extractions)
        if (not isinstance(data, dict) or data.get('schema_version') != 1 or data.get('source_id') != SOURCE_ID
                or not isinstance(data.get('candidates'), list) or not isinstance(data.get('stats'), dict)
                or not isinstance(data.get('threads'), list) or not isinstance(data.get('captured_at'), str)):
            raise ValueError('invalid_candidates')
        result = build_result(data['candidates'], facts, data['captured_at'], listed=data['stats'].get('in_window', 0),
                              stats=data['stats'], threads=data['threads'])
        digest = write_artifact(args.output, result)
        source = result['source']
        print(f"status={source['status']} valid={source['valid_jobs']} delivered={source['selected_for_m0']} "
              f"rejected={source['rejected_items']}")
        print(f'hn_result_sha256={digest}')
        return 0
    except FetchError as exc:
        print(f'hn_failed: {exc}')
        return 2
    except (ValueError, TypeError, KeyError, OSError) as exc:
        print(f'hn_failed: {safe_error_code(exc)}')
        return 2
    finally:
        if owned:
            client.close()


if __name__ == '__main__':
    raise SystemExit(main())
