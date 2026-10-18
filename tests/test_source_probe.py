import json

import httpx

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


def handler(request):
    url = str(request.url)
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
