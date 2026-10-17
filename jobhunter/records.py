"""Validate source facts and Claude excerpts; models never choose cell writes."""

from dataclasses import dataclass
from datetime import datetime
import re
from urllib.parse import urlsplit


def https_url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = urlsplit(value)
        return (parsed.scheme == "https" and bool(parsed.hostname)
                and parsed.username is None and parsed.password is None)
    except ValueError:
        return False


@dataclass(frozen=True)
class SourceJob:
    board: str
    company: str
    ai_company: bool
    source_item_id: int
    title: str
    location: str
    text: str
    apply_url: str
    captured_at: str

    def __post_init__(self):
        if not isinstance(self.board, str) or not re.fullmatch(r"[a-zA-Z0-9_-]+", self.board):
            raise ValueError("invalid_board")
        if type(self.source_item_id) is not int or self.source_item_id <= 0:
            raise ValueError("invalid_source_id")
        if type(self.ai_company) is not bool:
            raise ValueError("invalid_company_tag")
        for field in (self.company, self.title, self.text, self.captured_at):
            if not isinstance(field, str) or not field.strip():
                raise ValueError("invalid_source_text")
        if not isinstance(self.location, str) or not https_url(self.apply_url):
            raise ValueError("invalid_source_location_or_url")
        try:
            stamp = datetime.fromisoformat(self.captured_at)
            if stamp.utcoffset() is None:
                raise ValueError
        except (TypeError, ValueError):
            raise ValueError("invalid_capture_timestamp") from None

    @property
    def job_id(self) -> str:
        return f"greenhouse:{self.board}:{self.source_item_id}"


def validate_extractions(jobs: list[SourceJob], payload: object) -> list[dict]:
    """M0 contract: Claude chooses only an exact source excerpt, at most 300 chars.

    Title, company, location, URLs, identity and dates are from the API. No full
    eligibility decision is made. Absent salary remains unknown (blank).
    """
    sources = {job.job_id: job for job in jobs}
    if len(sources) != len(jobs):
        raise ValueError("duplicate_source_id")
    if not isinstance(payload, list):
        raise ValueError("extractions_must_be_list")
    output, seen = [], set()
    for item in payload:
        if not isinstance(item, dict) or set(item) != {"job_id", "description_quote"}:
            raise ValueError("invalid_extraction_fields")
        job_id, quote = item["job_id"], item["description_quote"]
        if not isinstance(job_id, str) or job_id not in sources:
            raise ValueError("unknown_source_id")
        if job_id in seen:
            raise ValueError("duplicate_extraction")
        job = sources[job_id]
        if not isinstance(quote, str) or not quote.strip() or len(quote) > 300 or quote not in job.text:
            raise ValueError("unsupported_description_quote")
        seen.add(job_id)
        output.append({
            "Job ID": job.job_id, "Date found": job.captured_at[:10],
            "Job title": job.title, "Company": job.company, "Salary": "",
            "Location": job.location, "Brief description": quote,
            "Apply link": job.apply_url, "Source": f"greenhouse:{job.board}",
            "Rank (prelim)": 1 if job.ai_company else 3,
            "Fit": "", "Next step": "", "Status": "New", "Notes": "",
            "My rating": "", "More details": f"Source: {job.apply_url}\nEvidence: {quote}",
        })
    return output
