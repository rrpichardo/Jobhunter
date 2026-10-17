"""Run artifacts belong outside Git, in operator-provisioned protected cloud storage."""

import json
import os
from pathlib import Path


def artifact_path(value: str | Path) -> Path:
    path = Path(value).expanduser().resolve()
    checkout = Path(__file__).resolve().parents[1]
    if path.is_relative_to(checkout):
        raise ValueError("artifact_must_be_outside_checkout")
    return path


def write_artifact(path: str | Path, payload: object) -> None:
    path = artifact_path(path)
    content = json.dumps(payload, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
    # Exclusive creation: retries must not overwrite prior evidence or pending work.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def read_artifact(path: str | Path) -> object:
    path = artifact_path(path)
    if path.stat().st_size > 5 * 1024 * 1024:
        raise ValueError("artifact_too_large")
    return json.loads(path.read_text(encoding="utf-8"))
