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
    items_fetched: int = 0
    rejected_items: int = 0
    attempts: int = 0
    http_status: int | None = None
    retry_after: float | None = None


def is_pm_candidate(title: str) -> bool:
    """Candidate sampling only; not the complete AI/location/eligibility filter."""
    return (not re.search(r"\b(intern|internship|summer associate)\b", title, re.I)
            and bool(re.search(r"\b(product manager|product lead|pm)\b", title, re.I)))


def collect_board(fetcher: JsonFetcher, *, board: str, company: str,
                  ai_company: bool, captured_at: str) -> BoardResult:
    if not isinstance(board, str) or not re.fullmatch(r"[a-zA-Z0-9_-]+", board):
        raise ValueError("invalid_board")
    board = board.lower()
    source_id = f"greenhouse:{board}"
    fetched = 0
    try:
        data = fetcher.get_json(f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true")
        if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
            raise ValueError("invalid_board_response")
        fetched = len(data["jobs"])
        jobs, seen, rejected = [], set(), 0
        for item in data["jobs"]:
            try:
                if not isinstance(item, dict):
                    raise ValueError("invalid_job")
                soup = BeautifulSoup(unescape(item.get("content") or ""), "html.parser")
                for tag in soup(["script", "style", "template", "noscript"]):
                    tag.decompose()
                for tag in list(soup.find_all()):
                    if tag.attrs is None:
                        continue
                    style = re.sub(r"\s+", "", str(tag.get("style", ""))).lower()
                    if (tag.has_attr("hidden") or tag.get("aria-hidden") == "true"
                            or "display:none" in style or "visibility:hidden" in style):
                        tag.decompose()
                text = " ".join(soup.get_text(" ", strip=True).split())
                location = item.get("location") or {}
                if not isinstance(location, dict):
                    raise ValueError("invalid_location")
                job = SourceJob(board=board, company=company, ai_company=ai_company,
                    source_item_id=item.get("id"), title=item.get("title"),
                    location=location.get("name") or "", text=text,
                    apply_url=item.get("absolute_url"), captured_at=captured_at)
            except (ValueError, TypeError, AttributeError):
                rejected += 1
                continue
            if job.job_id in seen:
                raise ValueError("duplicate_source_id")
            seen.add(job.job_id)
            jobs.append(job)
        meta = data.get("meta", {})
        total = meta.get("total") if isinstance(meta, dict) else None
        coverage = ("unknown" if type(total) is not int else
                    "complete-response" if total == fetched else "partial-response")
        if rejected:
            coverage += "-with-rejections"
        inconsistent_empty = not fetched and type(total) is int and total > 0
        status = "OK" if jobs else "failed" if rejected or inconsistent_empty else "OK-zero-jobs"
        return BoardResult(source_id, status, jobs, coverage,
            "invalid_items_quarantined" if rejected else "inconsistent_empty_response" if inconsistent_empty else "",
            fetched, rejected,
            fetcher.last_attempts, 200)
    except FetchError as exc:
        return BoardResult(source_id, "failed", error=str(exc), attempts=exc.attempts,
                           http_status=exc.status, retry_after=exc.retry_after)
    except (ValueError, TypeError, AttributeError) as exc:
        code = str(exc) if str(exc) in {"duplicate_source_id", "invalid_board_response"} else "invalid_board_response"
        return BoardResult(source_id, "failed", error=code,
                           items_fetched=fetched, attempts=fetcher.last_attempts, http_status=200)
