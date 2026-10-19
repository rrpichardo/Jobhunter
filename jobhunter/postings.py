"""Multi-source postings: one parser per source, collection preferences, deterministic rows.

Parsers take already-fetched data and never touch the network. Source text is
untrusted: it is cleaned, never executed, and only an exact leading excerpt of it
is stored. Models do not choose any cell value on this path.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
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

PM_TITLE_TERMS = (r"product manager|product lead|group product manager|head of product|"
                  r"director of product|vp of product|vp,? product")
PM_TITLE = re.compile(rf"\b({PM_TITLE_TERMS}|pm)\b", re.I)
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
# Same state vocabulary without a comma requirement; case-sensitive so words
# such as "or" and "in" are not mistaken for Oregon and Indiana.
US_STATE_CODE_TOKEN = re.compile(r'\b' + LOCATION_US_CODE.pattern.removeprefix(r',\s*'))
# Recheck state/ISO-code collisions in AMBIGUOUS_REGIONAL_CODES if this list changes.
LATIN_AMERICA = re.compile(r'\b(south america|latin america|latam|colombia|dominican republic|rep[uú]blica dominicana|'
                           r'brazil|brasil|argentina|chile|peru|perú|ecuador|bolivia|uruguay|paraguay|venezuela|'
                           r'(?<!new )mexico|méxico|costa rica|panama|panamá|guatemala|honduras|el salvador|nicaragua|belize)\b', re.I)
ONSITE_COUNTRIES = re.compile(r'\b(colombia|dominican republic|rep[uú]blica dominicana)\b', re.I)
REMOTE_TERMS = re.compile(r'\b(remote|remoto|anywhere|worldwide|global)\b', re.I)
EXPLICIT_US = re.compile(r'(?i:\b(?:united states|usa)\b|\bu\.s\.(?:a\.)?)|\bUS\b')
MIN_REGIONAL_ANNUAL_USD = 70_000
# Short country/state collisions are not US evidence on the regional path.
AMBIGUOUS_REGIONAL_CODES = {'AR', 'CO', 'DC', 'PA'}
US_STATE_NAME = re.compile(
    r',\s*(?:alabama|alaska|arizona|arkansas|california|colorado|connecticut|delaware|florida|'
    r'georgia|hawaii|idaho|illinois|indiana|iowa|kansas|kentucky|louisiana|maine|maryland|'
    r'massachusetts|michigan|minnesota|mississippi|missouri|montana|nebraska|nevada|'
    r'new hampshire|new jersey|new mexico|new york|north carolina|north dakota|ohio|'
    r'oklahoma|oregon|pennsylvania|rhode island|south carolina|south dakota|tennessee|'
    r'texas|utah|vermont|virginia|washington|west virginia|wisconsin|wyoming|district of columbia)\b', re.I)
US_WORK_MODE = r'(?:hybrid|on[- ]?site|in[- ]?office)'
US_LOCATION_SUFFIX = re.compile(
    r'\s*(?:\d{5}(?:-\d{4})?)?\s*'
    rf'(?:\(\s*{US_WORK_MODE}\s*\)|[-/,]?\s*{US_WORK_MODE})?\s*', re.I)


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
    posted_at: str = ""  # ISO-8601 UTC from source metadata; empty when the source gives no usable date

    def __post_init__(self):
        for value in (self.job_id, self.source_id, self.company, self.title, self.text):
            if not isinstance(value, str) or not value.strip():
                raise ValueError("invalid_posting_text")
        if (not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9:._~-]{0,300}", self.job_id)
                or not isinstance(self.location, str) or not isinstance(self.salary, str)
                or self.tag not in {"ai", "bigtech", "other"} or type(self.remote) is not bool
                or not https_url(self.apply_url) or not isinstance(self.posted_at, str)
                or (self.posted_at and parse_posted(self.posted_at) != self.posted_at)):
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


def annual_usd_salary_ceiling(salary: str) -> float | None:
    """Explicit annual USD base-pay ceiling; unsupported compensation is unresolved."""
    usd = re.compile(r'\bUSD\b|US\$', re.I)
    salary = salary.replace('_', ' ')
    if (not usd.search(salary)
            or not re.search(r'\b(year|yearly|annual|annually|annum|yr)\b', salary, re.I)
            or re.search(r'\b(COP|DOP|CAD|AUD|MXN|EUR|GBP|hour|hourly|month|monthly|week|weekly|day|daily|'
                         r'OTE|total compensation|equity)\b|RD\$|R\$', salary, re.I)):
        return None
    # Only amounts attached to currency are pay; benefits such as 401k are not.
    amount = r'\$?\s*(?<![\w.])\d[\d,]*(?:\.\d+)?\s*[kK]?(?!\w|\.\d)'
    pay_range = rf'{amount}(?:\s*[-–—]\s*{amount})?'
    amounts = []
    for match in re.finditer(rf'(?:\bUSD\b|US\$)\s*({pay_range})|({pay_range})\s*(?:\bUSD\b|US\$)',
                             salary, re.I):
        before, after = salary[:match.start()], salary[match.end():]
        period = r'(?:year|yearly|annual|annually|annum|yr)\b'
        annual_after = re.match(rf'\s*(?:(?:gross|base)\s+)?(?:(?:per|a)\s+|/\s*)?'
                                rf'(?:{period}|\(\s*{period}\s*\))', after, re.I)
        annual_before = re.search(r'\b(?:annual|annually|yearly)(?:\s+(?:base|salary|pay|range))*\s*:?\s*$',
                                  before, re.I)
        if not (annual_after or annual_before):
            continue  # another currency figure elsewhere is not evidence of annual pay
        non_salary = r'(?:bonus|commission|benefits?|allowance|reimbursement)'
        # Use the current compensation clause, keeping decimal/thousands separators intact.
        context = re.split(r'[;+\n]|(?<!\d)[,.]|[,.](?!\d)', before)[-1]
        labels = re.findall(rf'\b(?:{non_salary}|salary|base)\b', context, re.I)
        labelled_before = labels and labels[-1].casefold() not in {'salary', 'base'}
        non_salary_after = r'(?:bonus|commission|allowance|reimbursement|benefits?\b(?!\s+(?:included|available|offered)\b))'
        labelled_after = annual_after and re.match(
            rf'\s*(?:(?:performance|cash|target|guaranteed|retention|sign(?:ing|[- ]on)|discretionary|in)\s+)*'
            rf'{non_salary_after}\b', after[annual_after.end():], re.I)
        if labelled_before or labelled_after:
            continue
        pay = match.group(1) or match.group(2)
        for number, scale in re.findall(r'(\d[\d,]*(?:\.\d+)?)\s*([kK]?)', pay):
            value = float(number.replace(',', '')) * (1000 if scale else 1)
            if math.isfinite(value):
                amounts.append(value)
    return max(amounts) if amounts else None

def regional_salary_match(salary: str) -> bool:
    """Historical regional probe helper; production uses collection_match."""
    amount = annual_usd_salary_ceiling(salary)
    return amount is not None and amount >= MIN_REGIONAL_ANNUAL_USD



def collection_location_match(location: str, salary: str = '', *, remote: bool = False) -> bool:
    """Collection preference; a regional remote lead does not assert US eligibility."""
    if LATIN_AMERICA.search(location):
        us_state = any(US_LOCATION_SUFFIX.fullmatch(location[match.end():])
                       and match.group().lstrip(', ').strip() not in AMBIGUOUS_REGIONAL_CODES
                       for match in LOCATION_US_CODE.finditer(location))
        us_state = us_state or any(US_LOCATION_SUFFIX.fullmatch(location[match.end():])
                                   for match in US_STATE_NAME.finditer(location))
        if EXPLICIT_US.search(location) or us_state:
            return True
        return (remote or bool(REMOTE_TERMS.search(location))
                or bool(ONSITE_COUNTRIES.search(location) and regional_salary_match(salary)))
    return us_or_unknown(location)


def ai_pm_match(posting: Posting) -> bool:
    """PM role plus AI signal and the user's collection-location preference."""
    return (is_pm_title(posting.title)
            and collection_location_match(posting.location, posting.salary, remote=posting.remote)
            and (posting.tag == "ai" or bool(AI_TERMS.search(posting.title))
                 or bool(AI_TERMS.search(posting.text))))


# The AI-only helpers above remain for replaying the historical M0 probe. All
# current source collection uses these broader user-approved role preferences.
ROLE_EXCLUSIONS = re.compile(r"\b(intern|internship|summer associate|product marketing|"
                             r"product design(?:er)?|product communications)\b", re.I)
ROLE_FAMILIES = (
    ('Product management', PM_TITLE),
    ('Chief of Staff', re.compile(r'\bchief of staff\b', re.I)),
    ('Leadership program', re.compile(r'\b(?:leadership (?:development )?program|'
                                     r'(?:MBA|management) (?:development|rotation(?:al)?) program)\b', re.I)),
    ('Strategy', re.compile(r'\b(?:strategy (?:manager|lead|director)|'
                           r'(?:manager|director|head|vp) (?:of )?(?:corporate |business )?strategy)\b', re.I)),
    ('Entrepreneurship', re.compile(r'\b(?:entrepreneur|founder)[- ]in[- ]residence\b', re.I)),
    ('Project management', re.compile(r'\bproject (?:manager|management lead|director)\b', re.I)),
    # "Forward-Deployed AI Strategist" and its variants: forward deployed / FDE next to strategist or strategy within
    # one title, in either order ("AI Strategist, Forward Deployed"), plus "AI Deployment Strategist" and "AI
    # Implementation Strategist" (the user's other names for it) and the bare "Deployment Strategist". Forward-deployed
    # ENGINEER titles do not match.
    # "FDE" is itself short for forward deployed ENGINEER, so next to it only the noun "strategist" counts ("FDE Strategist"),
    # never the bare word "strategy" ("FDE - AI Strategy" is an engineering title).
    ('Forward-deployed strategy', re.compile(r'\bforward[- ]?deployed\b[^,;|\n]{0,40}?\bstrateg(?:ist|y)\b|'
                                             r'\bFDE\b[^,;|\n]{0,40}?\bstrategist\b|'
                                             r'\bstrateg(?:ist|y)\b[^;|\n]{0,40}?\bforward[- ]?deployed\b|'
                                             r'\bstrategist\b[^;|\n]{0,40}?\bFDE\b|'
                                             r'\b(?:(?:AI|GenAI|applied AI)\s+(?:deployment|implementation)|deployment)\s+strategist\b', re.I)),
)

# Free-text scan (Hacker News comments, social posts): the same families as above, built from ROLE_FAMILIES so
# candidate selection and delivery cannot drift apart. The bare "PM" token is left out because in running text
# it is mostly a time of day.
ROLE_TEXT = re.compile("|".join(
    rf"\b(?:{PM_TITLE_TERMS})\b" if family == "Product management" else pattern.pattern
    for family, pattern in ROLE_FAMILIES), re.I)


# A title that names an engineer or developer is an engineering role, even when "strategy" sits within 40 characters of
# "forward deployed" ("Forward-Deployed Engineer - AI Strategy"), so it never counts as the strategist family.
FORWARD_DEPLOYED_ENGINEER = re.compile(r'\b(?:engineers?|engineering|engr?|developers?|dev|SWEs?|SDEs?)\b|\bsoftware development\b', re.I)


def role_family(title: str) -> str | None:
    if ROLE_EXCLUSIONS.search(title):
        return None
    for family, pattern in ROLE_FAMILIES:
        if pattern.search(title) and not (family == 'Forward-deployed strategy' and FORWARD_DEPLOYED_ENGINEER.search(title)):
            return family
    return None


def collection_region(location: str, *, remote: bool = False) -> str | None:
    """US / LATAM / unresolved; None means explicitly outside collection scope."""
    # Normalize only explicit regional city/country pairs before inspecting US
    # state codes. This works anywhere in a multi-location listing and leaves
    # other CO/PA/AR locality pairs as potentially US evidence. Original source
    # location text remains on the Posting and Sheet row.
    city = r'(?:bogot[aá](?:\s+D\.?\s*C\.?)?|medell[ií]n)'
    # Only known department/capital-district spellings may be consumed. An
    # arbitrary phrase here could swallow a second city and its US state code.
    department = r'(?:Antioquia|Cundinamarca|D\.?\s*C\.?|Distrito Capital|Capital District|Colombia)'
    location = re.sub(rf'\b{city}(?:,\s*{department})?,\s*(?:CO|Colombia)\b', 'Colombia', location, flags=re.I)
    location = re.sub(r'\bsanto domingo,\s*DO\b', 'Dominican Republic', location, flags=re.I)
    for country, code in (('Colombia', 'CO'), ('Panama', 'PA'), ('Argentina', 'AR'),
                          ('Dominican Republic', 'DO')):
        location = re.sub(rf'\b{country},\s*{code}\b', country, location, flags=re.I)
    us_evidence = bool(EXPLICIT_US.search(location) or US_TERMS.search(location)
                       or US_STATE_NAME.search(location) or US_STATE_CODE_TOKEN.search(location))
    if re.fullmatch(rf'\s*(?:{city}|santo domingo)\s*', location, re.I):
        return 'unresolved'  # city names alone do not establish the country
    if (re.search(r'\b(?:bogot[aá]|medell[ií]n)\b', location, re.I)
            and re.search(r',\s*CO\b', location, re.I)):
        return 'unresolved'  # unsupported regional locality syntax is not Colorado evidence
    if LATIN_AMERICA.search(location):
        if us_evidence:
            return 'unresolved'  # mixed US/LATAM availability does not choose a work location
        # A second place without a reliable country/state cannot establish the
        # lower floor either. Strip only attached prefix/suffix work-mode labels:
        # "Remote - Colombia" is one place; "Colombia or Remote" is ambiguous.
        mode = r'(?:remote|remoto|hybrid|on[- ]?site|in[- ]?office)'
        operator = r'(?:[-–—/:,&|;·]|\b(?:or|and|y|o)\b)'
        places = location
        prefix = re.match(rf'^\s*{mode}\s*[-–—/:,]\s*', places, re.I)
        if prefix and not re.match(operator, places[prefix.end():].lstrip(), re.I):
            places = places[prefix.end():]
        suffix = re.search(rf'\s*[-–—/:]\s*{mode}\s*$', places, re.I)
        if suffix and not re.search(rf'{operator}\s*$', places[:suffix.start()], re.I):
            places = places[:suffix.start()]
        places = [part.strip(' -:.,') for part in re.split(
            r'[,|;/&·\n]+|\s+[-–—]\s+|\b(?:or|and|y|o)\b', places, flags=re.I)]
        places = [part for part in places if part]
        qualifier = rf'(?:{city}|santo domingo|{department})(?:\s*\(\s*{mode}\s*\))?'
        if len(places) > 1 and any(not LATIN_AMERICA.search(part)
                and not re.fullmatch(qualifier, part, re.I) for part in places):
            return 'unresolved'
        if remote or REMOTE_TERMS.search(location) or ONSITE_COUNTRIES.search(location):
            return 'LATAM'
        return None
    if (re.search(r'\b(?:bogot[aá]|medell[ií]n|santo domingo)\b', location, re.I)
            and not EXPLICIT_US.search(location)):
        return 'unresolved'  # a city/department without a country is not a US location
    if not us_or_unknown(location):
        if NON_US.search(location) or any(code != 'US' for code in COUNTRY_CODE.findall(location)):
            return None
        return 'unresolved'  # unrecognized text is not proof of a foreign location
    if US_TERMS.search(location) or LOCATION_US_CODE.search(location):
        return 'US'
    return 'unresolved'


def salary_preference(posting: Posting) -> tuple[str, int]:
    region = collection_region(posting.location, remote=posting.remote)
    floor = 70_000 if region == 'LATAM' else 140_000
    amount = annual_usd_salary_ceiling(posting.salary)
    if amount is not None and amount < 70_000:
        return 'below floor', floor
    if region in (None, 'unresolved') or amount is None:
        return 'unresolved', floor
    return ('satisfied' if amount >= floor else 'below floor'), floor


def collection_stub_match(title: str, location: str, salary: str) -> bool:
    """Apply known preference evidence before spending a capped detail request."""
    region = collection_region(location)
    amount = annual_usd_salary_ceiling(salary)
    floor = 70_000 if region == 'LATAM' else 140_000
    return bool(role_family(title) and region is not None
                and (amount is None or amount >= (70_000 if region == 'unresolved' else floor)))


def collection_reason(posting: Posting) -> str:
    """Why the collection filter drops a posting (a fixed code), or "" when it is collected."""
    if not role_family(posting.title):
        return 'role_not_in_scope'
    if collection_region(posting.location, remote=posting.remote) is None:
        return 'place_excluded'
    if salary_preference(posting)[0] == 'below floor':
        return 'pay_below_floor'
    return ''


def collection_match(posting: Posting) -> bool:
    """Collect approved roles; retain unresolved requirements without asserting eligibility."""
    return not collection_reason(posting)


def collection_title_priority(title: str, tag: str = 'other', text: str = '') -> int:
    """Available listing evidence orders roles before spending detail-fetch slots."""
    family = role_family(title)
    if family == 'Product management':
        ai_role = bool(AI_TERMS.search(title + ' ' + text))
        return (0 if ai_role else 3) + {'ai': 0, 'bigtech': 1, 'other': 2}[tag]
    return next((6 + index for index, (name, _) in enumerate(ROLE_FAMILIES[1:]) if name == family), 99)


def collection_priority(posting: Posting) -> int:
    """Apply the same role ordering to fully fetched posting candidates."""
    return collection_title_priority(posting.title, posting.tag, posting.text)



def parse_posted(value) -> str:
    """ISO-8601 UTC (seconds) from a source date, or "" when absent or unreadable.

    Accepts epoch seconds or milliseconds (int, float or digit string), ISO-8601 text and RFC 2822 text.
    A time without a zone is read as UTC. Never guesses: anything else returns "".
    """
    if value is None or isinstance(value, bool) or not isinstance(value, (str, int, float)):
        return ""
    try:
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return ""
            if re.fullmatch(r"\d{9,13}(?:\.\d+)?", text):
                value = float(text)
            else:
                try:
                    moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
                except ValueError:
                    moment = parsedate_to_datetime(text)
        if isinstance(value, (int, float)):
            seconds = value / 1000 if value > 1e11 else value
            moment = datetime.fromtimestamp(seconds, timezone.utc)
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        return moment.astimezone(timezone.utc).replace(microsecond=0).isoformat()
    except (ValueError, TypeError, OverflowError, OSError, IndexError):
        return ""


def within_lookback(posting: "Posting", now: datetime, days: int) -> bool:
    """True when the posting is inside the window, or its date is unknown (never dropped on missing data)."""
    if not posting.posted_at:
        return True
    return datetime.fromisoformat(posting.posted_at) >= now - timedelta(days=days)


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
                       item.get("absolute_url"), ctx["captured_at"], tag=ctx["tag"],
                       posted_at=parse_posted(item.get("first_published")))
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
                       text, item.get("hostedUrl"), ctx["captured_at"], tag=ctx["tag"],
                       remote=plain(item.get('workplaceType')).casefold() == 'remote',
                       posted_at=parse_posted(item.get("createdAt")))
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
                       ctx["captured_at"], tag=ctx["tag"], remote=item.get('isRemote') is True,
                       posted_at=parse_posted(item.get("publishedAt")))
    return (*_collect(listed, build), len(listed))


def parse_remotive(data, ctx):
    if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
        raise ValueError("invalid_board_response")

    def build(item):
        return Posting(f"remotive:{item['id']}", ctx["source_id"], plain(item.get("company_name")),
                       plain(item.get("title")), plain(item.get("candidate_required_location")),
                       clean_html(item.get("description")), item.get("url"), ctx["captured_at"],
                       salary=plain(item.get("salary")), tag="other", remote=True,
                       posted_at=parse_posted(item.get("publication_date")))
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
                       tag="other", remote=True,
                       posted_at=parse_posted(item.get("date") or item.get("epoch")))
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
                                      item.get("salaryPeriod")), tag="other", remote=True,
                       posted_at=parse_posted(item.get("pubDate")))
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
                                      item.get("salaryCurrency"), item.get("salaryPeriod")), tag="other", remote=True,
                       posted_at=parse_posted(item.get("pubDate")))
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
                       ctx["captured_at"], tag="other",
                       posted_at=parse_posted(item.get("publication_date")))
    return (*_collect(data["results"], build), len(data["results"]))


def _first_https(*links):
    for link in links:
        if https_url(link):
            return link
    raise ValueError("no_https_link")


# JSearch gives an ISO country code. Latin American codes become names so the regional rules in
# collection_location_match apply; any other non-US country is not a collection candidate.
JSEARCH_LATAM_COUNTRIES = {
    "AR": "Argentina", "BO": "Bolivia", "BR": "Brazil", "BZ": "Belize", "CL": "Chile", "CO": "Colombia",
    "CR": "Costa Rica", "DO": "Dominican Republic", "EC": "Ecuador", "GT": "Guatemala", "HN": "Honduras",
    "MX": "Mexico", "NI": "Nicaragua", "PA": "Panama", "PE": "Peru", "PY": "Paraguay", "SV": "El Salvador",
    "UY": "Uruguay", "VE": "Venezuela"}


def _jsearch_country(item):
    """'US', a Latin American country name, '' when absent, or None for any other country."""
    code = plain(item.get("job_country")).upper() if isinstance(item, dict) else ""
    if code in {"", "US", "USA"}:
        return "US" if code else ""
    return JSEARCH_LATAM_COUNTRIES.get(code)


def parse_jsearch(data, ctx):
    """JSearch (RapidAPI) results; any field may be missing or null."""
    if not isinstance(data, dict) or data.get("status", "OK") != "OK":
        raise ValueError("invalid_board_response")
    jobs = data.get("data")
    if isinstance(jobs, dict):  # /search-v2 nests the list: {"data": {"jobs": [...], "cursor": ...}}
        jobs = jobs.get("jobs")
    if not isinstance(jobs, list):
        raise ValueError("invalid_board_response")

    def build(item):
        job_id = item.get("job_id")
        if not isinstance(job_id, str) or not job_id.strip():
            raise ValueError
        remote = item.get("job_is_remote") is True
        country = _jsearch_country(item)
        place = ", ".join(part for part in (plain(item.get("job_city")), plain(item.get("job_state")), country)
                          if part)
        # Keep the place beside "Remote" so a remote job tied to a non-US country is not read as US.
        location = ", ".join(part for part in ("Remote" if remote else "", place) if part)
        return Posting(f"jsearch:{_digest(job_id)}", ctx["source_id"], plain(item.get("employer_name")),
                       plain(item.get("job_title")), location, clean_html(item.get("job_description")),
                       _first_https(item.get("job_apply_link"), item.get("job_google_link")),
                       ctx["captured_at"],
                       salary=_salary(item.get("job_min_salary"), item.get("job_max_salary"),
                                      item.get("job_salary_currency"), item.get("job_salary_period")),
                       tag="other", remote=remote,
                       posted_at=parse_posted(item.get("job_posted_at_datetime_utc")))
    # Non-US, non-Latin-American countries are skipped here (not counted as rejected items) because the
    # flattened location text alone cannot reliably exclude every foreign country.
    candidates = [item for item in jobs if not isinstance(item, dict) or _jsearch_country(item) is not None]
    return (*_collect(candidates, build), len(jobs))


def parse_jooble(data, ctx):
    """Jooble results; title and snippet carry highlight markup, and nothing marks a job remote."""
    if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
        raise ValueError("invalid_board_response")

    def build(item):
        link = _first_https(item.get("link"))
        raw_id = item.get("id")
        plain_id = (raw_id if type(raw_id) is int
                    else raw_id.strip() if isinstance(raw_id, str) and re.fullmatch(r"\s*-?\d{1,30}\s*", raw_id)
                    else None)
        identity = str(plain_id) if plain_id is not None else _digest(str(raw_id) if raw_id else link)
        return Posting(f"jooble:{identity}", ctx["source_id"], plain(item.get("company")),
                       clean_html(item.get("title")), plain(item.get("location")),
                       clean_html(item.get("snippet")), link, ctx["captured_at"],
                       salary=plain(item.get("salary")), tag="other",
                       posted_at=parse_posted(item.get("updated")))
    return (*_collect(data["jobs"], build), len(data["jobs"]))


def parse_wwr_rss(text, ctx):
    feed = feedparser.parse(text)
    if feed.bozo and not feed.entries:
        raise ValueError("invalid_board_response")

    def build(entry):
        title = plain(entry.get("title"))
        company, _, role = title.partition(": ")
        return Posting(f"wwr:{_digest(entry['link'])}", ctx["source_id"], company if role else "Unknown",
                       role or title, plain(entry.get("region")) or "Remote",
                       clean_html(entry.get("summary")), entry.get("link"), ctx["captured_at"],
                       tag="other", remote=True,  # WWR's feed contains remote jobs only
                       posted_at=parse_posted(entry.get("published")))
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
                          "salary": _stub_text(job.get("salaryRange")),
                          "posted_at": ""})  # the listing date is unverified; the job page's datePosted decides
        except (KeyError, TypeError, AttributeError):
            rejected += 1
    return stubs, rejected


def stubs_waas(text, ctx):
    """Work at a Startup public listing (no login): the page data holds the first jobs of one role page."""
    stubs, rejected = [], 0
    for job in _page_json(text)["props"]["jobs"]:
        try:
            stubs.append({"job_id": f"waas:{int(job['id'])}", "company": _stub_text(job.get("companyName")),
                          "title": _stub_text(job.get("title")), "location": _stub_text(job.get("location")),
                          "url": f"https://www.workatastartup.com/jobs/{int(job['id'])}",
                          "salary": _stub_text(job.get("salary")), "posted_at": ""})  # the site shows no posting date
        except (KeyError, TypeError, ValueError, AttributeError):
            rejected += 1
    return stubs, rejected


def detail_waas(text):
    props = _page_json(text)["props"]
    job, company = props["job"], props.get("company") or {}
    description = clean_html(job.get("descriptionHtml"))
    if not description:
        raise ValueError("invalid_board_response")
    return {"text": description, "company": _stub_text(company.get("name")), "location": _stub_text(job.get("location")),
            "salary": _stub_text(job.get("salaryRange"))}


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
    job = _job_posting(text)
    return {"text": clean_html(job.get("description")), "posted_at": parse_posted(job.get("datePosted"))}


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
                              "title": _stub_text(item.get("name")), "url": item["url"], "salary": "", "posted_at": ""})
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
    return {"text": clean_html(job.get("description")), "posted_at": parse_posted(job.get("datePosted")),
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
                          "url": f"{base}/companies/{org['slug']}/jobs/{job['slug']}", "salary": salary,
                          "posted_at": ""})  # the listing date is unverified
        except (KeyError, TypeError, AttributeError):
            rejected += 1
    return stubs, rejected


def detail_getro(text):
    job = _getro_state(text).get("currentJob") or {}
    return {"text": clean_html(job.get("description")), "posted_at": ""}  # no verified Getro date field yet


A16Z_JOB = re.compile(r"^/jobs/([a-z0-9-]+)/([0-9A-Za-z_-]+?--[0-9A-Za-z_-]*)$")


def stubs_a16z(text, ctx):
    """a16z portfolio board search page: the first page (about 25 jobs) of one search. Title from the link text;
    company, place, pay and date come from each job's own page."""
    stubs, seen, rejected = [], set(), 0
    for anchor in BeautifulSoup(text, "html.parser").find_all("a", href=A16Z_JOB):
        match = A16Z_JOB.match(anchor["href"])
        title = _stub_text(anchor.get_text(" "))
        # The job's identity is the company plus the whole last part of its link: on some boards the part before "--" is
        # only a title slug, so two different jobs of one title (two places) differ by what follows it.
        key = f"{match[1]}/{match[2]}"
        if key in seen:
            continue
        if not title:
            rejected += 1  # an image link with no text: the same job's text link may follow, so it is not marked seen
            continue
        seen.add(key)
        job_id = f"a16z:{match[1]}:{match[2]}" if len(key) <= 100 else f"a16z:{hashlib.sha256(key.encode()).hexdigest()[:24]}"
        stubs.append({"job_id": job_id, "company": match[1].replace("-", " ").title(),
                      "title": title, "location": "", "url": absolute("https://jobs.a16z.com", anchor["href"]),
                      "salary": "", "posted_at": ""})
    if not stubs and not rejected:
        if re.search(r"\b0 jobs\b|no roles match|no jobs found", BeautifulSoup(text, "html.parser").get_text(" "), re.I):
            return [], 0  # the board itself says the search has no results
        raise ValueError("invalid_board_response")  # a search page always lists jobs or says so; silence means a new layout
    return stubs, rejected


def _term(soup, label):
    """The text of the <dd> that follows a <dt> with this label (semantic tags, not class names). A page can show the
    same label twice, once cut short ("London, United Kingdom…") and once in full: the longest value wins."""
    values = []
    for term in soup.find_all("dt"):
        if _stub_text(term.get_text(" ")).casefold() == label:
            value = term.find_next_sibling("dd")
            if value is not None:
                values.append(_stub_text(value.get_text(" ")))
    return max(values, key=len, default="")


def detail_a16z(text):
    soup = BeautifulSoup(text, "html.parser")
    heading = soup.find("h1")
    about = next((h for h in soup.find_all("h2") if _stub_text(h.get_text(" ")).casefold() == "about the role"), None)
    if heading is None or about is None:
        raise ValueError("invalid_board_response")
    body = next((a for a in about.parents if heading in a.descendants), None)  # smallest block holding both
    description = clean_html(str(body)) if body is not None else ""
    marker = description.find("About the role")
    description = description[marker + len("About the role"):].strip() if marker >= 0 else description  # drop the page header
    if not description:
        raise ValueError("invalid_board_response")
    company = ""
    for block in _json_ld_blocks(text):
        if block.get("@type") == "BreadcrumbList":
            items = block.get("itemListElement") or []
            if len(items) >= 2 and isinstance(items[1], dict):
                company = _stub_text(items[1].get("name"))
    posted = re.search(r"\bPosted\s+([A-Z][a-z]{2})[a-z]*\s+(\d{1,2}),\s*(\d{4})", soup.get_text(" "))
    try:
        posted_at = (datetime.strptime(f"{posted[1]} {posted[2]} {posted[3]}", "%b %d %Y").replace(tzinfo=timezone.utc).isoformat()
                     if posted else "")
    except ValueError:
        posted_at = ""
    return {"text": description, "company": company, "location": _term(soup, "location"),
            "salary": _term(soup, "compensation"), "posted_at": posted_at}


def count_hn(data, ctx):
    hits = [h for h in data.get("hits", []) if isinstance(h, dict)
            and re.match(r"Ask HN: Who is hiring\?", h.get("title") or "")]
    if not hits:
        raise ValueError("invalid_board_response")
    return {"listed": hits[0].get("num_comments") or 0, "pm_titles": 0, "thread": hits[0].get("title")}


PARSERS = {"greenhouse": parse_greenhouse, "lever": parse_lever, "ashby": parse_ashby,
           "remotive": parse_remotive, "remoteok": parse_remoteok, "himalayas": parse_himalayas,
           "jobicy": parse_jobicy, "themuse": parse_themuse, "wwr": parse_wwr_rss,
           "jsearch": parse_jsearch, "jooble": parse_jooble}
LISTING_ONLY = {"hn": count_hn}
DETAIL_SOURCES = {"yc": (stubs_yc, detail_yc), "getro": (stubs_getro, detail_getro),
                  "builtin": (stubs_builtin, detail_builtin), "waas": (stubs_waas, detail_waas),
                  "a16z": (stubs_a16z, detail_a16z)}


SOURCE_PRIORITY = {"greenhouse": 0, "lever": 0, "ashby": 0, "yc-product": 1, "getro-accel": 1, "getro-primary": 1,
                   "builtin-product": 1, "waas-product": 1, "waas-operations": 1}


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
    kept, by_key, by_similar, by_id = [], {}, {}, {}
    for posting in ordered:
        if posting.job_id in by_id:  # the very same job found again (e.g. by two searches of one board): one row
            if by_id[posting.job_id]["posting"].source_id != posting.source_id:
                by_id[posting.job_id]["also"].append(posting.source_id)
            continue
        key = canonical_key(posting.apply_url)
        if (verified_requisition(key) and key in by_key
                and by_key[key]["posting"].source_id != posting.source_id):
            by_key[key]["also"].append(posting.source_id)
            seen = by_key[key]['seen']
            seen[posting.source_id] = min(seen.get(posting.source_id, posting.captured_at),
                                          posting.captured_at)
            continue
        entry = {"posting": posting, "also": [], 'seen': {},
                 "similar": by_similar.get(_similar(posting)),
                 'shared': by_key[key]['posting'].job_id if not verified_requisition(key) and key in by_key else None}
        by_key.setdefault(key, entry)
        by_similar.setdefault(_similar(posting), posting.job_id)
        by_id[posting.job_id] = entry
        kept.append(entry)
    notes = []
    for entry in kept:
        parts = []
        if entry["also"]:
            parts.append("Also listed by: " + ", ".join(sorted(set(entry["also"]))))
            parts.extend(f'First seen by {source}: {stamp}' for source, stamp in sorted(entry['seen'].items()))
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
    details = (f"Source: {posting.apply_url}\nEvidence: {quote}"
               f"\nFirst seen by {posting.source_id}: {posting.captured_at}" + (f"\n{note}" if note else ""))
    details += f'\nPosted: {posting.posted_at[:10]} (source metadata)' if posting.posted_at else '\nPosted: not provided by source'
    if posting.remote:
        details += '\nWork mode: Remote (source metadata)'
    preference, floor = salary_preference(posting)
    details += f'\nRole family: {role_family(posting.title) or "Unclassified"}'
    details += f'\nSalary preference: {preference} (annual USD floor {floor})'
    if preference == 'unresolved':
        details += f'\nCheck first: verify annual USD base salary reaches {floor:,}'
        if collection_region(posting.location, remote=posting.remote) == 'unresolved':
            details += '; verify permitted work location and applicable floor (US 140,000 / LATAM 70,000)'
    elif preference == 'below floor':
        details += '\nBelow salary preference floor'
    return {"Job ID": posting.job_id, "Date found": posting.captured_at[:10],
            "Job title": posting.title, "Company": posting.company, "Salary": posting.salary,
            "Location": posting.location, "Brief description": quote, "Apply link": posting.apply_url,
            "Source": posting.source_id, "Rank (prelim)": rank, "Fit": "", "Next step": "",
            "Status": "New", "Notes": "", "My rating": "", "More details": details}


def absolute(base: str, url: str) -> str:
    return urljoin(base, url)
