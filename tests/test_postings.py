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
    ("Toronto, Canada", False), ("Berlin, BE, DE / Remote", False), ("Worldwide", True), ("Bengaluru, KA, IN / Bengaluru, KA, IN", False), ("Chicago, IL, US", True),
    ("Mumbai", False)])
def test_us_or_unknown_location(location, expected):
    assert p.us_or_unknown(location) is expected


@pytest.mark.parametrize('location', ['South America', 'Latin America', 'Remote - South America'])
def test_ambiguous_america_regions_are_not_assumed_to_allow_us(location):
    assert not p.us_or_unknown(location)


def test_explicit_us_option_is_retained_alongside_foreign_locations():
    assert p.us_or_unknown('United States or Latin America')


@pytest.mark.parametrize('location', ['Remote - South America', 'Latin America (Remote)', 'LATAM remote'])
def test_remote_south_and_latin_america_roles_are_kept_without_salary(location):
    assert p.ai_pm_match(posting(location=location))


@pytest.mark.parametrize('location,salary,expected', [
    ('Colombia', 'USD 70,000 per year', True),
    ('Dominican Republic', 'US$ 70k annually', True),
    ('República Dominicana', '60,000 - 80,000 USD / year', True),
    ('Colombia', 'USD 69,999 annually', False),
    ('Colombia', 'COP 70,000,000 annually', False),
    ('Dominican Republic', 'DOP 100,000 annually', False),
    ('Colombia', 'USD 70,000 monthly', False),
    ('Colombia', 'USD 70,000', False),
    ('Colombia', '$70,000 annually', False),
    ('Colombia', 'USD 100,000 total compensation annually', False),
    ('Brazil', 'USD 100,000 annually', False),
    ('Remote - Brazil', '', True),
    ('Colombia (Hybrid)', '', False),
    ('Costa Rica (Hybrid)', '', False),
    ('Bogotá, DC, Colombia', '', False),
    ('Bogota, D.C., Colombia', 'USD 69,999 annually', False),
    ('Bogotá, DC, Colombia', 'USD 70,000 annually', True),
    ('Colombia or United States', '', True),
    ('Albuquerque, New Mexico', '', True),
    ('Panama City, FL', '', True),
    ('Mexico, MO', '', True),
    ('Peru, IL', '', True),
    ('Colombia, DC', '', False),
    ('Colombia, CO', '', False),
    ('Argentina, AR', '', False),
    ('Panama, PA', '', False),
    ('Panama City, FL 32401', '', True),
    ('Panama City, FL (Hybrid)', '', True),
    ('Mexico, Missouri', '', True),
    ('Peru, Pennsylvania', '', True),
    ('Panama City, FL, Panama', '', False),
    ('Panama City, FL - Hybrid', '', True),
    ('Panama City, FL / On-site', '', True),
    ('Mexico, MO (Hybrid/Remote)', '', True),
])
def test_regional_roles_follow_remote_or_country_and_annual_usd_salary_preference(location, salary, expected):
    from dataclasses import replace
    assert p.ai_pm_match(replace(posting(location=location), salary=salary)) is expected


def test_salary_amount_can_end_in_sentence_punctuation():
    assert p.regional_salary_match('Annual salary: USD 80,000.')


def test_explicit_annual_period_token_with_underscore_is_supported():
    assert p.regional_salary_match('USD 80,000 per_year')


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


@pytest.mark.parametrize('fields', [
    {'lists': [{'text': 'Responsibilities', 'content': '<li>Lead the AI platform roadmap.</li>'}]},
    {'additionalPlain': 'Lead the AI platform roadmap.'},
    {'additional': '<p>Lead the AI platform roadmap.</p>'},
])
def test_lever_ai_signal_in_description_sections_is_used_for_filtering(fields):
    data = [{'id': 'role-1', 'text': 'Product Manager', 'categories': {'location': 'United States'},
             'descriptionPlain': 'Join our product team.', 'hostedUrl': 'https://example.com/jobs/role-1', **fields}]
    jobs, rejected, _ = p.parse_lever(data, CTX)
    assert rejected == 0
    assert 'Lead the AI platform roadmap.' in jobs[0].text
    assert p.ai_pm_match(jobs[0])


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


YC_LISTING = ('<div data-page="{&quot;props&quot;:{&quot;jobPostings&quot;:[{&quot;id&quot;:7,&quot;title&quot;:'
              '&quot;Product Manager, AI&quot;,&quot;url&quot;:&quot;/companies/acme/jobs/abc-pm&quot;,&quot;location&quot;:'
              '&quot;San Francisco, CA&quot;,&quot;companyName&quot;:&quot;Acme&quot;,&quot;salaryRange&quot;:'
              '&quot;$150K - $200K&quot;},{&quot;title&quot;:&quot;broken, no id&quot;}]}}"></div>')
YC_DETAIL = ('<script type="application/ld+json">{"@type":"JobPosting","description":'
             '"\\u003cp\\u003eBuild AI agents.\\u003c/p\\u003e"}</script>')


def test_yc_stubs_and_detail_description():
    stubs, rejected = p.stubs_yc(YC_LISTING, {"source_id": "yc-product"})
    assert rejected == 1 and stubs == [{"job_id": "yc-product:7", "company": "Acme", "title": "Product Manager, AI",
        "location": "San Francisco, CA", "url": "https://www.ycombinator.com/companies/acme/jobs/abc-pm",
        "salary": "$150K - $200K", "posted_at": ""}]
    assert p.detail_yc(YC_DETAIL) == {"text": "Build AI agents.", "posted_at": ""}
    assert p.detail_yc("<html>no structured data</html>") == {"text": "", "posted_at": ""}


def test_getro_stubs_and_detail_description():
    state = {"props": {"pageProps": {"initialState": {"jobs": {"found": [
        {"id": 5, "slug": "5-pm", "title": "Product Manager", "organization": {"name": "Co", "slug": "co-1"},
         "locations": ["New York, NY"], "compensationAmountMinCents": 15000000, "compensationAmountMaxCents": 20000000,
         "compensationCurrency": "USD", "compensationPeriod": "year"}, {"id": 6}],
        "currentJob": {"description": "<p>Agents.</p>"}}}}}}
    page = f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(state)}</script>'
    stubs, rejected = p.stubs_getro(page, {"source_id": "getro-accel", "url": "https://jobs.accel.com/jobs?q=x"})
    assert rejected == 1 and stubs[0]["url"] == "https://jobs.accel.com/companies/co-1/jobs/5-pm"
    assert (stubs[0]["job_id"], stubs[0]["salary"]) == ("getro-accel:5", "150,000 - 200,000 USD year")
    assert p.detail_getro(page) == {"text": "Agents.", "posted_at": ""}


BUILTIN_LIST = ('<script type="application/ld&#x2B;json">{"@graph":[{"@type":"ItemList","itemListElement":['
                '{"name":"Principal Product Manager, AI","url":"https://builtin.com/job/principal-product-manager-ai/11735619",'
                '"description":"short"},{"name":"bad","url":"https://builtin.com/not-a-job"}]}]}</script>')
BUILTIN_JOB = ('<script type="application/ld&#x2B;json">{"@context":"https://schema.org","@type":"JobPosting",'
               '"description":"<p>Lead AI roadmap.</p>","hiringOrganization":{"name":"Expedia Group"},'
               '"jobLocation":{"address":{"addressLocality":"Seattle","addressRegion":"Washington","addressCountry":"USA"}},'
               '"baseSalary":{"currency":"USD","value":{"minValue":150000,"maxValue":200000,"unitText":"YEAR"}}}</script>')


def test_builtin_listing_and_job_page():
    stubs, rejected = p.stubs_builtin(BUILTIN_LIST, {"source_id": "builtin-product"})
    assert rejected == 1 and stubs[0]["job_id"] == "builtin-product:11735619"
    assert p.detail_builtin(BUILTIN_JOB) == {"text": "Lead AI roadmap.", "company": "Expedia Group", "posted_at": "",
        "location": "Seattle, Washington, USA", "salary": "150,000 - 200,000 USD YEAR"}
    assert p.detail_builtin("<html></html>")["text"] == ""


@pytest.mark.parametrize('currency', ['COP', 'DOP', ''])
def test_builtin_salary_keeps_source_currency_instead_of_assuming_usd(currency):
    data = {'@type': 'JobPosting', 'description': 'Build AI.',
            'baseSalary': {'currency': currency, 'value': {'minValue': 70000, 'unitText': 'YEAR'}}}
    detail = p.detail_builtin('<script type="application/ld+json">' + json.dumps(data) + '</script>')
    assert 'USD' not in detail['salary']
    if currency:
        assert currency in detail['salary']


def test_explicit_ashby_remote_flag_keeps_regional_remote_role_with_original_location():
    data = {'jobs': [{'id': 'remote-1', 'title': 'Product Manager, AI', 'location': 'Colombia',
                     'descriptionPlain': 'Build AI products.', 'jobUrl': 'https://example.com/remote-1',
                     'isRemote': True}]}
    job = p.parse_ashby(data, CTX)[0][0]
    assert p.ai_pm_match(job)
    assert p.to_row(job)['Location'] == 'Colombia'


@pytest.mark.parametrize('kind,data', [
    ('remotive', {'jobs': [{'id': 1, 'title': 'Product Manager, AI', 'company_name': 'Acme',
                           'candidate_required_location': 'Brazil', 'description': 'Build AI.',
                           'url': 'https://example.com/jobs/1'}]}),
    ('remoteok', [{'id': 1, 'position': 'Product Manager, AI', 'company': 'Acme', 'location': 'Brazil',
                   'description': 'Build AI.', 'url': 'https://example.com/jobs/1'}]),
    ('himalayas', {'jobs': [{'guid': '1', 'title': 'Product Manager, AI', 'companyName': 'Acme',
                            'locationRestrictions': ['Brazil'], 'description': 'Build AI.',
                            'applicationLink': 'https://example.com/jobs/1'}]}),
    ('jobicy', {'jobs': [{'id': 1, 'jobTitle': 'Product Manager, AI', 'companyName': 'Acme',
                         'jobGeo': 'Brazil', 'jobDescription': 'Build AI.', 'url': 'https://example.com/jobs/1'}]}),
])
def test_remote_only_board_contract_keeps_regional_remote_jobs(kind, data):
    job = p.PARSERS[kind](data, CTX)[0][0]
    assert p.ai_pm_match(job)
    assert p.to_row(job)['Location'] == 'Brazil'


def test_listing_only_counters():
    hn = {"hits": [{"title": "Ask HN: Who is hiring? (October 2026)", "num_comments": 393}]}
    assert p.count_hn(hn, CTX)["listed"] == 393
    with pytest.raises(ValueError):
        p.count_hn({"hits": []}, CTX)


def make(job_id, source, url, title="Senior Product Manager, AI", company="Acme"):
    return p.Posting(job_id, source, company, title, "Remote", "Build AI.", url, CTX["captured_at"])


@pytest.mark.parametrize("url,key", [
    ("https://job-boards.greenhouse.io/Acme/jobs/123?gh_src=x", "greenhouse:acme:123"),
    ("https://boards.greenhouse.io/acme/jobs/123", "greenhouse:acme:123"),
    ("https://jobs.lever.co/acme/7a8b9c0d-1111-2222-3333-444455556666", "lever:acme:7a8b9c0d-1111-2222-3333-444455556666"),
    ("https://jobs.ashbyhq.com/acme/7a8b9c0d-1111-2222-3333-444455556666/application", "ashby:acme:7a8b9c0d-1111-2222-3333-444455556666"),
    ("https://Example.com/jobs/1/?utm_source=x#top", "https://example.com/jobs/1")])
def test_canonical_keys(url, key):
    assert p.canonical_key(url) == key


@pytest.mark.parametrize('left,right', [
    ('https://example.com/jobs/ABC', 'https://example.com/jobs/abc'),
    ('https://example.com/jobs?Req=1', 'https://example.com/jobs?req=1'),
    ('https://example.com:8443/jobs/1', 'https://example.com/jobs/1'),
])
def test_canonical_identity_preserves_case_sensitive_components_and_ports(left, right):
    assert p.canonical_key(left) != p.canonical_key(right)
    assert len(p.dedupe([make('one:1', 'one', left), make('two:2', 'two', right)])) == 2


def test_dedupe_merges_identical_employer_links_and_prefers_company_boards():
    board = make("greenhouse:acme:123", "greenhouse:acme", "https://job-boards.greenhouse.io/acme/jobs/123")
    aggregator = make("remotive:9", "remotive", "https://boards.greenhouse.io/acme/jobs/123?src=remotive")
    kept = p.dedupe([aggregator, board])
    assert [(posting.job_id, note) for posting, note in kept] == [("greenhouse:acme:123",
        "Also listed by: remotive\nFirst seen by remotive: 2026-10-18T00:00:00+00:00")]


def test_shared_custom_links_retain_distinct_requisitions_for_review():
    first = make('remotive:1', 'remotive', 'https://example.com/careers', title='PM, AI Search')
    others = [make(f'himalayas:{n}', 'himalayas', 'https://example.com/careers', title=f'PM, AI {n}')
              for n in (1, 2)]
    kept = p.dedupe([first, *others])
    assert [job.job_id for job, note in kept] == ['remotive:1', 'himalayas:1', 'himalayas:2']
    assert all('Possible duplicate of remotive:1' in note and 'needs review' in note
               for job, note in kept[1:])


def test_custom_greenhouse_application_id_is_verified_for_cross_source_matching():
    a = make('remotive:1', 'remotive', 'https://example.com/careers?gh_jid=111')
    b = make('himalayas:2', 'himalayas', 'https://example.com/careers?gh_jid=111&utm_source=himalayas')
    assert len(p.dedupe([a, b])) == 1


def test_distinct_jobs_sharing_one_careers_page_path_are_not_merged():
    one = make("greenhouse:acme:1", "greenhouse:acme", "https://acme.com/careers/job?gh_jid=111", title="PM, AI Search")
    two = make("greenhouse:acme:2", "greenhouse:acme", "https://acme.com/careers/job?gh_jid=222", title="PM, AI Ads")
    assert [n for _, n in p.dedupe([one, two])] == ["", ""]
    assert p.canonical_key("https://acme.com/careers/job?gh_jid=111&utm_source=x") == "https://acme.com/careers/job?gh_jid=111"


def test_a_source_never_merges_its_own_postings():
    a = make("remotive:1", "remotive", "https://example.com/apply", title="PM, AI Search")
    b = make("remotive:2", "remotive", "https://example.com/apply", title="PM, AI Ads")
    assert len(p.dedupe([a, b])) == 2


def test_look_alikes_are_flagged_for_review_never_merged():
    a = make("greenhouse:acme:1", "greenhouse:acme", "https://job-boards.greenhouse.io/acme/jobs/1")
    b = make("remotive:2", "remotive", "https://remotive.com/jobs/2")
    kept = p.dedupe([a, b])
    assert len(kept) == 2 and kept[0][1] == ""
    assert kept[1][1].startswith("Possible duplicate of greenhouse:acme:1") and "needs review" in kept[1][1]
    assert "needs review" in p.to_row(*kept[1])["More details"]


def test_row_is_deterministic_and_excerpt_is_exact_prefix():
    text = "Build AI agents. " * 40
    row = p.to_row(posting(text=text, tag="ai"))
    assert row["Brief description"] == text[:300].rstrip() and text.startswith(row["Brief description"])
    assert (row["Rank (prelim)"], row["Status"], row["Notes"], row["My rating"]) == (1, "New", "", "")
    assert set(row) == set(__import__("jobhunter.sheet_records", fromlist=["JOB_HEADERS"]).JOB_HEADERS)
    json.dumps(row)


@pytest.mark.parametrize('salary,expected', [
    ('USD 50,000 - 60,000 per year + 401k', False),
    ('USD 80,000 per year + 401(k) matching', True),
    ('Annual salary: 50,000 - 60,000 USD; 100000 employees', False),
    ('USD 50,000 - 60,000 per year + USD 100,000 bonus', False),
    ('USD 80,000 per year + USD 100,000 bonus', True),
    ('Annual salary: USD 50,000 - 60,000; bonus USD 100,000', False),
    ('USD $70,000 - $90,000 per year', True),
    ('USD 70,000 - 90,000 a year', True),
    ('USD 80,000 (annual)', True),
    ('USD 80,000 gross per year', True),
    ('USD 50,000 - 60,000 per year + USD 100,000 annual bonus', False),
    ('USD 50,000 - 60,000 per year; Annual bonus: USD 100,000', False),
    ('USD 80,000 per year + USD 100,000 annual bonus', True),
    ('USD 50,000 per year, bonus up to USD 100,000 per year', False),
    ('USD 120,000 per year benefits included', True),
    ('USD 50,000 per year + USD 100,000 annual sign-on bonus', False),
    ('USD 50,000 per year; annual bonus (target): USD 100,000 per year', False),
    ('USD 80,000 per year, bonus up to USD 100,000 per year', True),
])
def test_regional_salary_uses_currency_linked_amounts_only(salary, expected):
    assert p.regional_salary_match(salary) is expected


@pytest.mark.parametrize('workplace,remote', [('remote', True), ('hybrid', False), ('on-site', False), ('', False)])
def test_lever_preserves_explicit_remote_workplace_type(workplace, remote):
    data = [{'id': 'regional-1', 'text': 'Product Manager, AI',
             'categories': {'location': 'Latin America'}, 'workplaceType': workplace,
             'descriptionPlain': 'Build AI products.', 'hostedUrl': 'https://jobs.lever.co/acme/regional-1'}]
    job = p.parse_lever(data, CTX | {'source_id': 'lever:acme'})[0][0]
    assert job.remote is remote
    assert p.ai_pm_match(job) is remote
    row = p.to_row(job)
    assert row['Location'] == 'Latin America' and row['Fit'] == ''
    assert ('Work mode: Remote (source metadata)' in row['More details']) is remote


def test_wwr_remote_feed_keeps_regional_location_without_salary():
    rss = ('<rss><channel><item><title>Acme: Product Manager, AI</title>'
           '<link>https://weworkremotely.com/jobs/regional-1</link><region>Costa Rica</region>'
           '<description>Build AI products.</description></item></channel></rss>')
    job = p.parse_wwr_rss(rss, CTX | {'source_id': 'weworkremotely'})[0][0]
    assert job.remote and p.ai_pm_match(job)
    row = p.to_row(job)
    assert row['Location'] == 'Costa Rica' and row['Fit'] == ''
    assert 'Work mode: Remote (source metadata)' in row['More details']


JS_ITEM = {"job_id": "abc123==", "employer_name": "Acme", "job_title": "AI Product Manager",
           "job_description": "<p>Build <b>agents</b>.</p>", "job_apply_link": "https://acme.test/apply/1",
           "job_google_link": "https://www.google.com/search?q=1", "job_city": "Austin", "job_state": "TX",
           "job_country": "US", "job_is_remote": False, "job_min_salary": 150000.0, "job_max_salary": 190000,
           "job_salary_currency": "USD", "job_salary_period": "YEAR",
           "job_posted_at_datetime_utc": "2026-10-15T00:00:00.000Z"}
JS_CTX = {**CTX, "source_id": "jsearch"}


def test_parse_jsearch_maps_fields():
    postings, rejected, total = p.parse_jsearch({"status": "OK", "data": [JS_ITEM]}, JS_CTX)
    assert (rejected, total) == (0, 1)
    job = postings[0]
    assert job.job_id == f"jsearch:{p._digest('abc123==')}" and job.source_id == "jsearch"
    assert (job.company, job.title, job.location) == ("Acme", "AI Product Manager", "Austin, TX, US")
    assert job.text == "Build agents ."
    assert job.apply_url == "https://acme.test/apply/1" and job.salary == "150,000 - 190,000 USD YEAR"
    assert job.tag == "other" and job.remote is False
    assert p.ai_pm_match(job)


def test_parse_jsearch_remote_keeps_place_and_falls_back_to_google_link():
    item = {**JS_ITEM, "job_is_remote": True, "job_apply_link": "http://insecure.test/1",
            "job_city": None, "job_state": None, "job_min_salary": None, "job_max_salary": None}
    job = p.parse_jsearch({"data": [item]}, JS_CTX)[0][0]
    assert job.apply_url == "https://www.google.com/search?q=1"
    assert job.location == "Remote, US" and job.remote is True and job.salary == ""
    assert p.ai_pm_match(job)
    bare = p.parse_jsearch({"data": [{**item, "job_country": None}]}, JS_CTX)[0][0]
    assert bare.location == "Remote" and p.ai_pm_match(bare)
    # A remote flag must not turn a non-US job into a US-eligible one: the structured country decides.
    for country, city in (("DE", "Berlin"), ("EE", "Tallinn"), ("IN", "Pune")):
        for remote in (True, False):
            foreign = {**item, "job_is_remote": remote, "job_city": city, "job_state": None, "job_country": country}
            postings, rejected, total = p.parse_jsearch({"data": [foreign, JS_ITEM]}, JS_CTX)
            assert [job.job_id for job in postings] == [p.parse_jsearch({"data": [JS_ITEM]}, JS_CTX)[0][0].job_id]
            assert (rejected, total) == (0, 2)  # skipped, not counted as a broken item
    # Latin American countries keep their regional rule, using the country name.
    latam = p.parse_jsearch({"data": [{**item, "job_city": "Bogota", "job_country": "co"}]}, JS_CTX)[0][0]
    assert latam.location == "Remote, Bogota, Colombia" and p.ai_pm_match(latam)


@pytest.mark.parametrize("change", [
    {"job_apply_link": "http://insecure.test/1", "job_google_link": None},
    {"job_apply_link": None, "job_google_link": "ftp://x.test/1"},
    {"job_apply_link": "javascript:alert(1)", "job_google_link": ""},
    {"job_id": None}, {"job_id": ""}, {"job_title": None}, {"employer_name": None}, {"job_description": None},
])
def test_parse_jsearch_rejects_unusable_items_without_dropping_the_rest(change):
    good = {**JS_ITEM, "job_id": "good"}
    postings, rejected, total = p.parse_jsearch({"data": [{**JS_ITEM, **change}, good]}, JS_CTX)
    assert (len(postings), rejected, total) == (1, 1, 2)


def test_parse_jsearch_tolerates_a_sparse_item_and_rejects_bad_envelopes():
    sparse = {"job_id": "x", "employer_name": "Acme", "job_title": "Product Manager",
              "job_description": "AI work", "job_google_link": "https://www.google.com/x"}
    job = p.parse_jsearch({"data": [sparse]}, JS_CTX)[0][0]
    assert job.location == "" and job.salary == ""
    for bad in ({"status": "ERROR", "data": []}, {"data": None}, [], {}):
        with pytest.raises(ValueError, match="invalid_board_response"):
            p.parse_jsearch(bad, JS_CTX)


JB_ITEM = {"id": 8374920193, "title": "Senior <b>Product</b> <b>Manager</b>, AI", "location": "New York, NY",
           "snippet": "&nbsp;...build <b>LLM</b> features...", "salary": "$160k - $200k", "source": "acme.test",
           "type": "Full-time", "link": "https://jooble.org/desc/8374920193", "company": "Acme",
           "updated": "2026-10-16T00:00:00.0000000"}
JB_CTX = {**CTX, "source_id": "jooble"}


def test_parse_jooble_maps_fields_and_strips_highlight_markup():
    postings, rejected, total = p.parse_jooble({"totalCount": 1, "jobs": [JB_ITEM]}, JB_CTX)
    assert (rejected, total) == (0, 1)
    job = postings[0]
    assert job.job_id == "jooble:8374920193" and job.source_id == "jooble"
    assert job.title == "Senior Product Manager , AI"
    assert "<" not in job.text and "LLM" in job.text
    assert (job.company, job.location, job.salary) == ("Acme", "New York, NY", "$160k - $200k")
    assert job.remote is False and job.tag == "other" and p.ai_pm_match(job)


def test_parse_jooble_ids_and_rejections():
    items = [{**JB_ITEM, "id": -42}, {**JB_ITEM, "id": "not/a plain id"},
             {**JB_ITEM, "id": None, "link": "https://jooble.org/desc/x"},
             {**JB_ITEM, "id": 3, "link": "http://insecure.test/3"}, {**JB_ITEM, "id": 4, "link": None},
             {**JB_ITEM, "id": 5, "company": None}, {**JB_ITEM, "id": 6, "snippet": None}]
    postings, rejected, total = p.parse_jooble({"jobs": items}, JB_CTX)
    assert (total, rejected) == (7, 4)
    ids = [job.job_id for job in postings]
    assert ids[0] == "jooble:-42"
    assert ids[1] == f"jooble:{p._digest('not/a plain id')}" and ids[2] == f"jooble:{p._digest('https://jooble.org/desc/x')}"
    for bad in ({"jobs": None}, [], {}):
        with pytest.raises(ValueError, match="invalid_board_response"):
            p.parse_jooble(bad, JB_CTX)


def test_jsearch_v2_nested_response_with_null_salary_fields():
    # Shape seen live from /search-v2: jobs under data.jobs, salary fields null, no currency key.
    v2_item = {**JS_ITEM, "job_min_salary": None, "job_max_salary": None, "job_salary_period": None}
    v2_item.pop("job_salary_currency", None)
    postings, rejected, total = p.parse_jsearch(
        {"status": "OK", "request_id": "r", "parameters": {}, "data": {"cursor": "c", "jobs": [v2_item]}}, JS_CTX)
    assert (total, rejected, len(postings)) == (1, 0, 1)
    assert postings[0].salary == ""
    with pytest.raises(ValueError):
        p.parse_jsearch({"status": "OK", "data": {"cursor": "c"}}, JS_CTX)
