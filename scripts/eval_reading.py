"""Compare two models on the same reading task (which jobs does each find in the same posts?).

  uv run --locked python -m scripts.eval_reading sample --candidates <work file> [--candidates ...] --size 100 --seed 1
      --output <new sample file outside checkout>
  (run the reading step once per model on the sample; each writes a facts file in the documented format)
  uv run --locked python -m scripts.eval_reading compare --candidates <sample file> --a <facts file> --b <facts file>
      [--a-name sonnet] [--b-name haiku] --output <new report file outside checkout>

Both fact files go through the SAME code checker the pipeline uses (`post_facts.build_result`: every value must appear
word for word in the item, then the role/salary/location filter), so what is compared is what would reach the Sheet.
Per item the two models AGREE when they deliver the same set of (title, company) pairs (both delivering nothing counts
as agreement). The report prints the agreement percentage, the per-item table (shareable as it stands) and each model's
rejected-fact counts. Nothing here calls a model or touches a Sheet; see docs/evals/HAIKU_READING_EVAL.md.
"""

import argparse
import random
import re

from jobhunter.artifacts import new_artifact_path, read_artifact, safe_error_code, write_artifact
from jobhunter.hn_hiring import PERMALINK as HN_PERMALINK
from jobhunter.post_facts import build_result

ID_FIELDS = ('item_id', 'comment_id')


def id_field(items):
    return next((f for f in ID_FIELDS if items and f in items[0]), None)


def norm(text):
    return re.sub(r'\W+', ' ', text.casefold()).strip()


def load_items(paths):
    items = []
    for path in paths:
        data = read_artifact(path)
        found = data.get('candidates') if isinstance(data, dict) else None
        if not isinstance(found, list):
            raise ValueError('invalid_candidates')
        items.extend(found)
    field = id_field(items)
    if field is None or len({i[field] for i in items}) != len(items):
        raise ValueError('invalid_candidates')
    return items, field


def sample(items, size, seed):
    """Deterministic sample, half from items that mention a collected role (where reading matters) and half from the rest."""
    from jobhunter.postings import ROLE_TEXT
    rng = random.Random(seed)
    with_role = [i for i in items if ROLE_TEXT.search(i['text'])]
    without = [i for i in items if not ROLE_TEXT.search(i['text'])]
    rng.shuffle(with_role)
    rng.shuffle(without)
    half = size // 2
    chosen = with_role[:max(half, size - len(without))][:size]
    chosen += without[:size - len(chosen)]
    return chosen


def delivered(items, field, facts):
    """({item id: {(title, company)}}, rejected fact count) after the pipeline's own validation."""
    processed = facts.get('processed') if isinstance(facts, dict) else None
    listed = facts.get('facts') if isinstance(facts, dict) else None
    if not isinstance(processed, list) or not isinstance(listed, list):
        raise ValueError('invalid_extractions')
    read = [i for i in items if i[field] in set(processed)]
    result = build_result('eval', read, listed, '2026-01-01T00:00:00+00:00', id_field=field, id_prefix='eval',
                          permalink=lambda c: c.get('url') or HN_PERMALINK.format(id=c[field]), listed=len(items), stats={},
                          attempts=1, known_ids={i[field] for i in items})
    by_id = {i[field]: set() for i in items}
    for posting in result['postings']:
        item_id = posting['job_id'].split(':')[1]
        by_id.setdefault(item_id, set()).add((norm(posting['title']), norm(posting['company'])))
    return by_id, result['source']['rejected_items'], len(read)


def compare(items, field, a, b, names):
    da, rej_a, read_a = delivered(items, field, a)
    db, rej_b, read_b = delivered(items, field, b)
    rows, agree = [], 0
    for item in items:
        key = item[field]
        same = da[key] == db[key]
        agree += same
        rows.append({'item': key, 'agree': same, names[0]: sorted(' | '.join(p) for p in da[key]),
                     names[1]: sorted(' | '.join(p) for p in db[key])})
    jobs_a = sum(len(v) for v in da.values())
    jobs_b = sum(len(v) for v in db.values())
    both = sum(len(da[k] & db[k]) for k in da)
    return {'items': len(items), 'agree': agree, 'agreement_percent': round(100 * agree / len(items), 1) if items else 0.0,
            'jobs': {names[0]: jobs_a, names[1]: jobs_b, 'in_both': both},
            'rejected_facts': {names[0]: rej_a, names[1]: rej_b}, 'items_read': {names[0]: read_a, names[1]: read_b},
            'rows': rows}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Compare two models on the same reading task; calls no model.')
    commands = parser.add_subparsers(dest='command', required=True)
    first = commands.add_parser('sample')
    first.add_argument('--candidates', action='append', required=True)
    first.add_argument('--size', type=int, default=100)
    first.add_argument('--seed', type=int, default=1)
    first.add_argument('--output', required=True)
    second = commands.add_parser('compare')
    second.add_argument('--candidates', required=True)
    second.add_argument('--a', required=True)
    second.add_argument('--b', required=True)
    second.add_argument('--a-name', default='sonnet')
    second.add_argument('--b-name', default='haiku')
    second.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    try:
        new_artifact_path(args.output)
        if args.command == 'sample':
            if not 1 <= args.size <= 1000:
                raise ValueError('invalid_sample_size')
            items, field = load_items(args.candidates)
            chosen = sample(items, args.size, args.seed)
            digest = write_artifact(args.output, {'schema_version': 1, 'candidates': chosen, 'seed': args.seed})
            print(f'sampled={len(chosen)} of {len(items)} id_field={field}')
            print(f'sample_sha256={digest}')
            return 0
        items, field = load_items([args.candidates])
        report = compare(items, field, read_artifact(args.a), read_artifact(args.b), (args.a_name, args.b_name))
        digest = write_artifact(args.output, report)
        print(f"items={report['items']} agree={report['agree']} agreement_percent={report['agreement_percent']}")
        print(f"jobs={report['jobs']} rejected_facts={report['rejected_facts']}")
        for row in report['rows']:
            if not row['agree']:
                print(f"DISAGREE {row['item']}: {args.a_name}={row[args.a_name]} {args.b_name}={row[args.b_name]}")
        print(f'eval_report_sha256={digest}')
        return 0
    except (ValueError, TypeError, KeyError, OSError) as exc:
        print(f'eval_failed: {safe_error_code(exc)}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
