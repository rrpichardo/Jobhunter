"""Run artifacts belong outside Git, in operator-provisioned protected cloud storage."""

import json
import hashlib
import os
from pathlib import Path
import tempfile
import re


def artifact_path(value: str | Path) -> Path:
    path = Path(value).expanduser().resolve()
    checkout = Path(__file__).resolve().parents[1]
    if path.is_relative_to(checkout):
        raise ValueError("artifact_must_be_outside_checkout")
    return path


def new_artifact_path(path: str | Path) -> Path:
    path = artifact_path(path)
    if path.exists():
        raise FileExistsError("artifact_exists")
    if not path.parent.is_dir():
        raise ValueError("artifact_directory_missing")
    return path


def write_artifact(path: str | Path, payload: object) -> str:
    path = new_artifact_path(path)
    content = (json.dumps(payload, ensure_ascii=True, allow_nan=False, indent=2) + "\n").encode("utf-8")
    # Publish a fully flushed file atomically, without replacing an existing name.
    # Private parent-directory permissions/ACLs are required, especially on Windows.
    fd, temporary = tempfile.mkstemp(prefix=".jobhunter-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return hashlib.sha256(content).hexdigest()


def read_artifact(path: str | Path, *, expected_sha256=None) -> object:
    path = artifact_path(path)
    if path.stat().st_size > 5 * 1024 * 1024:
        raise ValueError("artifact_too_large")
    with path.open("rb") as stream:
        data = stream.read(5 * 1024 * 1024 + 1)
    if len(data) > 5 * 1024 * 1024:
        raise ValueError("artifact_too_large")
    if expected_sha256 is not None:
        if (not isinstance(expected_sha256, str) or not re.fullmatch("[a-f0-9]{64}", expected_sha256)
                or hashlib.sha256(data).hexdigest() != expected_sha256):
            raise ValueError("artifact_digest_mismatch")
    try:
        result = json.loads(data)
        stack = [(result, 0)]
        while stack:
            item, depth = stack.pop()
            if depth > 100:
                raise ValueError("invalid_json")
            children = item.values() if isinstance(item, dict) else item if isinstance(item, list) else ()
            stack.extend((child, depth + 1) for child in children)
        return result
    except (ValueError, UnicodeError, RecursionError):
        raise ValueError("invalid_json") from None


def safe_error_code(exc: Exception) -> str:
    allowed = {"artifact_must_be_outside_checkout", "artifact_directory_missing",
               "artifact_too_large", "artifact_digest_mismatch", "invalid_json",
               "duplicate_source_id", "extractions_must_be_list", "invalid_extraction_fields",
               "unknown_source_id", "duplicate_extraction", "unsupported_description_quote",
               "invalid_harvest_version", "invalid_harvest_jobs", "source_not_successful",
               "invalid_registry", "invalid_board", "invalid_source_id", "invalid_company_tag",
               "invalid_source_text", "invalid_source_location_or_url", "invalid_capture_timestamp",
               "invalid_lookback_days", "invalid_hn_result", "invalid_board_response", "hn_no_threads",
               "invalid_candidates", "invalid_extractions", "invalid_work_artifact"}
    if isinstance(exc, FileExistsError):
        return "artifact_exists"
    return str(exc) if str(exc) in allowed else "invalid_input_or_artifact"
