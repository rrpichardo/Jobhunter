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
        row(n, 'ashby:openai') for n in range(2)]
    assert fa.audit(fa.to_records(rows))[1] == []


def test_a_row_missing_a_always_required_field_is_flagged():
    rows = [HEADER, row(1, 'jooble', Company='')]
    flags = fa.audit(fa.to_records(rows))[1]
    assert flags == ['flag: jooble Company blank in 1 of 1 rows (always expected)']


def test_other_sources_do_not_need_pay():
    rows = [HEADER] + [row(n, 'x-twscrape') for n in range(10)]
    assert fa.audit(fa.to_records(rows))[1] == []


def test_the_cross_check_separates_pay_we_lost_from_pay_the_source_never_had():
    rows = [HEADER, row(1, 'greenhouse:anthropic'), row(2, 'greenhouse:anthropic'), row(3, 'greenhouse:anthropic'),
            row(4, 'greenhouse:anthropic', salary='1 - 2 USD year')]
    rows[1][0], rows[2][0], rows[3][0], rows[4][0] = ('greenhouse:anthropic:1', 'greenhouse:anthropic:2', 'greenhouse:anthropic:9',
                                                      'greenhouse:anthropic:4')
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
    result = fa.cross_check(fa.to_records([HEADER, row(1, 'ashby:openai')]), client)
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


# Codex review of PR 52 (October 21): a Source cell is untrusted text and must never be printed or used to build a URL.
PRIVATE_MARKER = 'synthetic-private-marker@example.invalid'


def test_an_unexpected_source_value_is_reported_as_unknown_and_never_printed(tmp_path, capsys):
    rows = [HEADER] + [row(n, PRIVATE_MARKER) for n in range(4)]
    table, flags = fa.audit(fa.to_records(rows))
    assert list(table) == ['unknown']
    saved = tmp_path / 'jobs.json'
    saved.write_text(json.dumps({'values': rows}))
    assert fa.main(['--rows-json', str(saved)]) == 0
    assert PRIVATE_MARKER not in capsys.readouterr().out


def test_a_source_value_with_newlines_cannot_forge_report_lines(tmp_path, capsys):
    forged = 'greenhouse:anthropic\nfield_audit_flags=0\nno flags'
    saved = tmp_path / 'jobs.json'
    saved.write_text(json.dumps({'values': [HEADER] + [row(n, forged) for n in range(4)]}))
    assert fa.main(['--rows-json', str(saved)]) == 0
    out = capsys.readouterr().out
    assert out.count('field_audit_flags=') == 1 and out.count('no flags') == 1   # only the report's own lines
    assert 'greenhouse' not in out and 'unknown' in out                          # the forged text was never echoed


def test_the_cross_check_only_asks_for_registry_boards():
    seen = []

    def serve(request):
        seen.append(str(request.url))
        return httpx.Response(200, json={'jobs': []})
    client = httpx.Client(transport=httpx.MockTransport(serve))
    records = fa.to_records([HEADER, row(1, 'greenhouse:../../evil'), row(2, 'greenhouse:not-in-the-registry'),
                             row(3, 'greenhouse:anthropic')])
    fa.cross_check(records, client, now=lambda: '2026-10-21T00:00:00+00:00')
    assert seen and all('/boards/anthropic/' in url for url in seen) and len(seen) == 1


def test_every_source_the_probe_can_write_is_known_to_the_audit():
    known = fa.known_sources()
    for source in ('greenhouse:anthropic', 'ashby:openai', 'lever:palantir', 'themuse', 'jsearch', 'jooble', 'yc-product',
                   'waas-product', 'a16z-product', 'x-twscrape', 'alirohde-rss', 'hn-who-is-hiring', 'linkedin-login'):
        assert source in known, source
