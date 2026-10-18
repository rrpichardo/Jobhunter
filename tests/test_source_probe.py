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


def test_refused_detail_page_returns_no_jobs():
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


def test_known_low_regional_salary_does_not_consume_a_detail_slot():
    from html import escape
    listing = '<div data-page="' + escape(json.dumps({'props': {'jobPostings': [
        {'id': i, 'title': 'Product Manager, AI', 'url': f'/companies/acme/jobs/{i}',
         'location': 'Colombia', 'companyName': 'Acme', 'salaryRange': salary}
        for i, salary in [(1, '40,000 USD YEAR'), (2, '80,000 USD YEAR')]
    ]}}), quote=True) + '"></div>'
    seen = []

    def serve(request):
        seen.append(str(request.url))
        return httpx.Response(200, text=listing if 'jobs/role' in str(request.url) else YC_PAGE)

    entry = {'id': 'yc-product', 'kind': 'yc', 'url': 'https://www.ycombinator.com/jobs/role/product-manager'}
    with httpx.Client(transport=httpx.MockTransport(serve)) as client:
        source, jobs, _ = probe.probe_source(client, entry, '2026-10-18T00:00:00+00:00')
    assert [job.job_id for job in jobs] == ['yc-product:2']
    assert all(not url.endswith('/1') for url in seen)


def test_blank_regional_stub_salary_does_not_fetch_a_text_only_detail():
    listing = YC_LIST.replace('San Francisco, CA', 'Colombia')
    seen = []
    with httpx.Client(transport=httpx.MockTransport(lambda request: seen.append(str(request.url)) or
            httpx.Response(200, text=listing))) as client:
        source, jobs, _ = probe.probe_source(client, {'id': 'yc-product', 'kind': 'yc',
            'url': 'https://www.ycombinator.com/jobs/role/product-manager'}, '2026-10-18T00:00:00+00:00')
    assert jobs == [] and len(seen) == 1


def test_recursion_failure_in_a_source_parser_does_not_abort_other_sources(monkeypatch):
    registry = {**REGISTRY, 'detail_sources': [{'id': 'getro', 'kind': 'getro', 'url': 'https://getro.test/jobs'}]}
    def parser_limit(*args):
        raise RecursionError('source structure exceeds parser recursion limit')
    monkeypatch.setitem(probe.DETAIL_SOURCES, 'getro', (parser_limit, probe.DETAIL_SOURCES['getro'][1]))
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, text='source data')
                     if 'getro.test' in str(request.url) else handler(request))) as client:
        payload = probe.run(registry, client, delay=0, sleep=lambda _: None, environ={})
    assert payload['jobs']
    source = next(s for s in payload['sources'] if s['source_id'] == 'getro')
    assert (source['status'], source['error']) == ('failed', 'invalid_board_response')


def test_response_byte_limit_stops_reading_before_the_rest_of_the_body(monkeypatch):
    monkeypatch.setattr(probe, 'MAX_BYTES', 4)
    consumed = []

    class Body(httpx.SyncByteStream):
        def __iter__(self):
            for chunk in [b'12345', b'must-not-read']:
                consumed.append(chunk)
                yield chunk

    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, stream=Body()))) as client:
        status, body, error = probe.fetch_once(client, 'https://example.com/oversized')
    assert (status, body, error) == (200, None, 'invalid_board_response')
    assert consumed == [b'12345']


def test_total_cap_reports_how_many_jobs_were_omitted(monkeypatch):
    monkeypatch.setattr(probe, 'TOTAL_LIMIT', 0)
    payload = run_probe()
    assert payload['probe']['notes']['total_limit_skipped'] == 1


def test_detail_budget_prioritizes_known_ai_titles_and_reports_skipped_candidates(monkeypatch):
    from html import escape
    monkeypatch.setattr(probe, 'PER_SOURCE_LIMIT', 1)
    listing = '<div data-page="' + escape(json.dumps({'props': {'jobPostings': [
        {'id': i, 'title': title, 'url': f'/companies/acme/jobs/{i}',
         'location': 'United States', 'companyName': 'Acme'}
        for i, title in [(1, 'Product Manager'), (2, 'Product Manager'), (3, 'AI Product Manager')]
    ]}}), quote=True) + '"></div>'
    seen = []
    def serve(request):
        seen.append(str(request.url))
        return httpx.Response(200, text=listing if 'jobs/role' in str(request.url) else
            YC_PAGE if request.url.path.endswith('/3') else YC_PAGE.replace('Build AI agents.', 'Build products.'))
    with httpx.Client(transport=httpx.MockTransport(serve)) as client:
        source, jobs, note = probe.probe_source(client, {'id': 'yc-product', 'kind': 'yc',
            'url': 'https://www.ycombinator.com/jobs/role/product-manager'}, '2026-10-18T00:00:00+00:00')
    assert [job.job_id for job in jobs] == ['yc-product:3']
    assert len(seen) == 2
    assert 'details_skipped=2' in note


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


@pytest.mark.parametrize('field,error', [('job', 'invalid_job_fields'), ('source', 'invalid_source_records')])
def test_unhashable_artifact_source_ids_have_validation_errors_before_google(
        field, error, tmp_path, monkeypatch, capsys):
    from scripts import sheets_sync
    payload = run_probe()
    if field == 'job':
        payload['jobs'][0]['Source'] = []
    else:
        payload['sources'][0]['source_id'] = []
    path = tmp_path / 'bad-source.json'
    path.write_text(json.dumps(payload))
    calls = []
    monkeypatch.setattr(sheets_sync, 'open_workbook', lambda: calls.append('Google'))
    assert sheets_sync.main(['--input', str(path)]) == 2
    assert f'sync_failed: {error}' in capsys.readouterr().out
    assert calls == []


# --- keyed APIs: JSearch and Jooble --------------------------------------------------------

KEY = "SECRET-TEST-KEY-123"
KEYED_ENV = {"JSEARCH_API_KEY": KEY, "JOOBLE_API_KEY": KEY}
STAMP = "2026-10-18T00:00:00+00:00"
JSEARCH_BODY = {"status": "OK", "data": [
    {"job_id": "js-1", "employer_name": "Acme", "job_title": "AI Product Manager",
     "job_description": "<p>Build LLM agents.</p>", "job_apply_link": "https://acme.test/apply/1",
     "job_google_link": "https://www.google.com/search?q=1", "job_city": "Austin", "job_state": "TX",
     "job_country": "US", "job_is_remote": False, "job_min_salary": 150000, "job_max_salary": 190000,
     "job_salary_currency": "USD", "job_salary_period": "YEAR"},
    {"job_id": "js-2", "employer_name": "Beta", "job_title": "Software Engineer",
     "job_description": "Code.", "job_apply_link": "https://beta.test/2"},
    {"job_id": "js-3", "employer_name": "Gamma", "job_title": "Product Manager, AI",
     "job_description": "AI.", "job_apply_link": "http://insecure.test/3"}]}
JOOBLE_BODY = {"totalCount": 2, "jobs": [
    {"id": 555, "title": "Senior <b>Product</b> <b>Manager</b>, AI", "location": "New York, NY",
     "snippet": "build <b>LLM</b> features", "salary": "$160k", "source": "acme.test", "type": "Full-time",
     "link": "https://jooble.org/desc/555", "company": "Delta", "updated": "2026-10-16"},
    {"id": 556, "title": "Chef", "location": "Boston", "snippet": "cook", "link": "https://jooble.org/desc/556",
     "company": "Eats"}]}


def keyed_registry():
    import yaml
    from pathlib import Path
    config = yaml.safe_load(Path("sources/v0_sources.yaml").read_text(encoding="utf-8"))
    return {"boards": {}, "keyed_apis": config["keyed_apis"], "needs_setup": []}


def keyed_serve(seen, *, jsearch=None, jooble=None):
    def serve(request):
        seen.append(request)
        if request.url.host == "jsearch.p.rapidapi.com":
            return jsearch(request) if jsearch else httpx.Response(200, json=JSEARCH_BODY)
        return jooble(request) if jooble else httpx.Response(200, json=JOOBLE_BODY)
    return serve


def run_keyed(serve, environ):
    with httpx.Client(transport=httpx.MockTransport(serve)) as client:
        return probe.run(keyed_registry(), client, delay=0, sleep=lambda s: None, environ=environ, now=lambda: STAMP)


def test_registry_declares_both_keyed_sources_and_no_longer_lists_them_as_needs_setup():
    import yaml
    from pathlib import Path
    config = yaml.safe_load(Path("sources/v0_sources.yaml").read_text(encoding="utf-8"))
    assert [e["id"] for e in config["keyed_apis"]] == ["jsearch", "jooble"]
    assert not {"jsearch", "jooble", "adzuna"} & {e["id"] for e in config["needs_setup"]}
    assert "adzuna" not in json.dumps(config["keyed_apis"])  # skipped as paid-only, not a source row
    assert {e["id"] for e in probe.entries(config)} >= {"jsearch", "jooble"}


def test_keyed_sources_make_one_request_each_and_deliver_through_the_shared_filter():
    seen = []
    payload = run_keyed(keyed_serve(seen), KEYED_ENV)
    assert [(r.method, r.url.host) for r in seen] == [("GET", "jsearch.p.rapidapi.com"), ("POST", "jooble.org")]
    js, jb = seen
    assert dict(js.url.params) == {"query": "AI product manager in USA", "page": "1", "num_pages": "1",
                                   "date_posted": "week"}
    assert js.url.path == "/search-v2"
    assert js.headers["X-RapidAPI-Key"] == KEY and js.headers["X-RapidAPI-Host"] == "jsearch.p.rapidapi.com"
    assert jb.url.path == f"/api/{KEY}"
    assert json.loads(jb.content) == {"keywords": "AI product manager", "location": "United States", "page": "1"}
    by_id = {s["source_id"]: s for s in payload["sources"]}
    assert (by_id["jsearch"]["status"], by_id["jsearch"]["jobs_fetched"], by_id["jsearch"]["valid_jobs"],
            by_id["jsearch"]["rejected_items"], by_id["jsearch"]["selected_for_m0"]) == ("OK", 3, 2, 1, 1)
    assert (by_id["jooble"]["status"], by_id["jooble"]["jobs_fetched"], by_id["jooble"]["selected_for_m0"]) == (
        "OK", 2, 1)
    assert [(row["Source"], row["Job title"]) for row in payload["jobs"]] == [
        ("jsearch", "AI Product Manager"), ("jooble", "Senior Product Manager , AI")]
    assert payload["jobs"][0]["Salary"] == "150,000 - 190,000 USD YEAR"


def test_keyed_sources_respect_the_per_source_limit(monkeypatch):
    monkeypatch.setattr(probe, "PER_SOURCE_LIMIT", 1)
    many = {"status": "OK", "data": [{**JSEARCH_BODY["data"][0], "job_id": f"js-{i}",
                                      "job_apply_link": f"https://acme.test/apply/{i}"} for i in range(3)]}
    payload = run_keyed(keyed_serve([], jsearch=lambda r: httpx.Response(200, json=many)), KEYED_ENV)
    by_id = {s["source_id"]: s for s in payload["sources"]}
    assert by_id["jsearch"]["valid_jobs"] == 3 and by_id["jsearch"]["selected_for_m0"] == 1
    assert [row["Source"] for row in payload["jobs"]] == ["jsearch", "jooble"]


def test_keyed_sources_share_the_cross_source_dedupe_path():
    link = "https://job-boards.greenhouse.io/acme/jobs/77"
    one = {"status": "OK", "data": [{**JSEARCH_BODY["data"][0], "job_apply_link": link}]}
    other = {"totalCount": 1, "jobs": [{**JOOBLE_BODY["jobs"][0], "link": link + "?utm_source=jooble"}]}
    payload = run_keyed(keyed_serve([], jsearch=lambda r: httpx.Response(200, json=one),
                                    jooble=lambda r: httpx.Response(200, json=other)), KEYED_ENV)
    assert [row["Source"] for row in payload["jobs"]] == ["jsearch"]
    assert "Also listed by: jooble" in payload["jobs"][0]["More details"]
    assert payload["probe"]["notes"]["duplicates_merged"] == 1


@pytest.mark.parametrize("environ,missing", [
    ({}, "JSEARCH_API_KEY"), ({"JSEARCH_API_KEY": ""}, "JSEARCH_API_KEY"),
    ({"JSEARCH_API_KEY": "   "}, "JSEARCH_API_KEY"), ({"JSEARCH_API_KEY": None}, "JSEARCH_API_KEY")])
def test_missing_or_blank_key_is_needs_setup_with_no_request(environ, missing):
    seen = []
    payload = run_keyed(keyed_serve(seen), environ)
    assert seen == []  # not even the other source: neither key is set
    by_id = {s["source_id"]: s for s in payload["sources"]}
    assert by_id["jsearch"]["status"] == "needs setup" and by_id["jsearch"]["attempts"] == 0
    assert payload["probe"]["notes"]["jsearch"] == f"keys_missing:{missing}"
    assert payload["probe"]["notes"]["jooble"] == "keys_missing:JOOBLE_API_KEY"
    assert payload["jobs"] == []


def test_one_missing_key_does_not_stop_the_other_source():
    seen = []
    payload = run_keyed(keyed_serve(seen), {"JOOBLE_API_KEY": KEY})
    assert [r.url.host for r in seen] == ["jooble.org"]
    assert {s["source_id"]: s["status"] for s in payload["sources"]} == {"jsearch": "needs setup", "jooble": "OK"}


@pytest.mark.parametrize("code", [401, 403, 406, 429])
def test_blocked_keyed_sources_are_requested_exactly_once(code):
    seen = []
    refuse = lambda r: httpx.Response(code, headers={"Retry-After": "1"})  # noqa: E731
    payload = run_keyed(keyed_serve(seen, jsearch=refuse, jooble=refuse), KEYED_ENV)
    assert len(seen) == 2
    for source in payload["sources"]:
        assert (source["status"], source["error"], source["http_status"], source["attempts"]) == (
            "blocked", f"http_{code}", code, 1)
    assert payload["jobs"] == []


@pytest.mark.parametrize("serve_one,status,error", [
    (lambda r: httpx.Response(500), "failed", "http_500"),
    (lambda r: httpx.Response(302, headers={"Location": "https://elsewhere.test/"}), "failed", "http_302"),
    (lambda r: httpx.Response(200, text="<html>not json"), "failed", "invalid_json"),
    (lambda r: httpx.Response(200, json={"unexpected": True}), "failed", "invalid_board_response"),
    (lambda r: (_ for _ in ()).throw(httpx.ReadTimeout("slow", request=r)), "failed", "timeout"),
    (lambda r: (_ for _ in ()).throw(httpx.ConnectError("down", request=r)), "failed", "transport_error"),
])
def test_keyed_failures_are_classified_without_retry(serve_one, status, error):
    seen = []
    payload = run_keyed(keyed_serve(seen, jsearch=serve_one, jooble=serve_one), KEYED_ENV)
    assert len(seen) == 2
    assert [(s["status"], s["error"]) for s in payload["sources"]] == [(status, error)] * 2


def test_keyed_response_over_the_size_cap_is_rejected(monkeypatch):
    monkeypatch.setattr(probe, "MAX_BYTES", 10)
    payload = run_keyed(keyed_serve([]), KEYED_ENV)
    assert [(s["status"], s["error"]) for s in payload["sources"]] == [("failed", "invalid_board_response")] * 2


def _leaky(kind):
    """Failures whose own message would expose the key if it were ever recorded."""
    def serve(request):
        leak = f"{request.url} {request.headers.get('X-RapidAPI-Key', '')}"
        if kind == "timeout":
            raise httpx.ReadTimeout(leak, request=request)
        if kind == "transport":
            raise httpx.ConnectError(leak, request=request)
        if kind == "other":
            raise RuntimeError(leak)
        if kind == "success":
            return httpx.Response(200, json=JSEARCH_BODY if request.url.host.startswith("jsearch") else JOOBLE_BODY)
        if kind == "bad_json":
            return httpx.Response(200, text=f"not json {leak}")
        return httpx.Response(int(kind), text=f"error for {leak}", headers={"X-Echo": leak})
    return serve


@pytest.mark.parametrize("kind", ["success", "403", "429", "500", "timeout", "transport", "other", "bad_json"])
def test_api_key_never_appears_in_payload_summary_or_output(kind, capsys, caplog):
    import logging
    caplog.set_level(logging.DEBUG)
    seen = []
    serve = _leaky(kind)
    payload = run_keyed(keyed_serve(seen, jsearch=serve, jooble=serve), KEYED_ENV)
    print(probe.summary(payload))
    printed = capsys.readouterr().out
    assert len(seen) == 2
    assert KEY not in json.dumps(payload) and KEY not in printed and KEY not in caplog.text
    assert KEY not in repr(payload)


@pytest.mark.parametrize("kind", ["success", "403", "500", "timeout", "bad_json"])
def test_api_key_never_reaches_the_cli_artifact_stdout_or_sheet(kind, tmp_path, capsys, monkeypatch, caplog):
    import logging
    import yaml
    from scripts.sheets_sync import main as sync
    from sheet_fakes import MemoryStore
    caplog.set_level(logging.DEBUG)
    monkeypatch.setenv("JSEARCH_API_KEY", KEY)
    monkeypatch.setenv("JOOBLE_API_KEY", KEY)
    config = tmp_path / "registry.yaml"
    config.write_text(yaml.safe_dump(keyed_registry()))
    out = tmp_path.parent / (tmp_path.name + "_keyed.json")
    serve = _leaky(kind)
    client = httpx.Client(transport=httpx.MockTransport(keyed_serve([], jsearch=serve, jooble=serve)))
    assert probe.main(["--config", str(config), "--output", str(out), "--delay", "0"],
                      client=client, sleep=lambda s: None) == 0
    backend = MemoryStore()
    assert sync(["--input", str(out), "--run-id", "keyed1"], store=backend) == 0
    everything = capsys.readouterr().out + out.read_text() + repr(backend.tables) + caplog.text
    assert KEY not in everything


def test_keyed_sources_round_trip_through_sheets_sync(tmp_path, capsys, monkeypatch):
    import yaml
    from scripts.sheets_sync import main as sync
    from sheet_fakes import MemoryStore
    monkeypatch.setenv("JSEARCH_API_KEY", KEY)
    monkeypatch.delenv("JOOBLE_API_KEY", raising=False)
    config = tmp_path / "registry.yaml"
    config.write_text(yaml.safe_dump(keyed_registry()))
    out = tmp_path.parent / (tmp_path.name + "_keyed_rt.json")
    seen = []
    client = httpx.Client(transport=httpx.MockTransport(keyed_serve(seen)))
    assert probe.main(["--config", str(config), "--output", str(out), "--delay", "0"],
                      client=client, sleep=lambda s: None) == 0
    printed = capsys.readouterr().out
    assert "keys_missing:JOOBLE_API_KEY" in printed and len(seen) == 1
    backend = MemoryStore()
    assert sync(["--input", str(out), "--run-id", "keyed1"], store=backend) == 0
    assert "source_problems_recorded=0" in capsys.readouterr().out  # needs setup is evidence, not a failure
    headers, *rows = backend.tables["Sources"]
    statuses = {row[headers.index("Source ID")]: row[headers.index("Status")] for row in rows}
    assert statuses == {"jsearch": "OK", "jooble": "needs setup"}
    assert len(backend.tables["Jobs"]) == 2  # header plus the one AI PM job
    assert sync(["--input", str(out), "--run-id", "keyed1"], store=backend) == 0
    assert len(backend.tables["Jobs"]) == 2 and len(backend.tables["Run Log"]) == 2


def test_total_cap_is_shared_round_robin_across_sources():
    from jobhunter.postings import Posting

    def job(source, n):
        return (Posting(f"{source}:{n}", source, "Co", "Product Manager, AI", "Remote", "Build AI.",
                        f"https://example.com/{source}/{n}", "2026-10-18T00:00:00+00:00"), "")
    items = [job("early", n) for n in range(3)] + [job("late", n) for n in range(2)]
    order = [posting.job_id for posting, _ in probe.fair_order(items)]
    assert order == ["early:0", "late:0", "early:1", "late:1", "early:2"]
    assert probe.fair_order([]) == []
