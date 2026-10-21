"""The two-model reading comparison: sampling is deterministic and agreement is judged on what the checker delivers."""

import json

import pytest

from scripts import eval_reading as ev

TEXT = 'Acme is hiring a Senior Product Manager, AI (Remote US) for MBA students graduating in spring 2027. Salary $200,000 - $250,000.'
ITEMS = [{'item_id': str(n), 'url': f'https://x.com/a/status/{n}', 'created_at': '2026-10-15T12:00:00+00:00',
          'text': TEXT if n % 2 else 'Nothing relevant here.', 'links': []} for n in range(1, 21)]


def fact(item_id, title='Senior Product Manager, AI', company='Acme'):
    return {'item_id': item_id, 'title': title, 'company': company, 'location': 'Remote US', 'salary': '$200,000 - $250,000',
            'description_quote': TEXT.split(' Salary')[0], 'apply_url': ''}


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
    a = {'processed': [i['item_id'] for i in ITEMS], 'facts': [fact(i) for i in odd]}
    b = {'processed': [i['item_id'] for i in ITEMS], 'facts': [fact(i, company='Gamma') for i in odd]}  # "Gamma" is not in the text
    report = ev.compare(ITEMS, 'item_id', a, b, ('sonnet', 'haiku'))
    assert report['rejected_facts']['haiku'] == len(odd) and report['jobs']['haiku'] == 0 and report['agreement_percent'] == 50.0


def test_the_command_line_writes_a_report_and_lists_disagreements(tmp_path, capsys):
    odd = [i['item_id'] for i in ITEMS if i['text'] == TEXT]
    candidates = write(tmp_path, 'c.json', {'candidates': ITEMS})
    a = write(tmp_path, 'a.json', {'processed': [i['item_id'] for i in ITEMS], 'facts': [fact(i) for i in odd]})
    b = write(tmp_path, 'b.json', {'processed': [i['item_id'] for i in ITEMS], 'facts': [fact(i) for i in odd[:-1]]})
    out = tmp_path.parent / (tmp_path.name + '_report.json')
    assert ev.main(['compare', '--candidates', candidates, '--a', a, '--b', b, '--output', str(out)]) == 0
    text = capsys.readouterr().out
    assert 'agreement_percent=95.0' in text and 'DISAGREE 19' in text


def test_a_hacker_news_fact_with_no_apply_link_is_delivered_with_the_comment_link_as_its_fallback():
    items = [{'comment_id': str(n), 'story_id': '1', 'created_at': '2026-10-15T12:00:00+00:00', 'text': TEXT, 'links': []}
             for n in range(1, 4)]  # Hacker News comments have no `url`; the real pipeline falls back to their permalink
    facts = {'processed': [i['comment_id'] for i in items],
             'facts': [{**fact(i['comment_id']), 'comment_id': i['comment_id']} for i in items]}
    for row in facts['facts']:
        del row['item_id']
    report = ev.compare(items, 'comment_id', facts, facts, ('sonnet', 'haiku'))
    assert report['rejected_facts'] == {'sonnet': 0, 'haiku': 0} and report['jobs']['sonnet'] == 3


def test_the_fallback_link_is_chosen_by_id_field_and_a_missing_url_is_not_papered_over():
    assert ev.permalink_for('comment_id')({'comment_id': '5', 'url': 'https://elsewhere.example/x'}) == \
        'https://news.ycombinator.com/item?id=5'
    assert ev.permalink_for('item_id')({'item_id': '7', 'url': 'https://x.com/a/status/7'}) == 'https://x.com/a/status/7'
    with pytest.raises(KeyError):
        ev.permalink_for('item_id')({'item_id': '7'})  # the real pipeline drops such an item; the eval must not invent a link
