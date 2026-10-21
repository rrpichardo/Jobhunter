"""The blank-cell audit: flags a source that fills a column far less than it should, and checks the live board."""
import json

import httpx

from scripts import field_audit as fa

HEADER = ['Job ID', 'Date found', 'Job title', 'Company', 'Salary', 'Location', 'Brief description', 'Apply link', 'Source']


def row(n, source, salary='', location='San Francisco, CA', **changes):
    values = {'Job ID': f'{source}:{n}', 'Date found': '2026-10-19', 'Job title': 'Product Manager', 'Company': 'Acme',
              'Salary': salary, 'Location': location, 'Brief description': 'text', 'Apply link': 'https://x.example/1',
              'Source': source} | changes
    return [values[column] for column in HEADER]


def test_a_greenhouse_source_with_no_pay_in_california_is_flagged_twice_over():
    rows = [HEADER] + [row(n, 'greenhouse:anthropic') for n in range(5)]
    table, flags = fa.audit(fa.to_records(rows))
    assert table['greenhouse']['rows'] == 5 and table['greenhouse']['Salary'] == 0
    assert any('greenhouse Salary filled 0/5' in flag for flag in flags)
    assert any('CA/NY/CO/WA' in flag for flag in flags)


def test_a_healthy_source_and_a_source_with_too_few_rows_raise_no_flag():
    rows = [HEADER] + [row(n, 'greenhouse:anthropic', salary='305,000 - 385,000 USD year') for n in range(4)] + [
        row(n, 'ashby:x') for n in range(2)]
    assert fa.audit(fa.to_records(rows))[1] == []


def test_a_row_missing_a_always_required_field_is_flagged():
    rows = [HEADER, row(1, 'jooble', Company='')]
    flags = fa.audit(fa.to_records(rows))[1]
    assert flags == ['flag: jooble Company blank in 1 of 1 rows (always expected)']


def test_other_sources_do_not_need_pay():
    rows = [HEADER] + [row(n, 'x-twscrape') for n in range(10)]
    assert fa.audit(fa.to_records(rows))[1] == []


def test_the_cross_check_separates_pay_we_lost_from_pay_the_source_never_had():
    rows = [HEADER, row(1, 'greenhouse:acme'), row(2, 'greenhouse:acme'), row(3, 'greenhouse:acme'),
            row(4, 'greenhouse:acme', salary='1 - 2 USD year')]
    rows[1][0], rows[2][0], rows[3][0], rows[4][0] = ('greenhouse:acme:1', 'greenhouse:acme:2', 'greenhouse:acme:9',
                                                      'greenhouse:acme:4')
    live = {'jobs': [
        {'id': 1, 'title': 'Product Manager', 'location': {'name': 'SF'}, 'content': 'text', 'absolute_url': 'https://x.example/1',
         'pay_input_ranges': [{'min_cents': 15000000, 'max_cents': 20000000, 'currency_type': 'USD', 'title': 'Annual Salary:'}]},
        {'id': 2, 'title': 'Product Manager', 'location': {'name': 'SF'}, 'content': 'text', 'absolute_url': 'https://x.example/2',
         'pay_input_ranges': []},
        {'id': 4, 'title': 'Product Manager', 'location': {'name': 'SF'}, 'content': 'text', 'absolute_url': 'https://x.example/4'}]}
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=live)))
    result = fa.cross_check(fa.to_records(rows), client, now=lambda: '2026-10-21T00:00:00+00:00')
    assert (result['has_pay_we_left_blank'], result['source_also_blank'], result['no_longer_listed'],
            result['filled_already']) == (1, 1, 1, 1)


def test_an_unreadable_board_is_counted_not_hidden():
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(503)))
    result = fa.cross_check(fa.to_records([HEADER, row(1, 'ashby:acme')]), client)
    assert result['board_unreadable'] == 1


def test_the_command_reads_a_saved_sheet_reply_and_prints_only_counts_and_fixed_words(tmp_path, capsys):
    saved = tmp_path / 'jobs.json'
    saved.write_text(json.dumps({'values': [HEADER] + [row(n, 'greenhouse:anthropic') for n in range(5)]}))
    assert fa.main(['--rows-json', str(saved)]) == 0
    out = capsys.readouterr().out
    assert 'field_audit_flags=2' in out and 'Acme' not in out and 'x.example' not in out


def test_a_failure_prints_a_fixed_word(tmp_path, capsys):
    assert fa.main(['--rows-json', str(tmp_path / 'missing.json')]) == 2
    assert capsys.readouterr().out.strip() == 'field_audit_failed: FileNotFoundError'
