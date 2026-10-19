"""Detail-page sources skip jobs already in the Sheet, so a big source is not reopened every day."""

from html import escape
import json

import httpx
import pytest
import yaml

from jobhunter.sheet_records import JOB_HEADERS
from scripts import known_ids
from scripts import source_probe as probe
from sheet_fakes import MemoryStore

JOBS = [{'id': i, 'title': 'Product Manager', 'url': f'/companies/acme/jobs/{i}', 'location': 'United States',
         'companyName': 'Acme'} for i in range(1, 5)]
LISTING = '<div data-page="' + escape(json.dumps({'props': {'jobPostings': JOBS}}), quote=True) + '"></div>'
PAGE = '<script type="application/ld+json">{"@type":"JobPosting","description":"Build things."}</script>'
YC = {'id': 'yc-product', 'kind': 'yc', 'url': 'https://www.ycombinator.com/jobs/role/product-manager'}


def probe_with(known, seen):
    def serve(request):
        seen.append(str(request.url))
        return httpx.Response(200, text=LISTING if 'jobs/role' in str(request.url) else PAGE)
    with httpx.Client(transport=httpx.MockTransport(serve)) as client:
        return probe.probe_source(client, YC, '2026-10-18T12:00:00+00:00', known_ids=known)


def test_pages_for_jobs_already_delivered_are_not_opened():
    seen = []
    record, jobs, note = probe_with(frozenset({'yc-product:1', 'yc-product:3'}), seen)
    assert sorted(j.job_id for j in jobs) == ['yc-product:2', 'yc-product:4']
    assert len(seen) == 3 and 'already_delivered=2' in note  # the listing plus two new pages
    assert record['status'] == 'OK'


def test_with_everything_already_delivered_only_the_listing_is_read_and_the_source_is_zero_new():
    seen = []
    record, jobs, note = probe_with(frozenset(f'yc-product:{i}' for i in range(1, 5)), seen)
    assert jobs == [] and len(seen) == 1 and record['status'] == 'OK-zero-jobs' and 'already_delivered=4' in note


def test_without_a_known_list_every_page_is_opened_and_no_note_is_added():
    seen = []
    _, jobs, note = probe_with(frozenset(), seen)
    assert len(jobs) == 4 and len(seen) == 5 and 'already_delivered' not in note


def sheet_with(ids):
    store = MemoryStore()
    store.ensure_tab('Jobs', JOB_HEADERS)
    for number, job_id in enumerate(ids, 2):
        row = [''] * len(JOB_HEADERS)
        row[0] = job_id
        store.tables['Jobs'].append(row)
    return store


def test_known_ids_cli_lists_only_the_job_id_column_and_writes_nothing_to_the_sheet(tmp_path, capsys):
    store = sheet_with(['yc-product:2', 'greenhouse:acme:9'])
    store.tables['Jobs'][1][JOB_HEADERS.index('Notes')] = 'private note'
    out = tmp_path.parent / (tmp_path.name + '_known.json')
    assert known_ids.main(['--output', str(out)], store=store) == 0
    assert 'known_job_ids=2' in capsys.readouterr().out
    assert json.loads(out.read_text()) == {'schema_version': 1, 'job_ids': ['greenhouse:acme:9', 'yc-product:2']}
    assert 'private note' not in out.read_text() and store.writes == [] and store.owner is None


def test_known_ids_cli_fails_on_an_ambiguous_jobs_tab_without_writing_a_file(tmp_path, capsys):
    store = sheet_with(['a:1', 'a:1'])
    out = tmp_path.parent / (tmp_path.name + '_dup.json')
    assert known_ids.main(['--output', str(out)], store=store) == 2
    assert 'duplicate_existing_id' in capsys.readouterr().out and not out.exists()


def run_cli(tmp_path, capsys, extra):
    config = tmp_path / 'registry.yaml'
    config.write_text(yaml.safe_dump({'boards': {}, 'needs_setup': [], 'detail_sources': [YC]}))
    out = tmp_path.parent / (tmp_path.name + '_pr.json')
    client = httpx.Client(transport=httpx.MockTransport(
        lambda r: httpx.Response(200, text=LISTING if 'jobs/role' in str(r.url) else PAGE)))
    code = probe.main(['--config', str(config), '--output', str(out), '--delay', '0', *extra],
                      client=client, sleep=lambda s: None)
    return code, out, capsys.readouterr().out


def test_probe_cli_uses_the_known_list_and_checks_its_digest(tmp_path, capsys):
    from jobhunter.artifacts import write_artifact
    listing = tmp_path.parent / (tmp_path.name + '_k.json')
    digest = write_artifact(listing, {'schema_version': 1, 'job_ids': ['yc-product:1']})
    code, out, _ = run_cli(tmp_path, capsys, ['--known-ids', str(listing), '--known-ids-sha256', digest])
    assert code == 0 and len(json.loads(out.read_text())['jobs']) == 3
    code, out2, text = run_cli(tmp_path, capsys, ['--known-ids', str(listing), '--known-ids-sha256', '0' * 64])
    assert code == 2 and 'artifact_digest_mismatch' in text


@pytest.mark.parametrize('payload', [{'job_ids': 'x'}, {'job_ids': [1]}, ['x'], {}])
def test_a_malformed_known_list_is_refused(tmp_path, capsys, payload):
    from jobhunter.artifacts import write_artifact
    listing = tmp_path.parent / (tmp_path.name + '_bad.json')
    digest = write_artifact(listing, payload)
    code, _, text = run_cli(tmp_path, capsys, ['--known-ids', str(listing), '--known-ids-sha256', digest])
    assert code == 2 and 'invalid_known_ids' in text


def test_a_source_whose_listed_jobs_are_all_already_delivered_is_not_marked_failed_by_a_malformed_stub():
    """Found by the first real pull: getro-accel turned 'failed (invalid_items)' once every good job was known."""
    bad = {'id': 99, 'title': 'Product Manager', 'location': 'United States', 'companyName': 'Acme'}  # no url: rejected
    listing = '<div data-page="' + escape(json.dumps({'props': {'jobPostings': [*JOBS[:2], bad]}}), quote=True) + '"></div>'
    seen = []

    def serve(request):
        seen.append(str(request.url))
        return httpx.Response(200, text=listing if 'jobs/role' in str(request.url) else PAGE)
    with httpx.Client(transport=httpx.MockTransport(serve)) as client:
        record, jobs, note = probe.probe_source(client, YC, '2026-10-18T12:00:00+00:00',
                                                known_ids=frozenset({'yc-product:1', 'yc-product:2'}))
        failed, _, _ = probe.probe_source(client, YC, '2026-10-18T12:00:00+00:00')  # nothing known: pages open normally
    assert jobs == [] and len(seen) == 1 + 3  # the listing, then the second call's three pages; none for the known pair
    assert record['status'] == 'OK-zero-jobs' and record['error'] == '' and 'already_delivered=2' in note
    assert failed['status'] == 'OK'


def test_a_listing_that_is_entirely_malformed_still_fails_even_with_a_known_list():
    listing = '<div data-page="' + escape(json.dumps({'props': {'jobPostings': [{'id': 1, 'title': 'Product Manager'}]}}), quote=True) + '"></div>'
    with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, text=listing))) as client:
        record, jobs, _ = probe.probe_source(client, YC, '2026-10-18T12:00:00+00:00', known_ids=frozenset({'yc-product:7'}))
    assert jobs == [] and record['status'] == 'failed' and record['error'] == 'invalid_items_quarantined'
