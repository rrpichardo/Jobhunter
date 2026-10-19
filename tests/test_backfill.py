"""Keep every match: posted dates, the 4-week window, and recoverable delivery batches."""

from datetime import datetime, timezone
import hashlib
import json

import httpx
import pytest

from jobhunter import postings as p
from scripts import sheets_sync
from scripts import source_probe as probe
from sheet_fakes import MemoryStore

STAMP = '2026-10-18T00:00:00+00:00'
CTX = {'source_id': 'src', 'captured_at': STAMP, 'board': 'acme', 'company': 'Acme', 'tag': 'other'}


@pytest.mark.parametrize('value,expected', [
    (1786469891368, '2026-08-11T17:38:11+00:00'),            # epoch milliseconds (Lever createdAt)
    ('1792364391', '2026-10-18T22:59:51+00:00'),             # epoch seconds as text (Himalayas pubDate)
    ('2026-10-14T20:33:44', '2026-10-14T20:33:44+00:00'),    # no zone: read as UTC
    ('2026-10-13T18:44:30Z', '2026-10-13T18:44:30+00:00'),
    ('2026-04-07T17:12:35.753+00:00', '2026-04-07T17:12:35+00:00'),
    ('2024-12-20T13:53:38-05:00', '2024-12-20T18:53:38+00:00'),
    ('Mon, 12 Oct 2026 09:00:00 +0000', '2026-10-12T09:00:00+00:00'),  # RSS
])
def test_parse_posted_normalizes_known_formats_to_utc(value, expected):
    assert p.parse_posted(value) == expected


@pytest.mark.parametrize('value', [None, '', '   ', 'yesterday', 'N/A', True, False, [], {}, 10 ** 30, -10 ** 30])
def test_parse_posted_never_guesses(value):
    assert p.parse_posted(value) == ''


def test_posting_rejects_an_unnormalized_posted_at():
    base = dict(job_id='a:1', source_id='a', company='Co', title='Product Manager', location='US', text='x',
                apply_url='https://example.com/1', captured_at=STAMP)
    assert p.Posting(**base, posted_at='2026-10-14T20:33:44+00:00').posted_at.startswith('2026-10-14')
    for bad in ('2026-10-14', 'yesterday', '2026-10-14T20:33:44'):
        with pytest.raises(ValueError):
            p.Posting(**base, posted_at=bad)


def test_every_parser_reads_the_date_field_its_source_actually_uses():
    gh = {'jobs': [{'id': 1, 'title': 'Product Manager', 'location': {'name': 'US'}, 'content': 'x',
                    'absolute_url': 'https://boards.greenhouse.io/acme/jobs/1', 'updated_at': '2026-10-01T00:00:00-04:00',
                    'first_published': '2026-09-30T10:00:00-04:00'}]}
    assert p.parse_greenhouse(gh, CTX)[0][0].posted_at == '2026-09-30T14:00:00+00:00'  # not updated_at
    lever = [{'id': 'a', 'text': 'Product Manager', 'categories': {}, 'descriptionPlain': 'x',
              'hostedUrl': 'https://jobs.lever.co/acme/a', 'createdAt': 1786469891368}]
    assert p.parse_lever(lever, CTX)[0][0].posted_at == '2026-08-11T17:38:11+00:00'
    ashby = {'jobs': [{'id': 'a', 'title': 'Product Manager', 'location': 'US', 'descriptionPlain': 'x',
                       'jobUrl': 'https://jobs.ashbyhq.com/acme/a', 'publishedAt': '2026-04-07T17:12:35.753+00:00'}]}
    assert p.parse_ashby(ashby, CTX)[0][0].posted_at == '2026-04-07T17:12:35+00:00'
    remotive = {'jobs': [{'id': 1, 'title': 'Product Manager', 'company_name': 'Co', 'url': 'https://remotive.com/1',
                          'description': 'x', 'publication_date': '2026-10-14T20:33:44'}]}
    assert p.parse_remotive(remotive, CTX)[0][0].posted_at == '2026-10-14T20:33:44+00:00'
    remoteok = [{'legal': 'x'}, {'id': 1, 'position': 'Product Manager', 'company': 'Co', 'url': 'https://remoteok.com/1',
                                 'description': 'x', 'date': '2026-10-17T08:00:50+00:00', 'epoch': '1792224050'}]
    assert p.parse_remoteok(remoteok, CTX)[0][0].posted_at == '2026-10-17T08:00:50+00:00'
    himalayas = {'jobs': [{'guid': 'g1', 'title': 'Product Manager', 'companyName': 'Co', 'description': 'x',
                           'applicationLink': 'https://himalayas.app/1', 'pubDate': '1792364391'}]}
    assert p.parse_himalayas(himalayas, CTX)[0][0].posted_at == '2026-10-18T22:59:51+00:00'
    jobicy = {'jobs': [{'id': 1, 'jobTitle': 'Product Manager', 'companyName': 'Co', 'jobDescription': 'x',
                        'url': 'https://jobicy.com/1', 'pubDate': '2026-10-18T16:18:50+00:00'}]}
    assert p.parse_jobicy(jobicy, CTX)[0][0].posted_at == '2026-10-18T16:18:50+00:00'
    muse = {'results': [{'id': 1, 'name': 'Product Manager', 'company': {'name': 'Co'}, 'locations': [],
                         'contents': 'x', 'refs': {'landing_page': 'https://themuse.com/1'},
                         'publication_date': '2026-10-13T18:44:30Z'}]}
    assert p.parse_themuse(muse, CTX)[0][0].posted_at == '2026-10-13T18:44:30+00:00'
    rss = ('<rss version="2.0"><channel><item><title>Co: Product Manager</title><link>https://wwr.test/1</link>'
           '<description>x</description><pubDate>Mon, 12 Oct 2026 09:00:00 +0000</pubDate></item></channel></rss>')
    assert p.parse_wwr_rss(rss, CTX)[0][0].posted_at == '2026-10-12T09:00:00+00:00'


def test_a_source_without_a_date_leaves_posted_at_empty_and_the_row_says_so():
    lever = [{'id': 'a', 'text': 'Product Manager', 'categories': {}, 'descriptionPlain': 'x',
              'hostedUrl': 'https://jobs.lever.co/acme/a'}]
    posting = p.parse_lever(lever, CTX)[0][0]
    assert posting.posted_at == ''
    assert 'Posted: not provided by source' in p.to_row(posting)['More details']
    dated = p.parse_lever([{**lever[0], 'createdAt': 1786469891368}], CTX)[0][0]
    assert 'Posted: 2026-08-11 (source metadata)' in p.to_row(dated)['More details']


def lever_registry_entry():
    return {'id': 'lever:acme', 'kind': 'lever', 'board': 'acme', 'company': 'Acme', 'tag': 'other',
            'url': 'https://test.example/jobs'}


def lever_job(number, created):
    job = {'id': f'j{number}', 'text': 'Product Manager', 'categories': {'location': 'United States'},
           'descriptionPlain': 'Build products.', 'hostedUrl': f'https://jobs.lever.co/acme/j{number}'}
    if created is not None:
        job['createdAt'] = created
    return job


def test_lookback_keeps_recent_and_undated_and_counts_what_it_set_aside():
    ms = lambda text: int(datetime.fromisoformat(text).replace(tzinfo=timezone.utc).timestamp() * 1000)
    data = [lever_job(1, ms('2026-10-10T00:00:00')),   # 8 days old: inside
            lever_job(2, ms('2026-08-01T00:00:00')),   # 78 days old: outside
            lever_job(3, None)]                        # no date: kept, never dropped on missing data
    with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=data))) as client:
        record, jobs, note = probe.probe_source(client, lever_registry_entry(), STAMP, lookback_days=28)
        _, unwindowed, plain_note = probe.probe_source(client, lever_registry_entry(), STAMP)
    assert sorted(job.job_id for job in jobs) == ['lever:acme:j1', 'lever:acme:j3']
    assert 'outside_window=1' in note and 'date_unknown=1' in note
    assert record['selected_for_m0'] == 2 and record['jobs_fetched'] == 3
    assert len(unwindowed) == 3 and 'outside_window' not in plain_note  # no window means no filtering


def test_the_window_edge_is_inclusive_and_future_dates_are_kept():
    now = datetime.fromisoformat(STAMP)
    base = dict(job_id='a:1', source_id='a', company='Co', title='Product Manager', location='US', text='x',
                apply_url='https://example.com/1', captured_at=STAMP)
    edge = p.Posting(**base, posted_at='2026-09-20T00:00:00+00:00')      # exactly 28 days before STAMP
    older = p.Posting(**base, posted_at='2026-09-19T23:59:59+00:00')
    future = p.Posting(**base, posted_at='2026-10-25T00:00:00+00:00')
    assert p.within_lookback(edge, now, 28) and not p.within_lookback(older, now, 28)
    assert p.within_lookback(future, now, 28)


def test_an_unverified_listing_date_never_hides_a_job_the_detail_page_dates_as_recent():
    from html import escape
    jobs = [{'id': 1, 'title': 'Product Manager', 'url': '/companies/acme/jobs/1', 'location': 'United States',
             'companyName': 'Acme', 'createdAt': '2026-10-10T00:00:00Z'},
            {'id': 2, 'title': 'Product Manager', 'url': '/companies/acme/jobs/2', 'location': 'United States',
             'companyName': 'Acme', 'createdAt': '2026-07-01T00:00:00Z'}]
    listing = '<div data-page="' + escape(json.dumps({'props': {'jobPostings': jobs}}), quote=True) + '"></div>'
    page = '<script type="application/ld+json">{"@type":"JobPosting","description":"Build.","datePosted":"2026-10-10"}</script>'
    seen = []

    def serve(request):
        seen.append(str(request.url))
        return httpx.Response(200, text=listing if 'jobs/role' in str(request.url) else page)
    with httpx.Client(transport=httpx.MockTransport(serve)) as client:
        _, found, note = probe.probe_source(client, {'id': 'yc-product', 'kind': 'yc',
            'url': 'https://www.ycombinator.com/jobs/role/product-manager'}, STAMP, lookback_days=28)
    # The listing says job 2 is old, but the listing date is unverified: both pages are opened and the
    # authoritative datePosted on each page decides.
    assert sorted(job.job_id for job in found) == ['yc-product:1', 'yc-product:2']
    assert all(job.posted_at == '2026-10-10T00:00:00+00:00' for job in found)
    assert len(seen) == 3 and 'outside_window=0' in note
    old_page = page.replace('2026-10-10', '2026-07-01')
    seen.clear()
    with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(
            200, text=listing if 'jobs/role' in str(r.url) else old_page))) as client:
        _, found, note = probe.probe_source(client, {'id': 'yc-product', 'kind': 'yc',
            'url': 'https://www.ycombinator.com/jobs/role/product-manager'}, STAMP, lookback_days=28)
    assert found == [] and 'outside_window=2' in note  # a page-dated old job is excluded after its page is read


@pytest.mark.parametrize('days,bucket', [(1, 'today'), (2, '3days'), (3, '3days'), (7, 'week'), (8, 'month'), (28, 'month')])
def test_jsearch_uses_the_smallest_date_bucket_that_covers_the_window(days, bucket):
    assert probe.jsearch_date_posted(days) == bucket
    entry = {'kind': 'jsearch', 'url': 'https://jsearch.example/search', 'env': ['JSEARCH_API_KEY'],
             'params': {'query': 'pm', 'date_posted': 'week'}}
    _, request = probe.keyed_request(entry, {'JSEARCH_API_KEY': 'k'}, days)
    assert request['params']['date_posted'] == bucket and entry['params']['date_posted'] == 'week'


def test_the_cli_rejects_a_nonsense_window(tmp_path, capsys):
    out = tmp_path.parent / (tmp_path.name + '_x.json')
    assert probe.main(['--output', str(out), '--lookback-days', '0']) == 2
    assert 'invalid_lookback_days' in capsys.readouterr().out


# ---- delivery in recoverable batches -------------------------------------------------------------

@pytest.fixture(autouse=True)
def no_real_pauses(monkeypatch):
    monkeypatch.setattr(sheets_sync.time, 'sleep', lambda seconds: None)


def artifact(tmp_path, count, *, status='OK', selected=None):
    rows = [p.to_row(p.Posting(f'bulk:{i:04d}', 'bulk', 'Co', f'Product Manager {i}', 'United States',
                               'Build products.', f'https://example.com/jobs/{i}', STAMP, posted_at=STAMP))
            for i in range(count)]
    payload = {'schema_version': 2, 'jobs': rows, 'probe': {'notes': {}},
               'sources': [probe.record('bulk', status, STAMP, error='' if status == 'OK' else 'http_500',
                                        listed=count, valid=count, rejected=0, candidates=count,
                                        selected=count if selected is None else selected)],
               'extraction': {'selected': count, 'validated': count, 'status': 'complete'}}
    out = tmp_path.parent / (tmp_path.name + '_bulk.json')
    out.write_text(json.dumps(payload))
    return out


def test_a_run_larger_than_one_batch_delivers_every_job_in_numbered_batches(tmp_path, capsys):
    out, backend = artifact(tmp_path, 320), MemoryStore()
    assert sheets_sync.main(['--input', str(out), '--run-id', 'big'], store=backend) == 0
    assert 'batches=3' in capsys.readouterr().out
    ids = [row[0] for row in backend.tables['Jobs'][1:]]
    assert len(ids) == 320 and len(set(ids)) == 320
    assert [row[0] for row in backend.tables['Run Log'][1:]] == ['big-b001', 'big-b002', 'big-b003']
    assert [row[3] for row in backend.tables['Run Log'][1:]] == [150, 150, 20]
    assert len(backend.tables['Sources']) == 2  # one source row with the full total, not one per batch
    assert backend.tables['Sources'][1][backend.tables['Sources'][0].index('Selected')] == 320


def test_batches_are_paced_so_a_large_backfill_stays_under_the_sheets_quota(tmp_path, monkeypatch):
    pauses = []
    monkeypatch.setattr(sheets_sync.time, 'sleep', pauses.append)
    out, backend = artifact(tmp_path, 320), MemoryStore()
    assert sheets_sync.main(['--input', str(out), '--run-id', 'paced'], store=backend) == 0
    assert pauses == [sheets_sync.BATCH_PAUSE_SECONDS] * 2  # between three batches, never before the first


def test_a_run_id_that_just_fits_with_the_batch_suffix_is_accepted(tmp_path):
    out, backend = artifact(tmp_path, 320), MemoryStore()
    assert sheets_sync.main(['--input', str(out), '--run-id', 'x' * 75], store=backend) == 0
    assert backend.tables['Run Log'][1][0] == 'x' * 75 + '-b001'


def test_a_single_batch_keeps_the_plain_run_id(tmp_path):
    out, backend = artifact(tmp_path, 40), MemoryStore()
    assert sheets_sync.main(['--input', str(out), '--run-id', 'small'], store=backend) == 0
    assert [row[0] for row in backend.tables['Run Log'][1:]] == ['small']


def test_a_rerun_after_a_mid_run_failure_finishes_without_duplicates_and_keeps_user_notes(tmp_path, monkeypatch):
    out, backend = artifact(tmp_path, 320), MemoryStore()
    real, calls = sheets_sync.sync_jobs, []

    def flaky(*args, **kwargs):
        calls.append(kwargs['run_id'])
        if len(calls) == 2:
            raise ValueError('sheet_request_failed')
        return real(*args, **kwargs)
    monkeypatch.setattr(sheets_sync, 'sync_jobs', flaky)
    assert sheets_sync.main(['--input', str(out), '--run-id', 'big'], store=backend) == 2
    assert len(backend.tables['Jobs']) == 151  # batch one landed, nothing was dropped or half-written
    headers = backend.tables['Jobs'][0]
    backend.tables['Jobs'][1][headers.index('Notes')] = 'my note'
    backend.tables['Jobs'][1][headers.index('Status')] = 'Applied'
    monkeypatch.setattr(sheets_sync, 'sync_jobs', real)
    assert sheets_sync.main(['--input', str(out), '--run-id', 'big'], store=backend) == 0
    ids = [row[0] for row in backend.tables['Jobs'][1:]]
    assert len(ids) == 320 and len(set(ids)) == 320
    assert backend.tables['Jobs'][1][headers.index('Notes')] == 'my note'
    assert backend.tables['Jobs'][1][headers.index('Status')] == 'Applied'
    assert [row[0] for row in backend.tables['Run Log'][1:]] == ['big-b001', 'big-b002', 'big-b003']


def test_a_failed_source_may_deliver_its_partial_jobs_across_batches(tmp_path):
    out, backend = artifact(tmp_path, 200, status='failed'), MemoryStore()
    assert sheets_sync.main(['--input', str(out), '--run-id', 'part'], store=backend) == 0
    assert len(backend.tables['Jobs']) == 201


def test_a_job_from_a_source_that_did_not_record_it_is_still_refused(tmp_path):
    out, backend = artifact(tmp_path, 200, status='failed', selected=100), MemoryStore()
    assert sheets_sync.main(['--input', str(out), '--run-id', 'bad'], store=backend) == 2
    assert backend.tables == {}  # rejected before any Sheet access


def test_a_run_id_too_long_for_batch_suffixes_is_rejected_before_any_write(tmp_path):
    out, backend = artifact(tmp_path, 320), MemoryStore()
    assert sheets_sync.main(['--input', str(out), '--run-id', 'x' * 76], store=backend) == 2
    assert backend.tables == {}


def test_a_backfill_larger_than_the_default_artifact_limit_still_reaches_batching(tmp_path, capsys):
    out, backend = artifact(tmp_path, 8500), MemoryStore()
    assert out.stat().st_size > 5 * 1024 * 1024  # the old shared limit rejected this before any Sheet access
    digest = hashlib.sha256(out.read_bytes()).hexdigest()  # what source_probe prints as probe_sha256
    assert sheets_sync.main(['--input', str(out), '--input-sha256', digest, '--run-id', 'huge'], store=backend) == 0
    assert 'batches=57' in capsys.readouterr().out
    assert len({row[0] for row in backend.tables['Jobs'][1:]}) == 8500


def test_the_producer_refuses_a_file_the_writer_could_not_read(tmp_path):
    from jobhunter.artifacts import SYNC_MAX_BYTES, write_artifact
    target = tmp_path.parent / (tmp_path.name + '_toobig.json')
    with pytest.raises(ValueError, match='artifact_too_large'):
        write_artifact(target, {'text': 'x' * (SYNC_MAX_BYTES + 1)}, max_bytes=SYNC_MAX_BYTES)
    assert not target.exists()  # nothing half-published


def test_the_larger_limit_is_only_for_an_input_proven_by_its_digest(tmp_path, capsys):
    out, backend = artifact(tmp_path, 8500), MemoryStore()
    assert sheets_sync.main(['--input', str(out), '--run-id', 'nodigest'], store=backend) == 2
    assert 'artifact_too_large' in capsys.readouterr().out and backend.tables == {}
    assert sheets_sync.main(['--input', str(out), '--input-sha256', '0' * 64, '--run-id', 'wrong'], store=backend) == 2
    assert 'artifact_digest_mismatch' in capsys.readouterr().out and backend.tables == {}


def test_an_oversized_schema_one_extraction_file_stays_capped_even_with_a_digest(tmp_path, capsys):
    big = tmp_path.parent / (tmp_path.name + '_ext.json')
    big.write_text(json.dumps({'schema_version': 1, 'source': {}, 'jobs': [], 'pad': 'x' * (6 * 1024 * 1024)}))
    backend = MemoryStore()
    # no digest supplied: the default limit applies and nothing past 5 MiB is read or parsed
    assert sheets_sync.main(['--input', str(big), '--run-id', 'ext'], store=backend) == 2
    assert 'artifact_too_large' in capsys.readouterr().out and backend.tables == {}
