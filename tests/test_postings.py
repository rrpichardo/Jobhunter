import json

import pytest

from jobhunter import postings as p

CTX = {"board": "acme", "company": "Acme", "tag": "other", "source_id": "greenhouse:acme",
       "captured_at": "2026-10-18T00:00:00+00:00"}


def posting(title="Senior Product Manager, AI", location="San Francisco, CA", text="Build AI agents.",
            tag="other"):
    return p.Posting("greenhouse:acme:1", "greenhouse:acme", "Acme", title, location, text,
                     "https://example.com/1", CTX["captured_at"], tag=tag)


@pytest.mark.parametrize("title,expected", [
    ("Senior Product Manager, AI", True), ("Group Product Manager", True), ("Head of Product", True),
    ("AI PM", True), ("Product Marketing Manager", False), ("Product Manager Intern", False),
    ("Program Manager", False), ("Head of Product Communications", False), ("Software Engineer", False), ("Product Designer", False)])
def test_pm_title_filter(title, expected):
    assert p.is_pm_title(title) is expected


@pytest.mark.parametrize("location,expected", [
    ("", True), ("San Francisco, CA", True), ("New York City, NY", True), ("Remote - US", True),
    ("Remote", True), ("United States", True), ("Remote - Europe", False), ("London, UK", False),
    ("Toronto, Canada", False), ("Berlin, BE, DE / Remote", False), ("Worldwide", True)])
def test_us_or_unknown_location(location, expected):
    assert p.us_or_unknown(location) is expected


def test_ai_pm_needs_ai_signal_or_ai_company():
    assert p.ai_pm_match(posting())
    assert not p.ai_pm_match(posting(title="Product Manager, Billing", text="Invoices and tax."))
    assert p.ai_pm_match(posting(title="Product Manager, Billing", text="Invoices.", tag="ai"))
    assert not p.ai_pm_match(posting(location="London, UK"))
    assert not p.ai_pm_match(posting(title="Software Engineer, AI"))
    assert p.ai_pm_match(posting(title="Product Manager", text="Work on machine learning ranking."))
    assert not p.ai_pm_match(posting(title="Product Manager", text="We maintain facilities."))


def test_html_is_cleaned_and_hidden_text_dropped():
    html = "<p>Hello <b>world</b></p><script>alert(1)</script><div style='display: none'>IGNORE ME</div>"
    assert p.clean_html(html) == "Hello world"


def test_greenhouse_lever_ashby_parse_and_quarantine_bad_items():
    gh = {"jobs": [{"id": 5, "title": "PM", "location": {"name": "Remote"}, "content": "&lt;p&gt;hi&lt;/p&gt;",
                    "absolute_url": "https://example.com/5"}, {"id": "bad"}]}
    jobs, rejected, total = p.parse_greenhouse(gh, CTX)
    assert (jobs[0].job_id, jobs[0].text, rejected, total) == ("greenhouse:acme:5", "hi", 1, 2)
    lever = [{"id": "abc-1", "text": "PM", "categories": {"location": "NYC"}, "descriptionPlain": "Do things",
              "hostedUrl": "https://jobs.lever.co/acme/abc-1"}]
    assert p.parse_lever(lever, CTX)[0][0].job_id == "lever:acme:abc-1"
    ashby = {"jobs": [{"id": "x1", "title": "PM", "location": "NYC", "descriptionPlain": "Do", "isListed": True,
                       "jobUrl": "https://jobs.ashbyhq.com/acme/x1"},
                      {"id": "x2", "title": "Hidden", "isListed": False}]}
    jobs, rejected, total = p.parse_ashby(ashby, CTX)
    assert [j.job_id for j in jobs] == ["ashby:acme:x1"] and total == 1


def test_duplicate_ids_fail_the_source():
    data = [{"id": "same", "text": "PM", "descriptionPlain": "x", "hostedUrl": "https://example.com/a"}] * 2
    with pytest.raises(ValueError, match="duplicate_source_id"):
        p.parse_lever(data, CTX)


def test_aggregators_parse():
    ctx = CTX | {"source_id": "agg"}
    remotive = {"jobs": [{"id": 1, "title": "PM", "company_name": "Co", "candidate_required_location": "USA",
                          "description": "<p>x</p>", "url": "https://remotive.com/1", "salary": "$100k"}]}
    assert p.parse_remotive(remotive, ctx)[0][0].salary == "$100k"
    ok = [{"legal": "notice"}, {"id": "9", "position": "PM", "company": "Co", "description": "x",
                                 "url": "https://remoteok.com/9", "salary_min": 100000, "salary_max": 150000}]
    job = p.parse_remoteok(ok, ctx)[0][0]
    assert (job.job_id, job.salary, job.location) == ("remoteok:9", "100,000 - 150,000", "Remote")
    muse = {"results": [{"id": 3, "name": "PM", "company": {"name": "Co"}, "locations": [{"name": "NYC"}],
                         "contents": "<p>y</p>", "refs": {"landing_page": "https://themuse.com/3"}}]}
    assert p.parse_themuse(muse, ctx)[0][0].location == "NYC"
    jobicy = {"jobs": [{"id": 4, "jobTitle": "PM", "companyName": "Co", "jobGeo": "USA",
                        "jobDescription": "<p>z</p>", "url": "https://jobicy.com/4"}]}
    assert p.parse_jobicy(jobicy, ctx)[0][0].job_id == "jobicy:4"
    him = {"jobs": [{"guid": "g-1", "title": "PM", "companyName": "Co", "locationRestrictions": ["US"],
                     "description": "<p>w</p>", "applicationLink": "https://himalayas.app/1"}]}
    assert p.parse_himalayas(him, ctx)[0][0].location == "US"
    rss = ("<rss><channel><item><title>Legion: Principal Product Manager, Agentic AI</title>"
           "<link>https://weworkremotely.com/jobs/1</link><description>&lt;p&gt;agentic&lt;/p&gt;</description>"
           "</item></channel></rss>")
    job = p.parse_wwr_rss(rss, ctx)[0][0]
    assert (job.company, job.title) == ("Legion", "Principal Product Manager, Agentic AI")


def test_listing_only_counters():
    html = ('<div data-page="{&quot;props&quot;:{&quot;jobPostings&quot;:[{&quot;title&quot;:&quot;Product '
            'Manager&quot;},{&quot;title&quot;:&quot;Designer&quot;}]}}"></div>')
    assert p.count_yc(html, CTX) == {"listed": 2, "pm_titles": 1}
    hn = {"hits": [{"title": "Ask HN: Who is hiring? (October 2026)", "num_comments": 393}]}
    assert p.count_hn(hn, CTX)["listed"] == 393
    with pytest.raises(ValueError):
        p.count_hn({"hits": []}, CTX)


def test_row_is_deterministic_and_excerpt_is_exact_prefix():
    text = "Build AI agents. " * 40
    row = p.to_row(posting(text=text, tag="ai"))
    assert row["Brief description"] == text[:300].rstrip() and text.startswith(row["Brief description"])
    assert (row["Rank (prelim)"], row["Status"], row["Notes"], row["My rating"]) == (1, "New", "", "")
    assert set(row) == set(__import__("jobhunter.sheet_records", fromlist=["JOB_HEADERS"]).JOB_HEADERS)
    json.dumps(row)
