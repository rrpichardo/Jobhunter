"""Validate Claude's facts for X or LinkedIn hiring posts; the collectors that fetch the posts are separate.

  uv run --locked python -m scripts.social_posts validate --source x-twscrape --candidates <file>
      --candidates-sha256 <digest> --extractions <file> --output <new file outside checkout>

Candidates come from a collector (not built yet) as {"candidates": [{"url","created_at","text","links"}], ...}; the
AI queue (`scripts.ai_queue pull --id-field item_id`) hands Claude only the unread ones. Claude writes
{"processed": [item ids], "facts": [{item_id, title, company, location, salary, description_quote, apply_url}]}.
Same rules as Hacker News: every value must appear verbatim in that post, the Job ID, date and the fallback
post-URL lead come from code, and nothing here touches a social site or a Sheet.
"""

import argparse

from jobhunter.artifacts import read_artifact, safe_error_code, write_artifact
from jobhunter.post_facts import SOCIAL, clean_social_candidates, format_trace, social_result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Social post facts; no network, no Sheet.')
    commands = parser.add_subparsers(dest='command', required=True)
    sub = commands.add_parser('validate')
    sub.add_argument('--source', required=True, choices=sorted(SOCIAL))
    sub.add_argument('--candidates', required=True)
    sub.add_argument('--candidates-sha256', required=True)
    sub.add_argument('--extractions', required=True)
    sub.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    try:
        data = read_artifact(args.candidates, expected_sha256=args.candidates_sha256)
        if (not isinstance(data, dict) or data.get('schema_version') != 1 or data.get('source_id') != args.source
                or not isinstance(data.get('captured_at'), str) or not isinstance(data.get('stats'), dict)):
            raise ValueError('invalid_candidates')
        candidates, unreadable = clean_social_candidates(args.source, data.get('candidates'))
        extractions = read_artifact(args.extractions)
        if (not isinstance(extractions, dict) or set(extractions) != {'processed', 'facts'}
                or not isinstance(extractions['processed'], list) or not isinstance(extractions['facts'], list)):
            raise ValueError('invalid_extractions')
        known = {c['item_id'] for c in candidates}
        processed = extractions['processed']
        if any(not isinstance(i, str) or i not in known for i in processed) or len(set(processed)) != len(processed):
            raise ValueError('invalid_extractions')
        read = [c for c in candidates if c['item_id'] in set(processed)]  # a fact for an unread post is rejected
        stats = {**data['stats'], 'unreadable': data['stats'].get('unreadable', 0) + unreadable}
        result = social_result(args.source, read, extractions['facts'], data['captured_at'],
                               listed=len(candidates), stats=stats, error=str(data.get('error') or ''),
                               known_ids=known)
        # A post whose proposed fact was rejected stays queued, so one extraction error cannot lose a job.
        held = set(result['rejected_item_ids'])
        result['processed_ids'] = sorted(set(processed) - held)
        digest = write_artifact(args.output, result)
        source = result['source']
        print(f"status={source['status']} valid={source['valid_jobs']} delivered={source['selected_for_m0']} "
              f"rejected={source['rejected_items']} held_for_retry={len(held)}")
        print(format_trace(result))
        print(f'social_result_sha256={digest}')
        return 0
    except (ValueError, TypeError, KeyError, OSError) as exc:
        print(f'social_failed: {safe_error_code(exc)}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
