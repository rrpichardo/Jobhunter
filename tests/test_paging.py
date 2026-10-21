"""The Muse and Jobicy page; a failed later page keeps what was read and says why it stopped."""

import json

import httpx
import pytest

from scripts import source_probe as probe

STAMP = '2026-10-18T12:00:00+00:00'


def muse_job(number, date='2026-10-10T00:00:00Z'):
    return {'id': number, 'name': 'Product Manager', 'company': {'name': f'Co{number}'},
            'locations': [{'name': 'Remote'}], 'contents': 'Build. This role is open to MBA students graduating in spring 2027.', 'publication_date': date,
            'refs': {'landing_page': f'https://www.themuse.com/jobs/{number}'}}


MUSE = {'id': 'themuse', 'kind': 'themuse',
        'url': 'https://www.themuse.com/api/public/jobs?category=Product%20Management&page=0'}


def muse_client(pages, seen, fail_page=None):
    def serve(request):
        number = int(request.url.params['page'])
        seen.append(number)
        if number == fail_page:
            return httpx.Response(500)
        return httpx.Response(200, json={'page_count': len(pages), 'results': pages[number]})
    return httpx.Client(transport=httpx.MockTransport(serve))


def test_muse_is_read_from_page_zero_through_the_last_page():
    seen = []
    pages = [[muse_job(1), muse_job(2)], [muse_job(3)], [muse_job(4)]]
    with muse_client(pages, seen) as client:
        record, jobs, note = probe.probe_source(client, MUSE, STAMP, sleep=lambda s: None)
    assert seen == [0, 1, 2] and sorted(j.job_id for j in jobs) == [f'themuse:{n}' for n in (1, 2, 3, 4)]
    assert 'pages_fetched=3' in note and record['coverage'] == 'complete-response' and record['attempts'] == 3


def test_muse_is_not_date_ordered_so_an_old_job_on_an_early_page_does_not_stop_paging():
    seen = []
    pages = [[muse_job(1, '2026-03-01T00:00:00Z')], [muse_job(2)]]
    with muse_client(pages, seen) as client:
        _, jobs, note = probe.probe_source(client, MUSE, STAMP, lookback_days=28, sleep=lambda s: None)
    assert seen == [0, 1] and [j.job_id for j in jobs] == ['themuse:2'] and 'outside_window=1' in note


def test_a_failed_later_page_keeps_earlier_pages_and_reports_the_stop():
    seen = []
    pages = [[muse_job(1)], [muse_job(2)], [muse_job(3)]]
    with muse_client(pages, seen, fail_page=1) as client:
        record, jobs, note = probe.probe_source(client, MUSE, STAMP, sleep=lambda s: None)
    assert [j.job_id for j in jobs] == ['themuse:1'] and 'paging_stopped=http_500' in note
    # the failure is durable evidence in the source record, not only a probe note; page-one jobs are kept
    assert record['status'] == 'failed' and record['error'] == 'http_500' and record['http_status'] == 500
    assert record['coverage'] == 'partial-response' and record['attempts'] == 2 and record['selected_for_m0'] == 1


def test_a_later_page_failure_record_and_its_partial_jobs_are_accepted_by_the_writer_validation():
    from jobhunter.sheets import prepare_payload
    seen = []
    with muse_client([[muse_job(1)], [muse_job(2)]], seen, fail_page=1) as client:
        record, jobs, _ = probe.probe_source(client, MUSE, STAMP, sleep=lambda s: None)
    rows = [probe.to_row(j) for j in jobs]
    prepare_payload(rows, [record])  # a failed source may carry the partial jobs it really read


def test_a_blocked_later_page_is_recorded_as_blocked():
    def serve(request):
        if request.url.params['page'] == '0':
            return httpx.Response(200, json={'page_count': 2, 'results': [muse_job(1)]})
        return httpx.Response(429)
    with httpx.Client(transport=httpx.MockTransport(serve)) as client:
        record, jobs, _ = probe.probe_source(client, MUSE, STAMP, sleep=lambda s: None)
    assert record['status'] == 'blocked' and record['error'] == 'http_429' and len(jobs) == 1


def test_a_malformed_later_muse_page_is_a_fixed_error_that_keeps_earlier_jobs():
    def serve(request):
        if request.url.params['page'] == '0':
            return httpx.Response(200, json={'page_count': 2, 'results': [muse_job(1)]})
        return httpx.Response(200, json={'page_count': 2, 'results': 'not a list'})
    with httpx.Client(transport=httpx.MockTransport(serve)) as client:
        record, jobs, _ = probe.probe_source(client, MUSE, STAMP, sleep=lambda s: None)
    assert record['status'] == 'failed' and record['error'] == 'invalid_json' and len(jobs) == 1


def test_the_page_safety_stop_limits_pages_and_says_so():
    seen = []
    pages = [[muse_job(n)] for n in range(1, 8)]
    with muse_client(pages, seen) as client:
        record, jobs, note = probe.probe_source(client, MUSE, STAMP, sleep=lambda s: None, page_stop=3)
    assert seen == [0, 1, 2] and len(jobs) == 3 and 'paging_stopped=page_safety_stop' in note
    assert record['coverage'] == 'partial-response'


JOBICY = {'id': 'jobicy', 'kind': 'jobicy', 'url': 'https://jobicy.com/api/v2/remote-jobs?count=50&tag=product'}


def jobicy_job(number, date):
    return {'id': number, 'jobTitle': 'Product Manager', 'companyName': f'Co{number}', 'jobDescription': 'Build. This role is open to MBA students graduating in spring 2027.',
            'url': f'https://jobicy.com/jobs/{number}', 'pubDate': date, 'jobGeo': 'USA'}


def jobicy_client(pages, seen):
    def serve(request):
        cursor = request.url.params.get('cursor')
        seen.append(cursor)
        number = 0 if cursor is None else int(cursor.split('-')[1])
        more = number + 1 < len(pages)
        return httpx.Response(200, json={'jobs': pages[number], 'hasMore': more,
                                         'nextCursor': f'page-{number + 1}' if more else None})
    return httpx.Client(transport=httpx.MockTransport(serve))


def test_jobicy_follows_the_cursor_until_a_page_reaches_the_window_edge():
    seen = []
    pages = [[jobicy_job(1, '2026-10-17T00:00:00+00:00')], [jobicy_job(2, '2026-10-01T00:00:00+00:00')],
             [jobicy_job(3, '2026-08-01T00:00:00+00:00')], [jobicy_job(4, '2026-07-01T00:00:00+00:00')]]
    with jobicy_client(pages, seen) as client:
        record, jobs, note = probe.probe_source(client, JOBICY, STAMP, lookback_days=28, sleep=lambda s: None)
    assert seen == [None, 'page-1', 'page-2']  # page 3 is never requested: page 2 ended behind the window
    assert sorted(j.job_id for j in jobs) == ['jobicy:1', 'jobicy:2'] and 'outside_window=1' in note
    assert 'pages_fetched=3' in note and record['coverage'] == 'complete-response'


def test_jobicy_without_a_window_pages_until_the_source_has_no_more():
    seen = []
    pages = [[jobicy_job(n, '2026-10-17T00:00:00+00:00')] for n in range(1, 4)]
    with jobicy_client(pages, seen) as client:
        _, jobs, note = probe.probe_source(client, JOBICY, STAMP, sleep=lambda s: None)
    assert len(jobs) == 3 and 'pages_fetched=3' in note


def test_a_hostile_cursor_is_never_followed():
    def serve(request):
        return httpx.Response(200, json={'jobs': [jobicy_job(1, '2026-10-17T00:00:00+00:00')], 'hasMore': True,
                                         'nextCursor': 'x&redirect=https://evil.example'})
    with httpx.Client(transport=httpx.MockTransport(serve)) as client:
        record, jobs, note = probe.probe_source(client, JOBICY, STAMP, sleep=lambda s: None)
    assert len(jobs) == 1 and 'paging_stopped=invalid_cursor' in note
    assert record['status'] == 'failed' and record['error'] == 'invalid_board_response'


def test_a_null_trailing_job_does_not_abort_the_run_and_readable_jobs_survive():
    def serve(request):
        return httpx.Response(200, json={'jobs': [jobicy_job(1, '2026-10-17T00:00:00+00:00'), None],
                                         'hasMore': True, 'nextCursor': 'page-1'}
                              if request.url.params.get('cursor') is None else
                              {'jobs': [jobicy_job(2, '2026-10-16T00:00:00+00:00')], 'hasMore': False, 'nextCursor': None})
    with httpx.Client(transport=httpx.MockTransport(serve)) as client:
        record, jobs, _ = probe.probe_source(client, JOBICY, STAMP, lookback_days=28, sleep=lambda s: None)
    assert sorted(j.job_id for j in jobs) == ['jobicy:1', 'jobicy:2']  # the null item is quarantined by the parser
    assert record['rejected_items'] == 1


def test_a_malformed_jobicy_page_is_contained_per_source():
    def serve(request):
        if request.url.params.get('cursor') is None:
            return httpx.Response(200, json={'jobs': [jobicy_job(1, '2026-10-17T00:00:00+00:00')],
                                             'hasMore': True, 'nextCursor': 'page-1'})
        return httpx.Response(200, json={'jobs': 'oops', 'hasMore': True, 'nextCursor': 'page-2'})
    with httpx.Client(transport=httpx.MockTransport(serve)) as client:
        record, jobs, _ = probe.probe_source(client, JOBICY, STAMP, sleep=lambda s: None)
    assert [j.job_id for j in jobs] == ['jobicy:1'] and record['error'] == 'invalid_json'


def test_the_cli_page_safety_stop_flag_is_validated_and_printed(tmp_path, capsys):
    out = tmp_path.parent / (tmp_path.name + '_pg.json')
    assert probe.main(['--output', str(out), '--page-safety-stop', '0']) == 2
    assert 'invalid_safety_stop' in capsys.readouterr().out and not out.exists()


def test_the_registry_starts_the_muse_at_page_zero():
    import yaml
    config = yaml.safe_load(open('sources/v0_sources.yaml', encoding='utf-8'))
    muse = next(e for e in config['aggregators'] if e['id'] == 'themuse')
    assert 'page=0' in muse['url']


@pytest.mark.parametrize('failure,code', [(httpx.ReadTimeout('slow'), 'timeout'), (httpx.ConnectError('down'), 'transport_error')])
def test_a_later_page_that_never_answers_records_no_http_status(failure, code):
    def serve(request):
        if request.url.params['page'] == '0':
            return httpx.Response(200, json={'page_count': 2, 'results': [muse_job(1)]})
        raise failure
    with httpx.Client(transport=httpx.MockTransport(serve)) as client:
        record, jobs, _ = probe.probe_source(client, MUSE, STAMP, sleep=lambda s: None)
    assert record['status'] == 'failed' and record['error'] == code and record['http_status'] is None
    assert len(jobs) == 1
