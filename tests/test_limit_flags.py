"""Safety stops can be raised or lowered from the command line, and the active limits are printed."""

from html import escape
import json

import httpx
import pytest
import yaml

from scripts import hn_hiring as hn_cli
from scripts import sheets_sync
from scripts import source_probe as probe
from sheet_fakes import MemoryStore
from test_hn_hiring import NOW, comment, hn_client, item
from test_backfill import artifact

JOBS = [{'id': i, 'title': 'Product Manager', 'url': f'/companies/acme/jobs/{i}', 'location': 'United States',
         'companyName': 'Acme'} for i in range(1, 6)]
LISTING = '<div data-page="' + escape(json.dumps({'props': {'jobPostings': JOBS}}), quote=True) + '"></div>'
PAGE = '<script type="application/ld+json">{"@type":"JobPosting","description":"Build things. This role is open to MBA students graduating in spring 2027."}</script>'


def probe_cli(tmp_path, capsys, *flags):
    config = tmp_path / 'registry.yaml'
    config.write_text(yaml.safe_dump({'boards': {}, 'needs_setup': [], 'detail_sources': [
        {'id': 'yc-product', 'kind': 'yc', 'url': 'https://www.ycombinator.com/jobs/role/product-manager'}]}))
    out = tmp_path.parent / (tmp_path.name + '_p.json')
    client = httpx.Client(transport=httpx.MockTransport(
        lambda r: httpx.Response(200, text=LISTING if 'jobs/role' in str(r.url) else PAGE)))
    code = probe.main(['--config', str(config), '--output', str(out), '--delay', '0', *flags],
                      client=client, sleep=lambda s: None)
    return code, out, capsys.readouterr().out


def test_detail_safety_stop_flag_changes_how_many_pages_are_opened_and_is_printed(tmp_path, capsys):
    code, out, text = probe_cli(tmp_path, capsys, '--detail-safety-stop', '2')
    payload = json.loads(out.read_text())
    assert code == 0 and len(payload['jobs']) == 2 and 'details_skipped=3' in payload['probe']['notes']['yc-product']
    assert 'limits: lookback_days=28 detail_safety_stop=2' in text


def test_the_default_opens_every_page_up_to_the_standing_stop(tmp_path, capsys):
    code, out, text = probe_cli(tmp_path, capsys)
    assert code == 0 and len(json.loads(out.read_text())['jobs']) == 5
    assert f'detail_safety_stop={probe.DETAIL_SAFETY_STOP}' in text


@pytest.mark.parametrize('flag,value,code', [('--detail-safety-stop', '0', 'invalid_safety_stop'),
                                              ('--detail-safety-stop', '100001', 'invalid_safety_stop'),
                                              ('--lookback-days', '366', 'invalid_lookback_days')])
def test_out_of_range_limits_are_refused_before_any_request(tmp_path, capsys, flag, value, code):
    result, out, text = probe_cli(tmp_path, capsys, flag, value)
    assert result == 2 and not out.exists() and code in text


def test_hn_candidate_safety_stop_flag_is_applied_and_reported(tmp_path, capsys):
    story = item(1000, [comment(2001 + 2 * i, f'Co{i} | Product Manager | Remote US') for i in range(5)])
    out = tmp_path.parent / (tmp_path.name + '_hn.json')
    assert hn_cli.main(['candidates', '--output', str(out), '--candidate-safety-stop', '3'], client=hn_client(story),
                       sleep=lambda s: None, now=lambda: NOW) == 0
    text = capsys.readouterr().out
    assert 'candidate_safety_stop=3' in text and 'candidates=3' in text and 'truncated=True' in text


def test_hn_candidate_safety_stop_must_be_in_range(tmp_path, capsys):
    out = tmp_path.parent / (tmp_path.name + '_hn0.json')
    assert hn_cli.main(['candidates', '--output', str(out), '--candidate-safety-stop', '0'],
                       client=hn_client(item(1000, [])), sleep=lambda s: None, now=lambda: NOW) == 2
    assert 'invalid_safety_stop' in capsys.readouterr().out and not out.exists()


def test_batch_pause_flag_sets_the_pause_between_batches(tmp_path, monkeypatch):
    pauses = []
    monkeypatch.setattr(sheets_sync.time, 'sleep', pauses.append)
    out, backend = artifact(tmp_path, 320), MemoryStore()
    assert sheets_sync.main(['--input', str(out), '--run-id', 'flagged', '--batch-pause', '0.5'], store=backend) == 0
    assert pauses == [0.5, 0.5]


def test_batch_pause_out_of_range_is_refused_before_any_write(tmp_path, monkeypatch, capsys):
    out, backend = artifact(tmp_path, 320), MemoryStore()
    assert sheets_sync.main(['--input', str(out), '--batch-pause', '61'], store=backend) == 2
    assert 'invalid_batch_pause' in capsys.readouterr().out and backend.tables == {}
