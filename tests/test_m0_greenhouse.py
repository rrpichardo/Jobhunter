import httpx
import pytest


def collect(payload=None, status=200):
    from jobhunter.fetch import JsonFetcher
    from jobhunter.greenhouse import collect_board
    client = httpx.Client(transport=httpx.MockTransport(
        lambda request: httpx.Response(status, json=payload)))
    return collect_board(JsonFetcher(client, sleep=lambda delay: None),
                         board="example", company="Example", ai_company=True,
                         captured_at="2026-10-17T12:00:00+00:00")


def test_collects_public_job_identity_and_cleans_embedded_html():
    result = collect({"jobs": [{"id": 101, "title": "AI Product Manager",
        "absolute_url": "https://job-boards.greenhouse.io/example/jobs/101",
        "location": {"name": "Remote, US"},
        "content": "&lt;p&gt;Build &amp;amp; ship AI.&lt;/p&gt;"}], "meta": {"total": 1}})
    assert result.status == "OK"
    assert result.jobs[0].job_id == "greenhouse:example:101"
    assert result.jobs[0].text == "Build & ship AI."
    assert result.coverage == "complete-response"


def test_valid_empty_board_is_distinct_from_failure_and_malformed_response():
    assert collect({"jobs": [], "meta": {"total": 0}}).status == "OK-zero-jobs"
    assert collect(status=403).status == "failed"
    assert collect({"error": "login required"}).status == "failed"
    assert collect({"jobs": [None]}).status == "failed"


def test_duplicate_source_ids_and_partial_response_are_not_silently_accepted():
    item = {"id": 101, "title": "AI Product Manager",
            "absolute_url": "https://example.com/jobs/101", "content": "Build AI."}
    assert collect({"jobs": [item, item]}).status == "failed"
    assert collect({"jobs": [item], "meta": {"total": 10}}).coverage == "partial-response"


@pytest.mark.parametrize("title,expected", [("Product Manager, AI", True),
    ("Group PM", True), ("Product Lead", True), ("Engineering Manager", False),
    ("Product Manager Intern", False), ("Summer Associate, Product Manager", False),
    ("PMO Analyst", False)])
def test_m0_candidate_title_filter_is_explicit(title, expected):
    from jobhunter.greenhouse import is_pm_candidate
    assert is_pm_candidate(title) is expected
