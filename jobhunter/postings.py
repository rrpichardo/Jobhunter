"""Multi-source postings: one parser per source, the AI-PM filter, deterministic rows.

Parsers take already-fetched data and never touch the network. Source text is
untrusted: it is cleaned, never executed, and only an exact leading excerpt of it
is stored. Models do not choose any cell value on this path.
"""

from dataclasses import dataclass
from html import unescape
import hashlib
import json
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
import feedparser

from jobhunter.records import https_url

PM_TITLE = re.compile(r"\b(product manager|product lead|group product manager|head of product|"
                      r"director of product|vp of product|vp,? product|pm)\b", re.I)
EXCLUDED_TITLE = re.compile(r"\b(intern|internship|summer associate|product marketing|"
                            r"product designer|product design|product communications|program manager|"
                            r"project manager)\b", re.I)
AI_TERMS = re.compile(r"\b(ai|a\.i\.|ml|llms?|genai|gen ai|generative ai|machine learning|"
                      r"artificial intelligence|agentic|ai agents?|foundation models?|"
                      r"language models?|deep learning)\b", re.I)
US_TERMS = re.compile(r"\b(united states|usa|u\.s\.a?\.?|us|america|new york|nyc|san francisco|"
                      r"sf|bay area|seattle|austin|boston|chicago|los angeles|denver|atlanta|"
                      r"washington|dc|miami|california|texas|massachusetts)\b", re.I)
ANYWHERE = re.compile(r"\b(remote|anywhere|worldwide|global|hybrid)\b", re.I)
NON_US = re.compile(r"\b(europe|emea|apac|asia|latam|canada|mexico|brazil|uk|united kingdom|london|"
                    r"ireland|dublin|germany|berlin|france|paris|spain|netherlands|amsterdam|india|"
                    r"bangalore|singapore|japan|tokyo|australia|sydney|israel|tel aviv|poland|"
                    r"portugal|sweden|switzerland|zurich|dubai|nigeria|kenya|south africa)\b", re.I)
LOCATION_US_CODE = re.compile(r",\s*(?:A[LKZR]|C[AOT]|DE|FL|GA|HI|I[ADLN]|K[SY]|LA|M[ADEINOST]|"
                              r"N[CDEHJMVY]|O[HKR]|PA|RI|S[CD]|T[NX]|UT|V[AT]|W[AIVY]|DC)\b")


@dataclass(frozen=True)
class Posting:
    job_id: str
    source_id: str
    company: str
    title: str
    location: str
    text: str
    apply_url: str
    captured_at: str
    salary: str = ""
    tag: str = "other"  # ai | bigtech | other, from the reviewed registry

    def __post_init__(self):
        for value in (self.job_id, self.source_id, self.company, self.title, self.text):
            if not isinstance(value, str) or not value.strip():
                raise ValueError("invalid_posting_text")
        if (not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9:._~-]{0,300}", self.job_id)
                or not isinstance(self.location, str) or not isinstance(self.salary, str)
                or self.tag not in {"ai", "bigtech", "other"} or not https_url(self.apply_url)):
            raise ValueError("invalid_posting")


def clean_html(markup: str) -> str:
    """Plain text with scripts and visibly hidden markup removed."""
    soup = BeautifulSoup(unescape(markup or ""), "html.parser")
    for tag in soup(["script", "style", "template", "noscript"]):
        tag.decompose()
    for tag in list(soup.find_all()):
        if tag.attrs is None:
            continue
        style = re.sub(r"\s+", "", str(tag.get("style", ""))).lower()
        if (tag.has_attr("hidden") or tag.get("aria-hidden") == "true"
                or "display:none" in style or "visibility:hidden" in style):
            tag.decompose()
    return " ".join(soup.get_text(" ", strip=True).split())


def plain(text: object) -> str:
    return " ".join(text.split()) if isinstance(text, str) else ""


def is_pm_title(title: str) -> bool:
    return bool(PM_TITLE.search(title)) and not EXCLUDED_TITLE.search(title)


def us_or_unknown(location: str) -> bool:
    if not location.strip():
        return True
    if US_TERMS.search(location):  # country or well-known US city: allow even if a non-US place is also listed
        return True
    if NON_US.search(location):  # checked before ambiguous two-letter codes (", DE" is Germany or Delaware)
        return False
    return bool(LOCATION_US_CODE.search(location) or ANYWHERE.search(location))


def ai_pm_match(posting: Posting) -> bool:
    """PLAN filter: PM title and (AI term in title/description or AI-tagged company) and US/unknown."""
    return (is_pm_title(posting.title) and us_or_unknown(posting.location)
            and (posting.tag == "ai" or bool(AI_TERMS.search(posting.title))
                 or bool(AI_TERMS.search(posting.text))))


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:20]


def _collect(items, build):
    postings, rejected, seen = [], 0, set()
    for item in items:
        try:
            posting = build(item)
        except (ValueError, TypeError, AttributeError, KeyError):
            rejected += 1
            continue
        if posting.job_id in seen:
            raise ValueError("duplicate_source_id")
        seen.add(posting.job_id)
        postings.append(posting)
    return postings, rejected


def _salary(low, high, currency="", period=""):
    nums = [n for n in (low, high) if type(n) in (int, float) and n > 0]
    if not nums:
        return ""
    amount = " - ".join(f"{int(n):,}" for n in nums)
    return " ".join(part for part in (amount, str(currency or ""), str(period or "")) if part)


def parse_greenhouse(data, ctx):
    if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
        raise ValueError("invalid_board_response")

    def build(item):
        location = item.get("location") or {}
        if type(item.get("id")) is not int or not isinstance(location, dict):
            raise ValueError
        return Posting(f"greenhouse:{ctx['board']}:{item['id']}", ctx["source_id"], ctx["company"],
                       plain(item.get("title")), plain(location.get("name")), clean_html(item.get("content")),
                       item.get("absolute_url"), ctx["captured_at"], tag=ctx["tag"])
    return (*_collect(data["jobs"], build), len(data["jobs"]))


def parse_lever(data, ctx):
    if not isinstance(data, list):
        raise ValueError("invalid_board_response")

    def build(item):
        categories = item.get("categories") or {}
        text = plain(item.get("descriptionPlain")) or clean_html(item.get("description"))
        return Posting(f"lever:{ctx['board']}:{item['id']}", ctx["source_id"], ctx["company"],
                       plain(item.get("text")), plain(categories.get("location") or ""),
                       text, item.get("hostedUrl"), ctx["captured_at"], tag=ctx["tag"])
    return (*_collect(data, build), len(data))


def parse_ashby(data, ctx):
    if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
        raise ValueError("invalid_board_response")
    listed = [job for job in data["jobs"] if isinstance(job, dict) and job.get("isListed", True)]

    def build(item):
        location = plain(item.get("location")) or ("Remote" if item.get("isRemote") else "")
        text = plain(item.get("descriptionPlain")) or clean_html(item.get("descriptionHtml"))
        return Posting(f"ashby:{ctx['board']}:{item['id']}", ctx["source_id"], ctx["company"],
                       plain(item.get("title")), location, text, item.get("jobUrl"),
                       ctx["captured_at"], tag=ctx["tag"])
    return (*_collect(listed, build), len(listed))


def parse_remotive(data, ctx):
    if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
        raise ValueError("invalid_board_response")

    def build(item):
        return Posting(f"remotive:{item['id']}", ctx["source_id"], plain(item.get("company_name")),
                       plain(item.get("title")), plain(item.get("candidate_required_location")),
                       clean_html(item.get("description")), item.get("url"), ctx["captured_at"],
                       salary=plain(item.get("salary")), tag="other")
    return (*_collect(data["jobs"], build), len(data["jobs"]))


def parse_remoteok(data, ctx):
    if not isinstance(data, list):
        raise ValueError("invalid_board_response")
    jobs = [job for job in data if isinstance(job, dict) and "position" in job]  # first row is a legal notice

    def build(item):
        return Posting(f"remoteok:{item['id']}", ctx["source_id"], plain(item.get("company")),
                       plain(item.get("position")), plain(item.get("location")) or "Remote",
                       clean_html(item.get("description")), item.get("url") or item.get("apply_url"),
                       ctx["captured_at"], salary=_salary(item.get("salary_min"), item.get("salary_max")),
                       tag="other")
    return (*_collect(jobs, build), len(jobs))


def parse_himalayas(data, ctx):
    if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
        raise ValueError("invalid_board_response")

    def build(item):
        restrictions = item.get("locationRestrictions")
        location = ", ".join(map(plain, restrictions)) if isinstance(restrictions, list) else ""
        return Posting(f"himalayas:{_digest(str(item['guid']))}", ctx["source_id"], plain(item.get("companyName")),
                       plain(item.get("title")), location or "Remote",
                       clean_html(item.get("description")) or plain(item.get("excerpt")),
                       item.get("applicationLink"), ctx["captured_at"],
                       salary=_salary(item.get("minSalary"), item.get("maxSalary"), item.get("currency"),
                                      item.get("salaryPeriod")), tag="other")
    return (*_collect(data["jobs"], build), len(data["jobs"]))


def parse_jobicy(data, ctx):
    if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
        raise ValueError("invalid_board_response")

    def build(item):
        geo = item.get("jobGeo")
        return Posting(f"jobicy:{item['id']}", ctx["source_id"], plain(item.get("companyName")),
                       plain(item.get("jobTitle")), plain(", ".join(geo) if isinstance(geo, list) else geo),
                       clean_html(item.get("jobDescription")) or plain(item.get("jobExcerpt")),
                       item.get("url"), ctx["captured_at"],
                       salary=_salary(item.get("salaryMin"), item.get("salaryMax"),
                                      item.get("salaryCurrency"), item.get("salaryPeriod")), tag="other")
    return (*_collect(data["jobs"], build), len(data["jobs"]))


def parse_themuse(data, ctx):
    if not isinstance(data, dict) or not isinstance(data.get("results"), list):
        raise ValueError("invalid_board_response")

    def build(item):
        locations = item.get("locations") or []
        company = item.get("company") or {}
        return Posting(f"themuse:{item['id']}", ctx["source_id"], plain(company.get("name")),
                       plain(item.get("name")), ", ".join(plain(loc.get("name")) for loc in locations),
                       clean_html(item.get("contents")), (item.get("refs") or {}).get("landing_page"),
                       ctx["captured_at"], tag="other")
    return (*_collect(data["results"], build), len(data["results"]))


def parse_wwr_rss(text, ctx):
    feed = feedparser.parse(text)
    if feed.bozo and not feed.entries:
        raise ValueError("invalid_board_response")

    def build(entry):
        title = plain(entry.get("title"))
        company, _, role = title.partition(": ")
        return Posting(f"wwr:{_digest(entry['link'])}", ctx["source_id"], company if role else "Unknown",
                       role or title, plain(entry.get("region")) or "Remote",
                       clean_html(entry.get("summary")), entry.get("link"), ctx["captured_at"], tag="other")
    return (*_collect(feed.entries, build), len(feed.entries))


def _page_json(text):
    match = re.search(r'data-page="([^"]+)"', text)
    if not match:
        raise ValueError("invalid_board_response")
    return json.loads(unescape(match.group(1)))


def count_yc(text, ctx):
    """Listing only: titles, no description text. Counts coverage, delivers nothing."""
    jobs = _page_json(text)["props"]["jobPostings"]
    titles = [plain(j.get("title")) for j in jobs if isinstance(j, dict)]
    return {"listed": len(titles), "pm_titles": sum(is_pm_title(t) for t in titles)}


def count_getro(text, ctx):
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', text, re.S)
    if not match:
        raise ValueError("invalid_board_response")
    jobs = json.loads(match.group(1))["props"]["pageProps"]["initialState"]["jobs"]
    titles = [plain(j.get("title")) for j in jobs["found"] if isinstance(j, dict)]
    return {"listed": len(titles), "pm_titles": sum(is_pm_title(t) for t in titles),
            "total_on_board": jobs.get("total")}


def count_a16z(text, ctx):
    links = set(re.findall(r'href="(/jobs/[a-z0-9-]+/[0-9a-z]+-[^"]+)"', text))
    return {"listed": len(links), "pm_titles": sum(bool(re.search(r"product-manager", link)) for link in links)}


def count_hn(data, ctx):
    hits = [h for h in data.get("hits", []) if isinstance(h, dict)
            and re.match(r"Ask HN: Who is hiring\?", h.get("title") or "")]
    if not hits:
        raise ValueError("invalid_board_response")
    return {"listed": hits[0].get("num_comments") or 0, "pm_titles": 0, "thread": hits[0].get("title")}


PARSERS = {"greenhouse": parse_greenhouse, "lever": parse_lever, "ashby": parse_ashby,
           "remotive": parse_remotive, "remoteok": parse_remoteok, "himalayas": parse_himalayas,
           "jobicy": parse_jobicy, "themuse": parse_themuse, "wwr": parse_wwr_rss}
LISTING_ONLY = {"yc": count_yc, "getro": count_getro, "a16z": count_a16z, "hn": count_hn}


def to_row(posting: Posting) -> dict:
    """Deterministic Jobs row; the description is an exact leading excerpt of source text."""
    quote = posting.text[:300].rstrip()
    rank = {"ai": 1, "bigtech": 2, "other": 3}[posting.tag]
    return {"Job ID": posting.job_id, "Date found": posting.captured_at[:10],
            "Job title": posting.title, "Company": posting.company, "Salary": posting.salary,
            "Location": posting.location, "Brief description": quote, "Apply link": posting.apply_url,
            "Source": posting.source_id, "Rank (prelim)": rank, "Fit": "", "Next step": "",
            "Status": "New", "Notes": "", "My rating": "",
            "More details": f"Source: {posting.apply_url}\nEvidence: {quote}"}


def absolute(base: str, url: str) -> str:
    return urljoin(base, url)
