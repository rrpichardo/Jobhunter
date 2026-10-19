"""The two-model reading comparison: sampling is deterministic and agreement is judged on what the checker delivers."""

import json

from scripts import eval_reading as ev

TEXT = 'Acme is hiring a Senior Product Manager, AI (Remote US). Salary $200,000 - $250,000.'
ITEMS = [{'item_id': str(n), 'url': f'https://x.com/a/status/{n}', 'created_at': '2026-10-15T12:00:00+00:00',
          'text': TEXT if n % 2 else 'Nothing relevant here.', 'links': []} for n in range(1, 21)]


def fact(item_id, title='Senior Product Manager, AI', company='Acme'):
    return {'item_id': item_id, 'title': title, 'company': company, 'location': 'Remote US', 'salary': '$200,000 - $250,000',
            'description_quote': TEXT[:60], 'apply_url': ''}


def write(tmp_path, name, data):
    path = tmp_path / name
    path.write_text(json.dumps(data))
    return str(path)


def test_the_sample_is_deterministic_and_leans_on_items_that_mention_a_role():
    first, second = ev.sample(ITEMS, 10, 1), ev.sample(ITEMS, 10, 1)
    assert [i['item_id'] for i in first] == [i['item_id'] for i in second] and len(first) == 10
    assert sum(i['text'] == TEXT for i in first) == 5


def test_models_agree_when_the_checker_delivers_the_same_jobs_and_disagree_when_one_misses_a_job():
    odd = [i['item_id'] for i in ITEMS if i['text'] == TEXT]
    a = {'processed': [i['item_id'] for i in ITEMS], 'facts': [fact(i) for i in odd]}
    b_missing = {'processed': [i['item_id'] for i in ITEMS], 'facts': [fact(i) for i in odd[:-2]]}
    same = ev.compare(ITEMS, 'item_id', a, a, ('sonnet', 'haiku'))
    worse = ev.compare(ITEMS, 'item_id', a, b_missing, ('sonnet', 'haiku'))
    assert same['agreement_percent'] == 100.0 and same['jobs']['in_both'] == len(odd)
    assert worse['agree'] == 18 and worse['agreement_percent'] == 90.0 and worse['jobs'] == {'sonnet': 10, 'haiku': 8, 'in_both': 8}


def test_an_invented_value_is_rejected_by_the_checker_so_it_counts_as_a_miss_not_a_job():
    odd = [i['item_id'] for i in ITEMS if i['text'] == TEXT]
    a = {'processed': odd, 'facts': [fact(i) for i in odd]}
    b = {'processed': odd, 'facts': [fact(i, company='Gamma') for i in odd]}  # "Gamma" is not in the text
    report = ev.compare(ITEMS, 'item_id', a, b, ('sonnet', 'haiku'))
    assert report['rejected_facts']['haiku'] == len(odd) and report['jobs']['haiku'] == 0 and report['agreement_percent'] == 50.0


def test_the_command_line_writes_a_report_and_lists_disagreements(tmp_path, capsys):
    odd = [i['item_id'] for i in ITEMS if i['text'] == TEXT]
    candidates = write(tmp_path, 'c.json', {'candidates': ITEMS})
    a = write(tmp_path, 'a.json', {'processed': odd, 'facts': [fact(i) for i in odd]})
    b = write(tmp_path, 'b.json', {'processed': odd, 'facts': [fact(i) for i in odd[:-1]]})
    out = tmp_path.parent / (tmp_path.name + '_report.json')
    assert ev.main(['compare', '--candidates', candidates, '--a', a, '--b', b, '--output', str(out)]) == 0
    text = capsys.readouterr().out
    assert 'agreement_percent=95.0' in text and 'DISAGREE 19' in text
