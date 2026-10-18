"""Multi-source postings: one parser per source, the AI-PM filter, deterministic rows.

Parsers take already-fetched data and never touch the network. Source text is
untrusted: it is cleaned, never executed, and only an exact leading excerpt of it
is stored. Models do not choose any cell value on this path.
"""

from dataclasses import dataclass
from html import unescape
import hashlib
import json
import math
import re
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup
import feedparser

from jobhunter.records import https_url
from jobhunter.job_identity import canonical_key, verified_requisition

PM_TITLE = re.compile(r"\b(product manager|product lead|group product manager|head of product|"
                      r"director of product|vp of product|vp,? product|pm)\b", re.I)
EXCLUDED_TITLE = re.compile(r"\b(intern|internship|summer associate|product marketing|"
                            r"product designer|product design|product communications|program manager|"
                            r"project manager)\b", re.I)
AI_TERMS = re.compile(r"\b(ai|a\.i\.|ml|llms?|genai|gen ai|generative ai|machine learning|"
                      r"artificial intelligence|agentic|ai agents?|foundation models?|"
                      r"language models?|deep learning)\b", re.I)
US_TERMS = re.compile(r"\b(united states(?: of america)?|usa|u\.s\.a?\.?|us|north america|new mexico|new york|nyc|san francisco|"
                      r"sf|bay area|seattle|austin|boston|chicago|los angeles|denver|atlanta|"
                      r"washington|dc|miami|california|texas|massachusetts)\b", re.I)
ANYWHERE = re.compile(r"\b(remote|anywhere|worldwide|global|hybrid)\b", re.I)
NON_US = re.compile(r"\b(south america|latin america|dominican republic|rep[uú]blica dominicana|europe|emea|apac|asia|latam|canada|mexico|brazil|uk|united kingdom|london|"
                    r"ireland|dublin|germany|berlin|france|paris|spain|netherlands|amsterdam|india|"
                    r"bangalore|singapore|japan|tokyo|australia|sydney|israel|tel aviv|poland|"
                    r"portugal|sweden|switzerland|zurich|dubai|nigeria|kenya|south africa|bengaluru|mumbai|delhi|"
                    r"hyderabad|pune|chennai|gurgaon|gurugram|noida|karnataka|philippines|manila|vietnam|"
                    r"indonesia|jakarta|argentina|buenos aires|colombia|bogota|chile|santiago|turkey|"
                    r"istanbul|egypt|cairo|pakistan|bangladesh|china|shanghai|beijing|hong kong|korea|seoul|"
                    r"taiwan|new zealand|auckland|italy|milan|rome|belgium|brussels|denmark|copenhagen|"
                    r"norway|oslo|finland|helsinki|austria|vienna|czech|prague|romania|bucharest|ukraine)\b", re.I)
COUNTRY_CODE = re.compile(r",\s*[A-Z]{2},\s*([A-Z]{2})\b")
LOCATION_US_CODE = re.compile(r",\s*(?:A[LKZR]|C[AOT]|DE|FL|GA|HI|I[ADLN]|K[SY]|LA|M[ADEINOST]|"
                              r"N[CDEHJMVY]|O[HKR]|PA|RI|S[CD]|T[NX]|UT|V[AT]|W[AIVY]|DC)\b")
LATIN_AMERICA = re.compile(r'\b(south america|latin america|latam|colombia|dominican republic|rep[uú]blica dominicana|'
                           r'brazil|brasil|argentina|chile|peru|perú|ecuador|bolivia|uruguay|paraguay|venezuela|'
                           r'(?<!new )mexico|méxico|costa rica|panama|panamá|guatemala|honduras|el salvador|nicaragua|belize)\b', re.I)
ONSITE_COUNTRIES = re.compile(r'\b(colombia|dominican republic|rep[uú]blica dominicana)\b', re.I)
REMOTE_TERMS = re.compile(r'\b(remote|anywhere|worldwide|global)\b', re.I)
EXPLICIT_US = re.compile(r'(?i:\b(?:united states|usa)\b|\bu\.s\.(?:a\.)?)|\bUS\b')
MIN_REGIONAL_ANNUAL_USD = 70_000


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
    remote: bool = False  # explicit source metadata; False does not prove on-site

    def __post_init__(self):
        for value in (self.job_id, self.source_id, self.company, self.title, self.text):
            if not isinstance(value, str) or not value.strip():
                raise ValueError("invalid_posting_text")
        if (not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9:._~-]{0,300}", self.job_id)
                or not isinstance(self.location, str) or not isinstance(self.salary, str)
                or self.tag not in {"ai", "bigtech", "other"} or type(self.remote) is not bool
                or not https_url(self.apply_url)):
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
    if any(code != "US" for code in COUNTRY_CODE.findall(location)):  # "City, ST, CC" with a non-US country
        return False
    return bool(LOCATION_US_CODE.search(location) or ANYWHERE.search(location))


def regional_salary_match(salary: str) -> bool:
    """Annual USD salary range overlaps the user's floor; unknown units stay unknown."""
    usd = re.compile(r'\bUSD\b|US\$', re.I)
    salary = salary.replace('_', ' ')
    if (not usd.search(salary)
            or not re.search(r'\b(year|yearly|annual|annually|annum|yr)\b', salary, re.I)
            or re.search(r'\b(COP|DOP|CAD|AUD|MXN|EUR|GBP|hour|hourly|month|monthly|week|weekly|day|daily|'
                         r'OTE|total compensation|equity)\b|RD\$|R\$', salary, re.I)):
        return False
    amounts = []
    for number, scale in re.findall(r'(?<![\w.])(\d[\d,]*(?:\.\d+)?)\s*([kK]?)(?!\w|\.\d)', usd.sub(' ', salary)):
        value = float(number.replace(',', '')) * (1000 if scale else 1)
        if math.isfinite(value):
            amounts.append(value)
    return bool(amounts and max(amounts) >= MIN_REGIONAL_ANNUAL_USD)


def collection_location_match(location: str, salary: str = '', *, remote: bool = False) -> bool:
    """Collection preference; a regional remote lead does not assert US eligibility."""
    if LATIN_AMERICA.search(location) and not EXPLICIT_US.search(location):
        return (remote or bool(REMOTE_TERMS.search(location))
                or bool(ONSITE_COUNTRIES.search(location) and regional_salary_match(salary)))
    return us_or_unknown(location)


def ai_pm_match(posting: Posting) -> bool:
    """PM role plus AI signal and the user's collection-location preference."""
    return (is_pm_title(posting.title)
            and collection_location_match(posting.location, posting.salary, remote=posting.remote)
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
        sections = [plain(item.get("descriptionPlain")) or clean_html(item.get("description"))]
        for section in item.get("lists") or []:
            sections.extend([plain(section.get("text")), clean_html(section.get("content"))])
        sections.append(plain(item.get("additionalPlain")) or clean_html(item.get("additional")))
        text = " ".join(section for section in sections if section)
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
                       ctx["captured_at"], tag=ctx["tag"], remote=item.get('isRemote') is True)
    return (*_collect(listed, build), len(listed))


def parse_remotive(data, ctx):
    if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
        raise ValueError("invalid_board_response")

    def build(item):
        return Posting(f"remotive:{item['id']}", ctx["source_id"], plain(item.get("company_name")),
                       plain(item.get("title")), plain(item.get("candidate_required_location")),
                       clean_html(item.get("description")), item.get("url"), ctx["captured_at"],
                       salary=plain(item.get("salary")), tag="other", remote=True)
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
                       tag="other", remote=True)
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
                                      item.get("salaryPeriod")), tag="other", remote=True)
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
                                      item.get("salaryCurrency"), item.get("salaryPeriod")), tag="other", remote=True)
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


def _stub_text(value):
    return plain(value) if isinstance(value, str) else ""


def stubs_yc(text, ctx):
    """Listing rows for YC product jobs; the description comes from each job's own page."""
    stubs, rejected = [], 0
    for job in _page_json(text)["props"]["jobPostings"]:
        try:
            stubs.append({"job_id": f"{ctx['source_id']}:{job['id']}", "company": _stub_text(job.get("companyName")),
                          "title": _stub_text(job.get("title")), "location": _stub_text(job.get("location")),
                          "url": absolute("https://www.ycombinator.com", job["url"]),
                          "salary": _stub_text(job.get("salaryRange"))})
        except (KeyError, TypeError, AttributeError):
            rejected += 1
    return stubs, rejected


LD_JSON = re.compile(r'<script type="application/ld(?:\+|&#x2B;)json">(.*?)</script>', re.S)


def _json_ld_blocks(text):
    for block in LD_JSON.findall(text):
        try:
            data = json.loads(block)
        except (ValueError, RecursionError):
            continue
        for item in data.get("@graph", [data]) if isinstance(data, dict) else data:
            if isinstance(item, dict):
                yield item


def _job_posting(text):
    return next((item for item in _json_ld_blocks(text) if item.get("@type") == "JobPosting"), {})


def detail_yc(text):
    return {"text": clean_html(_job_posting(text).get("description"))}


def stubs_builtin(text, ctx):
    """Built In listing: JSON-LD ItemList of titles and links; company and place come from each job page."""
    stubs, rejected = [], 0
    for block in _json_ld_blocks(text):
        if block.get("@type") != "ItemList":
            continue
        for item in block.get("itemListElement", []):
            try:
                match = re.search(r"/job/[^/]+/(\d+)$", item["url"])
                stubs.append({"job_id": f"{ctx['source_id']}:{match.group(1)}", "company": "", "location": "",
                              "title": _stub_text(item.get("name")), "url": item["url"], "salary": ""})
            except (KeyError, TypeError, AttributeError):
                rejected += 1
    return stubs, rejected


def detail_builtin(text):
    job = _job_posting(text)
    org = job.get("hiringOrganization")
    places = job.get("jobLocation") or []
    places = places if isinstance(places, list) else [places]
    parts = []
    for place in places:
        address = place.get("address", {}) if isinstance(place, dict) else {}
        label = ", ".join(plain(address.get(k)) for k in ("addressLocality", "addressRegion", "addressCountry")
                          if isinstance(address.get(k), str) and address.get(k).strip())
        if label:
            parts.append(label)
    requirement = job.get("applicantLocationRequirements")
    if not parts and isinstance(requirement, dict) and isinstance(requirement.get("name"), str):
        parts.append(plain(requirement["name"]))
    base_salary = job.get('baseSalary') if isinstance(job.get('baseSalary'), dict) else {}
    salary = base_salary.get('value', {})
    return {"text": clean_html(job.get("description")),
            "company": plain(org.get("name")) if isinstance(org, dict) else "",
            "location": "; ".join(parts),
            "salary": _salary(salary.get("minValue"), salary.get("maxValue"), plain(base_salary.get('currency')), salary.get("unitText"))
            if isinstance(salary, dict) else ""}


def _getro_state(text):
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', text, re.S)
    if not match:
        raise ValueError("invalid_board_response")
    return json.loads(match.group(1))["props"]["pageProps"]["initialState"]["jobs"]


def stubs_getro(text, ctx):
    stubs, rejected = [], 0
    base = "https://" + urlsplit(ctx["url"]).hostname
    for job in _getro_state(text)["found"]:
        try:
            org = job["organization"]
            low, high = job.get("compensationAmountMinCents"), job.get("compensationAmountMaxCents")
            salary = _salary(low // 100 if type(low) is int else None, high // 100 if type(high) is int else None,
                             job.get("compensationCurrency"), job.get("compensationPeriod"))
            locations = job.get("locations") or job.get("searchableLocations") or []
            stubs.append({"job_id": f"{ctx['source_id']}:{job['id']}", "company": _stub_text(org.get("name")),
                          "title": _stub_text(job.get("title")),
                          "location": ", ".join(_stub_text(x) for x in locations if isinstance(x, str)),
                          "url": f"{base}/companies/{org['slug']}/jobs/{job['slug']}", "salary": salary})
        except (KeyError, TypeError, AttributeError):
            rejected += 1
    return stubs, rejected


def detail_getro(text):
    job = _getro_state(text).get("currentJob") or {}
    return {"text": clean_html(job.get("description"))}


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
LISTING_ONLY = {"a16z": count_a16z, "hn": count_hn}
DETAIL_SOURCES = {"yc": (stubs_yc, detail_yc), "getro": (stubs_getro, detail_getro),
                  "builtin": (stubs_builtin, detail_builtin)}


SOURCE_PRIORITY = {"greenhouse": 0, "lever": 0, "ashby": 0, "yc-product": 1, "getro-accel": 1, "getro-primary": 1,
                   "builtin-product": 1}


def _similar(posting: Posting) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", f"{posting.company} {posting.title}".lower()).split())


def dedupe(postings):
    """[(posting, note)]: merge only identical employer links/requisitions; flag look-alikes.

    Company/title similarity alone never merges (PLAN): it adds a review note and keeps both rows.
    Company boards win over aggregators; the winner's note lists the other discovery sources.
    """
    def rank(posting):
        return SOURCE_PRIORITY.get(posting.source_id.split(":")[0], SOURCE_PRIORITY.get(posting.source_id, 2))
    ordered = sorted(postings, key=rank)  # stable: first-seen order inside a priority
    kept, by_key, by_similar = [], {}, {}
    for posting in ordered:
        key = canonical_key(posting.apply_url)
        if (verified_requisition(key) and key in by_key
                and by_key[key]["posting"].source_id != posting.source_id):
            by_key[key]["also"].append(posting.source_id)
            continue
        entry = {"posting": posting, "also": [], "similar": by_similar.get(_similar(posting)),
                 'shared': by_key[key]['posting'].job_id if not verified_requisition(key) and key in by_key else None}
        by_key.setdefault(key, entry)
        by_similar.setdefault(_similar(posting), posting.job_id)
        kept.append(entry)
    notes = []
    for entry in kept:
        parts = []
        if entry["also"]:
            parts.append("Also listed by: " + ", ".join(sorted(set(entry["also"]))))
        if entry['shared']:
            parts.append(f"Possible duplicate of {entry['shared']} (shared application link; requisition identity unverified; needs review)")
        elif entry["similar"]:
            parts.append(f"Possible duplicate of {entry['similar']} (same company and title, different link; needs review)")
        notes.append((entry["posting"], "\n".join(parts)))
    return notes


def to_row(posting: Posting, note: str = "") -> dict:
    """Deterministic Jobs row; the description is an exact leading excerpt of source text."""
    quote = posting.text[:300].rstrip()
    rank = {"ai": 1, "bigtech": 2, "other": 3}[posting.tag]
    details = f"Source: {posting.apply_url}\nEvidence: {quote}" + (f"\n{note}" if note else "")
    if posting.remote:
        details += '\nWork mode: Remote (source metadata)'
    return {"Job ID": posting.job_id, "Date found": posting.captured_at[:10],
            "Job title": posting.title, "Company": posting.company, "Salary": posting.salary,
            "Location": posting.location, "Brief description": quote, "Apply link": posting.apply_url,
            "Source": posting.source_id, "Rank (prelim)": rank, "Fit": "", "Next step": "",
            "Status": "New", "Notes": "", "My rating": "", "More details": details}


def absolute(base: str, url: str) -> str:
    return urljoin(base, url)
