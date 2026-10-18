import json

import httpx
import pytest

from scripts import source_probe as probe

GH = {"jobs": [{"id": 1, "title": "Product Manager, AI Agents", "location": {"name": "Remote"},
                "content": "<p>Build agents.</p>", "absolute_url": "https://example.com/1"},
               {"id": 2, "title": "Software Engineer", "location": {"name": "Remote"},
                "content": "<p>Code.</p>", "absolute_url": "https://example.com/2"}]}
REGISTRY = {
    "boards": {"greenhouse": [{"board": "good", "company": "Good", "tag": "ai"},
                              {"board": "ghost", "company": "Ghost", "tag": "other", "candidate": True},
                              {"board": "walled", "company": "Walled", "tag": "other"},
                              {"board": "broken", "company": "Broken", "tag": "other"}]},
    "aggregators": [{"id": "badjson", "kind": "remotive", "url": "https://agg.test/bad"}],
    "listing_only": [{"id": "hn", "kind": "hn", "url": "https://hn.test/x"}],
    "needs_setup": [{"id": "jsearch", "env": ["JSEARCH_API_KEY"], "action": "add key"},
                    {"id": "linkedin-logged-in", "env": [], "action": "cookie"}],
}


YC_LIST = ('<div data-page="{&quot;props&quot;:{&quot;jobPostings&quot;:[{&quot;id&quot;:7,&quot;title&quot;:'
           '&quot;Product Manager, AI&quot;,&quot;url&quot;:&quot;/companies/acme/jobs/abc-pm&quot;,&quot;location&quot;:'
           '&quot;San Francisco, CA&quot;,&quot;companyName&quot;:&quot;Acme&quot;,&quot;salaryRange&quot;:&quot;&quot;},'
           '{&quot;id&quot;:8,&quot;title&quot;:&quot;Designer&quot;,&quot;url&quot;:&quot;/companies/acme/jobs/d&quot;,'
           '&quot;location&quot;:&quot;Remote&quot;,&quot;companyName&quot;:&quot;Acme&quot;}]}}"></div>')
YC_PAGE = ('<script type="application/ld+json">{"@type":"JobPosting","description":"Build AI agents."}</script>')


def handler(request):
    url = str(request.url)
    if "ycombinator.com/jobs/role" in url:
        return httpx.Response(200, text=YC_LIST)
    if "ycombinator.com/companies" in url:
        return httpx.Response(200, text=YC_PAGE)
    if "good" in url:
        return httpx.Response(200, json=GH)
    if "ghost" in url:
        return httpx.Response(404)
    if "walled" in url:
        return httpx.Response(429, headers={"Retry-After": "60"})
    if "broken" in url:
        return httpx.Response(500)
    if "agg.test" in url:
        return httpx.Response(200, text="<html>not json")
    return httpx.Response(200, json={"hits": [{"title": "Ask HN: Who is hiring? (October 2026)", "num_comments": 5}]})


def run_probe(environ=None):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return probe.run(REGISTRY, client, delay=0, sleep=lambda s: None, environ=environ or {},
                     now=lambda: "2026-10-18T00:00:00+00:00")


def test_each_source_is_classified_and_unresponsive_candidates_are_dropped():
    payload = run_probe()
    by_id = {s["source_id"]: s for s in payload["sources"]}
    assert by_id["greenhouse:good"]["status"] == "OK" and by_id["greenhouse:good"]["selected_for_m0"] == 1
    assert "greenhouse:ghost" not in by_id
    assert (by_id["greenhouse:walled"]["status"], by_id["greenhouse:walled"]["error"]) == ("blocked", "http_429")
    assert (by_id["greenhouse:broken"]["status"], by_id["greenhouse:broken"]["error"]) == ("failed", "http_500")
    assert by_id["badjson"]["error"] == "invalid_json"
    assert by_id["hn"]["status"] == "OK-zero-jobs" and by_id["hn"]["jobs_fetched"] == 5
    assert by_id["jsearch"]["status"] == "needs setup" and by_id["linkedin-logged-in"]["status"] == "needs setup"
    assert payload["probe"]["notes"]["jsearch"] == "keys_missing:JSEARCH_API_KEY"
    assert [row["Job ID"] for row in payload["jobs"]] == ["greenhouse:good:1"]


def test_no_request_is_made_for_needs_setup_sources():
    seen = []
    client = httpx.Client(transport=httpx.MockTransport(lambda r: seen.append(str(r.url)) or handler(r)))
    probe.run(REGISTRY, client, delay=0, sleep=lambda s: None, environ={})
    assert not any("linkedin" in url or "jsearch" in url or "x.com" in url for url in seen)
    assert len(seen) == 6  # 4 boards (incl. the ghost candidate) + 1 aggregator + 1 listing


def test_a_blocked_source_is_requested_exactly_once():
    seen = []
    client = httpx.Client(transport=httpx.MockTransport(lambda r: seen.append(str(r.url)) or handler(r)))
    probe.run(REGISTRY, client, delay=0, sleep=lambda s: None, environ={})
    assert sum("walled" in url for url in seen) == 1


def test_total_cap_keeps_source_counts_honest(monkeypatch):
    monkeypatch.setattr(probe, "TOTAL_LIMIT", 0)
    payload = run_probe()
    assert payload["jobs"] == [] and payload["sources"][0]["status"] == "OK-zero-jobs"
    assert all(s["selected_for_m0"] == 0 for s in payload["sources"])


def test_cli_writes_artifact_and_delivery_roundtrips_through_sheets_sync(tmp_path, capsys, monkeypatch):
    import yaml
    from scripts.sheets_sync import main as sync
    from sheet_fakes import MemoryStore
    config = tmp_path / "registry.yaml"
    config.write_text(yaml.safe_dump(REGISTRY))
    out = tmp_path.parent / (tmp_path.name + "_probe.json")
    client = httpx.Client(transport=httpx.MockTransport(handler))
    assert probe.main(["--config", str(config), "--output", str(out), "--delay", "0"],
                      client=client, sleep=lambda s: None) == 0
    assert "probe_sha256=" in capsys.readouterr().out
    backend = MemoryStore()
    assert sync(["--input", str(out), "--run-id", "probe1"], store=backend) == 0
    assert "source_problems_recorded=3" in capsys.readouterr().out
    assert len(backend.tables["Jobs"]) == 2 and len(backend.tables["Sources"]) == 8
    assert sync(["--input", str(out), "--run-id", "probe1"], store=backend) == 0
    assert len(backend.tables["Jobs"]) == 2 and len(backend.tables["Run Log"]) == 2


def test_sync_rejects_inconsistent_multi_source_payload(tmp_path):
    from scripts.sheets_sync import main as sync
    from sheet_fakes import MemoryStore
    payload = run_probe()
    payload["sources"][0]["selected_for_m0"] = 5
    out = tmp_path.parent / (tmp_path.name + "_bad.json")
    out.write_text(json.dumps(payload))
    backend = MemoryStore()
    assert sync(["--input", str(out)], store=backend) == 2
    assert backend.tables == {}


def test_detail_source_fetches_only_shortlisted_pm_pages_and_delivers_them():
    registry = {**REGISTRY, "boards": {}, "aggregators": [], "listing_only": [], "needs_setup": [],
                "detail_sources": [{"id": "yc-product", "kind": "yc", "url": "https://www.ycombinator.com/jobs/role/product-manager"}]}
    seen = []
    client = httpx.Client(transport=httpx.MockTransport(lambda r: seen.append(str(r.url)) or handler(r)))
    payload = probe.run(registry, client, delay=0, sleep=lambda s: None, environ={}, now=lambda: "2026-10-18T00:00:00+00:00")
    assert [row["Job ID"] for row in payload["jobs"]] == ["yc-product:7"]
    assert payload["jobs"][0]["Brief description"] == "Build AI agents."
    assert sum("ycombinator.com/companies" in url for url in seen) == 1  # the Designer page was never fetched
    source = payload["sources"][0]
    assert (source["status"], source["jobs_fetched"], source["pm_candidates"], source["selected_for_m0"]) == ("OK", 2, 1, 1)


def test_a_refused_detail_page_stops_that_source_and_is_never_retried():
    registry = {**REGISTRY, "boards": {}, "aggregators": [], "listing_only": [], "needs_setup": [],
                "detail_sources": [{"id": "yc-product", "kind": "yc", "url": "https://www.ycombinator.com/jobs/role/product-manager"}]}
    seen = []

    def refuse(request):
        seen.append(str(request.url))
        return httpx.Response(200, text=YC_LIST) if "jobs/role" in str(request.url) else httpx.Response(429)
    payload = probe.run(registry, httpx.Client(transport=httpx.MockTransport(refuse)), delay=0,
                        sleep=lambda s: None, environ={})
    assert payload["jobs"] == [] and sum("companies" in url for url in seen) == 1


@pytest.mark.parametrize('blocked_status', [401, 403, 406, 429])
@pytest.mark.parametrize('successful_details', [0, 1])
def test_detail_blocks_keep_actual_evidence_and_deliver_prior_valid_jobs(
        blocked_status, successful_details, tmp_path):
    from html import escape
    from scripts.sheets_sync import main as sync
    from sheet_fakes import MemoryStore
    listing = '<div data-page="' + escape(json.dumps({'props': {'jobPostings': [
        {'id': i, 'title': 'Product Manager, AI', 'url': f'/companies/acme/jobs/{i}',
         'location': 'United States', 'companyName': 'Acme'} for i in range(3)
    ]}}), quote=True) + '"></div>'
    registry = {'boards': {}, 'needs_setup': [], 'detail_sources': [
        {'id': 'yc-product', 'kind': 'yc', 'url': 'https://www.ycombinator.com/jobs/role/product-manager'}]}
    seen = []

    def serve(request):
        seen.append(str(request.url))
        if 'jobs/role' in str(request.url):
            return httpx.Response(200, text=listing)
        if request.url.path.endswith(f'/{successful_details}'):
            return httpx.Response(blocked_status)
        return httpx.Response(200, text=YC_PAGE)

    with httpx.Client(transport=httpx.MockTransport(serve)) as client:
        payload = probe.run(registry, client, delay=0, sleep=lambda _: None, environ={})
    source = payload['sources'][0]
    assert (source['status'], source['http_status'], source['error']) == (
        'blocked', blocked_status, f'http_{blocked_status}')
    assert source['selected_for_m0'] == successful_details == len(payload['jobs'])
    assert len(seen) == successful_details + 2  # listing, successful details, then stop
    path = tmp_path / 'partial.json'
    path.write_text(json.dumps(payload))
    store = MemoryStore()
    assert sync(['--input', str(path), '--run-id', 'partial'], store=store) == 0
    assert len(store.tables['Jobs']) == successful_details + 1
    headers, values = store.tables['Sources']
    assert values[headers.index('Status')] == 'blocked'
    assert values[headers.index('HTTP status')] == blocked_status


@pytest.mark.parametrize('change', [
    {'valid_jobs': None}, {'valid_jobs': 0}, {'selected_for_m0': 2}, {'error': ''},
])
def test_partial_source_jobs_require_explicit_successful_item_evidence(change):
    from test_sheet_records import job
    from jobhunter.sheets import prepare_payload
    source = probe.record('greenhouse:example', 'blocked', '2026-10-18T00:00:00+00:00',
                          error='http_429', http=429, valid=1, selected=1)
    with pytest.raises(ValueError, match='job_source_not_successful'):
        prepare_payload([job()], [source | change])


@pytest.mark.parametrize('location,salary,expected', [
    ('Colombia', '70,000 USD YEAR', 1), ('Dominican Republic', '80,000 USD YEAR', 1),
    ('Colombia', '65,000 USD YEAR', 0), ('Brazil', '90,000 USD YEAR', 0),
    ('Remote - Latin America', '', 1),
])
def test_detail_collection_uses_regional_location_and_salary_preferences(location, salary, expected):
    listing = YC_LIST.replace('San Francisco, CA', location).replace(
        '&quot;salaryRange&quot;:&quot;&quot;', f'&quot;salaryRange&quot;:&quot;{salary}&quot;')
    entry = {'id': 'yc-product', 'kind': 'yc', 'url': 'https://www.ycombinator.com/jobs/role/product-manager'}
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(
            200, text=listing if 'jobs/role' in str(request.url) else YC_PAGE))) as client:
        source, jobs, _ = probe.probe_source(client, entry, '2026-10-18T00:00:00+00:00')
    assert source['selected_for_m0'] == len(jobs) == expected
    if jobs:
        assert jobs[0].location == location


def test_duplicates_across_sources_are_merged_and_counted():
    gh = {"jobs": [{"id": 1, "title": "Product Manager, AI Agents", "location": {"name": "Remote"},
                    "content": "<p>Agents.</p>", "absolute_url": "https://job-boards.greenhouse.io/good/jobs/1"}]}
    remotive = {"jobs": [{"id": 9, "title": "Product Manager, AI Agents", "company_name": "Good",
                          "candidate_required_location": "USA", "description": "<p>Agents.</p>",
                          "url": "https://job-boards.greenhouse.io/good/jobs/1?ref=remotive"}]}
    registry = {"boards": {"greenhouse": [{"board": "good", "company": "Good", "tag": "ai"}]},
                "aggregators": [{"id": "remotive", "kind": "remotive", "url": "https://agg.test/r"}],
                "needs_setup": []}

    def serve(request):
        return httpx.Response(200, json=gh if "greenhouse" in str(request.url) else remotive)
    payload = probe.run(registry, httpx.Client(transport=httpx.MockTransport(serve)), delay=0,
                        sleep=lambda s: None, environ={})
    assert [row["Job ID"] for row in payload["jobs"]] == ["greenhouse:good:1"]
    assert "Also listed by: remotive" in payload["jobs"][0]["More details"]
    by_id = {s["source_id"]: s for s in payload["sources"]}
    assert (by_id["greenhouse:good"]["selected_for_m0"], by_id["remotive"]["selected_for_m0"],
            by_id["remotive"]["status"]) == (1, 0, "OK-zero-jobs")
    assert payload["probe"]["notes"]["duplicates_merged"] == 1
