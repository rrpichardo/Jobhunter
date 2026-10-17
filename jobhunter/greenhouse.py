"""M0 public Greenhouse route. Full-source access is distinct from extraction sample."""

from dataclasses import dataclass, field
from html import unescape
import re

from bs4 import BeautifulSoup

from jobhunter.fetch import FetchError, JsonFetcher
from jobhunter.records import SourceJob


@dataclass
class BoardResult:
    source_id: str
    status: str
    jobs: list[SourceJob] = field(default_factory=list)
    coverage: str = "unknown"
    error: str = ""


def is_pm_candidate(title: str) -> bool:
    """Candidate sampling only; not the complete AI/location/eligibility filter."""
    return (not re.search(r"\b(intern|internship|summer associate)\b", title, re.I)
            and bool(re.search(r"\b(product manager|product lead|pm)\b", title, re.I)))


def collect_board(fetcher: JsonFetcher, *, board: str, company: str,
                  ai_company: bool, captured_at: str) -> BoardResult:
    if not isinstance(board, str) or not re.fullmatch(r"[a-zA-Z0-9_-]+", board):
        raise ValueError("invalid_board")
    source_id = f"greenhouse:{board}"
    try:
        data = fetcher.get_json(f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true")
        if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
            raise ValueError("invalid_board_response")
        jobs, seen = [], set()
        for item in data["jobs"]:
            if not isinstance(item, dict):
                raise ValueError("invalid_job")
            soup = BeautifulSoup(unescape(item.get("content", "")), "html.parser")
            for tag in soup(["script", "style"]):
                tag.decompose()
            text = " ".join(soup.get_text(" ", strip=True).split())
            location = item.get("location") or {}
            if not isinstance(location, dict):
                raise ValueError("invalid_location")
            job = SourceJob(board=board, company=company, ai_company=ai_company,
                source_item_id=item.get("id"), title=item.get("title"),
                location=location.get("name") or "", text=text,
                apply_url=item.get("absolute_url"), captured_at=captured_at)
            if job.job_id in seen:
                raise ValueError("duplicate_source_id")
            seen.add(job.job_id)
            jobs.append(job)
        meta = data.get("meta", {})
        total = meta.get("total", len(jobs)) if isinstance(meta, dict) else None
        coverage = "complete-response" if type(total) is int and total == len(jobs) else "partial-response"
        return BoardResult(source_id, "OK" if jobs else "OK-zero-jobs", jobs, coverage)
    except FetchError as exc:
        return BoardResult(source_id, "failed", error=str(exc))
    except (ValueError, TypeError, AttributeError):
        return BoardResult(source_id, "failed", error="invalid_board_response")
