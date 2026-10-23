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
            "absolute_url": "https://example.com/jobs/101", "content": "Build AI. This role is open to MBA students graduating in spring 2027."}
    assert collect({"jobs": [item, item]}).status == "failed"
    assert collect({"jobs": [item], "meta": {"total": 10}}).coverage == "partial-response"


def test_bad_individual_post_is_quarantined_without_discarding_valid_jobs():
    item = {"id": 101, "title": "AI Product Manager", "content": "Build AI products. This role is open to MBA students graduating in spring 2027.",
            "absolute_url": "https://example.com/jobs/101"}
    result = collect({"jobs": [item, item | {"id": 102, "content": None}], "meta": {"total": 2}})
    assert result.status == "OK"
    assert len(result.jobs) == 1
    assert result.items_fetched == 2
    assert result.rejected_items == 1
    assert result.coverage == "complete-response-with-rejections"
    assert collect({"jobs": [item | {"content": None}]}).status == "failed"


def test_absent_total_does_not_claim_complete_coverage():
    assert collect({"jobs": []}).coverage == "unknown"


def test_obviously_hidden_markup_is_excluded_from_source_excerpt_text():
    item = {"id": 101, "title": "AI Product Manager",
            "absolute_url": "https://example.com/jobs/101",
            "content": '<p>Build AI. This role is open to MBA students graduating in spring 2027.</p><span hidden>Hidden claim</span><div style="display: none">Other claim</div>'}
    assert collect({"jobs": [item]}).jobs[0].text == "Build AI. This role is open to MBA students graduating in spring 2027."


def test_inconsistent_empty_response_is_failed_and_schema_failure_retains_attempts():
    from jobhunter.fetch import JsonFetcher
    from jobhunter.greenhouse import collect_board
    assert collect({"jobs": [], "meta": {"total": 50}}).status == "failed"
    calls = []
    item = {"id": 101, "title": "PM", "content": "Build AI. This role is open to MBA students graduating in spring 2027.",
            "absolute_url": "https://example.com/jobs/101"}
    def handler(request):
        calls.append(1)
        return (httpx.Response(503) if len(calls) == 1 else
                httpx.Response(200, json={"jobs": [item, item]}))
    result = collect_board(JsonFetcher(httpx.Client(transport=httpx.MockTransport(handler)),
        sleep=lambda delay: None), board="example", company="Example", ai_company=True,
        captured_at="2026-10-17T12:00:00+00:00")
    assert result.status == "failed"
    assert result.error == "duplicate_source_id"
    assert result.attempts == 2 and result.http_status == 200
    assert result.items_fetched == 2


@pytest.mark.parametrize("title,expected", [("Product Manager, AI", True),
    ("Group PM", True), ("Product Lead", True), ("Engineering Manager", False),
    ("Product Manager Intern", False), ("Summer Associate, Product Manager", False),
    ("PMO Analyst", False)])
def test_m0_candidate_title_filter_is_explicit(title, expected):
    from jobhunter.greenhouse import is_pm_candidate
    assert is_pm_candidate(title) is expected
