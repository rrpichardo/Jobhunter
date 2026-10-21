"""Pay that a source publishes must reach the Salary column (the Anthropic California rows were blank)."""
import pytest

from jobhunter import postings as p
from mba_fixtures import mba
from scripts import source_probe

CTX = {"board": "acme", "company": "Acme", "tag": "ai", "source_id": "greenhouse:acme",
       "captured_at": "2026-10-21T00:00:00+00:00"}


def gh_job(ranges, **changes):
    return {"id": 1, "title": "Product Manager, Billing", "location": {"name": "San Francisco, CA | New York City, NY"},
            "content": mba("Own billing."), "absolute_url": "https://job-boards.greenhouse.io/acme/jobs/1",
            "pay_input_ranges": ranges} | changes


ANTHROPIC_STYLE = [{"min_cents": 30500000, "max_cents": 38500000, "currency_type": "USD", "title": "Annual Salary:",
                    "blurb": "<p>The annual compensation range for this role is listed below.</p>"}]


def test_greenhouse_pay_ranges_fill_the_salary_cell_and_the_pay_filter_can_read_it():
    postings, rejected, _ = p.parse_greenhouse({"jobs": [gh_job(ANTHROPIC_STYLE)]}, CTX)
    assert rejected == 0 and postings[0].salary == "305,000 - 385,000 USD year"
    assert p.annual_usd_salary_ceiling(postings[0].salary) == 385000
    row = p.to_row(postings[0])
    assert row["Salary"] == "305,000 - 385,000 USD year" and "Salary preference: satisfied" in row["More details"]


def test_a_posting_with_zone_tiers_becomes_one_merged_range():
    zones = [{"min_cents": 12800000, "max_cents": 17600000, "currency_type": "USD", "title": "Zone 1 Pay Range"},
             {"min_cents": 11520000, "max_cents": 15840000, "currency_type": "USD", "title": "Zone 2 Pay Range"}]
    assert p.greenhouse_pay(zones) == "115,200 - 176,000 USD year"


@pytest.mark.parametrize("ranges,expected", [
    ([{"min_cents": 4000, "max_cents": 6000, "currency_type": "USD", "title": "Hourly Rate:"}], "40 - 60 USD hour"),
    ([{"min_cents": 8500000, "max_cents": 10000000, "currency_type": "CAD", "title": "Canada Pay Range"}], "85,000 - 100,000 CAD year"),
    ([{"min_cents": 9000000, "max_cents": 12000000, "currency_type": "USD", "title": "OTE Range"}], "90,000 - 120,000 USD OTE"),
    # a yearly USD range beats a Canadian one on the same posting
    ([{"min_cents": 8500000, "max_cents": 10000000, "currency_type": "CAD", "title": "CAN"},
      {"min_cents": 15000000, "max_cents": 20000000, "currency_type": "USD", "title": "US based applicants only"}],
     "150,000 - 200,000 USD year"),
    ([], ""), (None, ""), ("junk", ""), ([{"min_cents": None, "max_cents": None, "currency_type": "USD"}], ""), ([None], ""),
])
def test_other_greenhouse_pay_shapes(ranges, expected):
    assert p.greenhouse_pay(ranges) == expected


@pytest.mark.parametrize("salary", ["40 - 60 USD hour", "85,000 - 100,000 CAD year", "90,000 - 120,000 USD OTE"])
def test_pay_that_is_not_yearly_usd_stays_unresolved_instead_of_being_dropped_or_trusted(salary):
    assert p.annual_usd_salary_ceiling(salary) is None


ASHBY_COMPENSATION = {"summaryComponents": [
    {"compensationType": "EquityPercentage", "interval": "NONE", "currencyCode": None, "minValue": None, "maxValue": None},
    {"compensationType": "Commission", "interval": "1 YEAR", "currencyCode": "USD", "minValue": None, "maxValue": None},
    {"compensationType": "Salary", "interval": "1 YEAR", "currencyCode": "USD", "minValue": 160000, "maxValue": 300000}]}


def test_ashby_salary_component_fills_the_salary_cell():
    data = {"jobs": [{"id": "a1", "title": "Product Manager", "location": "San Francisco, CA", "isListed": True,
                      "descriptionPlain": mba("Build."), "jobUrl": "https://jobs.ashbyhq.com/acme/a1",
                      "compensation": ASHBY_COMPENSATION}]}
    postings, _, _ = p.parse_ashby(data, CTX | {"source_id": "ashby:acme"})
    assert postings[0].salary == "160,000 - 300,000 USD year"


def test_ashby_without_compensation_is_blank_not_an_error():
    assert p.ashby_pay(None) == "" and p.ashby_pay({"summaryComponents": [{"compensationType": "Bonus"}]}) == ""


@pytest.mark.parametrize("text,expected", [
    ("The estimated salary range for this position is $135,000 - $200,000/year. Total compensation may include equity.",
     "135,000 - 200,000 USD year"),
    ("San Francisco Estimated Base salary $161,000 - $221,000. New York Estimated Base salary $153,000 - $210,000.",
     "153,000 - 221,000 USD year"),
    ("The annual base pay range is $160K to $200K plus bonus.", "160,000 - 200,000 USD year"),
    ("Hourly pay: $40 - $60 per hour.", ""),                                   # too small and hourly
    ("The salary range is $45,000 - $60,000 per month.", ""),                  # monthly
    ("Target bonus of $20,000 - $40,000 on top of salary.", ""),               # a bonus is not base pay
    ("We offer a $5,000 - $10,000 relocation allowance and a salary that is competitive.", ""),
    ("The salary range is CAD $90,000 - $120,000.", ""),                       # another currency
    ("Join 10,000 - 50,000 employees worldwide.", ""),                          # no dollar sign, no pay word
    ("", ""), (None, ""),
])
def test_pay_written_in_the_posting_is_read_narrowly(text, expected):
    assert p.salary_from_text(text) == expected


def test_the_text_fallback_fills_rows_from_sources_without_a_pay_field_and_does_not_overwrite_a_published_one():
    lever = [{"id": "l1", "text": "Product Manager", "categories": {"location": "New York, NY"},
              "descriptionPlain": mba("The salary range for this role is $150,000 - $190,000."),
              "hostedUrl": "https://jobs.lever.co/acme/l1"}]
    assert p.parse_lever(lever, CTX | {"source_id": "lever:acme"})[0][0].salary == "150,000 - 190,000 USD year"
    gh = {"jobs": [gh_job(ANTHROPIC_STYLE, content=mba("The salary range is $100,000 - $120,000."))]}
    assert p.parse_greenhouse(gh, CTX)[0][0].salary == "305,000 - 385,000 USD year"


def test_published_pay_below_the_floor_drops_the_job_with_that_reason():
    cheap = [{"min_cents": 6000000, "max_cents": 9000000, "currency_type": "USD", "title": "Annual Salary:"}]
    posting = p.parse_greenhouse({"jobs": [gh_job(cheap)]}, CTX)[0][0]
    assert p.collection_reason(posting) == "pay_below_floor"


def test_the_probe_asks_greenhouse_and_ashby_for_their_pay_fields():
    registry = {"boards": {"greenhouse": [{"board": "acme", "company": "Acme", "tag": "ai"}],
                           "ashby": [{"board": "acme", "company": "Acme", "tag": "ai"}]}}
    urls = {entry["kind"]: entry["url"] for entry in source_probe.entries(registry)}
    assert "pay_transparency=true" in urls["greenhouse"] and "content=true" in urls["greenhouse"]
    assert "includeCompensation=true" in urls["ashby"]


# Codex review of PR 52 (October 21): the label and the whole compensation sentence decide what an amount is.
@pytest.mark.parametrize("text", [
    "The annual base salary range is $90,000 - $120,000 CAD.",          # another currency written after the range
    "Total compensation is $100,000 - $120,000 per year.",              # not base pay
    "The monthly salary range is $40,000 - $50,000.",                   # a monthly amount
    "The weekly pay range is $3,000 - $4,000.",
    "Target total cash compensation is $150,000 - $190,000.",
    "The base salary range is $150,000 - $190,000 EUR.",
])
def test_text_pay_with_another_currency_period_or_type_stays_unresolved(text):
    assert p.salary_from_text(text) == ""


def test_text_pay_that_is_unresolved_does_not_drop_an_otherwise_matching_job():
    posting = p.parse_lever([{"id": "l9", "text": "Product Manager", "categories": {"location": "New York, NY"},
                              "descriptionPlain": mba("The monthly salary range is $40,000 - $50,000."),
                              "hostedUrl": "https://jobs.lever.co/acme/l9"}], CTX | {"source_id": "lever:acme"})[0][0]
    assert posting.salary == "" and p.collection_reason(posting) == ""


@pytest.mark.parametrize("title,expected", [
    ("Monthly Salary", "10,000 - 15,000 USD month"),
    ("Annual Bonus", "10,000 - 15,000 USD bonus"),
    ("Annual Total Compensation", "10,000 - 15,000 USD total compensation"),
    ("Sign-on bonus", "10,000 - 15,000 USD bonus"),
    ("Weekly Rate", "10,000 - 15,000 USD week"),
    ("Annual Base Salary Range:", "10,000 - 15,000 USD year"),
    ("Annual base salary range (excluding equity and bonus):", "10,000 - 15,000 USD year"),
    ("Zone 1 Pay Range", "10,000 - 15,000 USD year"),
])
def test_greenhouse_labels_decide_what_the_amount_is(title, expected):
    ranges = [{"min_cents": 1000000, "max_cents": 1500000, "currency_type": "USD", "title": title}]
    assert p.greenhouse_pay(ranges) == expected


@pytest.mark.parametrize("title", ["Monthly Salary", "Annual Bonus", "Annual Total Compensation"])
def test_a_greenhouse_amount_that_is_not_yearly_base_pay_is_unresolved_and_does_not_drop_the_job(title):
    ranges = [{"min_cents": 1000000, "max_cents": 1500000, "currency_type": "USD", "title": title}]
    posting = p.parse_greenhouse({"jobs": [gh_job(ranges)]}, CTX)[0][0]
    assert p.annual_usd_salary_ceiling(posting.salary) is None
    assert p.collection_reason(posting) == ""


def test_a_yearly_base_range_wins_over_a_bonus_range_on_the_same_posting():
    ranges = [{"min_cents": 1000000, "max_cents": 2000000, "currency_type": "USD", "title": "Annual Bonus"},
              {"min_cents": 15000000, "max_cents": 19000000, "currency_type": "USD", "title": "Annual Base Salary Range:"}]
    assert p.greenhouse_pay(ranges) == "150,000 - 190,000 USD year"


def test_the_generic_sales_disclaimer_in_the_blurb_does_not_turn_a_base_range_into_ote():
    blurb = ('<p>The annual compensation range for this role is listed below.</p><p>For sales roles, the range provided is the '
             'role’s On Target Earnings ("OTE") range, meaning that the range includes both commissions and base salary.</p>')
    ranges = [{"min_cents": 30500000, "max_cents": 38500000, "currency_type": "USD", "title": "Annual Salary:", "blurb": blurb}]
    assert p.greenhouse_pay(ranges) == "305,000 - 385,000 USD year"
