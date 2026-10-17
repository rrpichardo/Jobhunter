"""In-memory reviewer demonstration; no network access or production integration."""


def _job_id(row):
    value = row.get("Job ID")
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Each row must have a non-empty string Job ID")
    return value


def prepare_sheet_rows(existing_rows, incoming_jobs):
    """Return one row per Job ID, preserving existing user-owned fields.

    Jobs with different requisition IDs must remain separate even when their
    titles and companies match. Existing Status, Notes, and My rating belong
    to the user and must survive a refresh of machine-owned fields.
    Reject duplicate existing IDs rather than silently discarding user data.
    Repeated incoming IDs use their latest machine-owned values.
    """
    by_id = {}
    for row in existing_rows:
        job_id = _job_id(row)
        if job_id in by_id:
            raise ValueError(f"Duplicate existing Job ID: {job_id}")
        by_id[job_id] = dict(row)

    defaults = {"Status": "New", "Notes": "", "My rating": ""}
    for job in incoming_jobs:
        job_id = _job_id(job)
        existing = by_id.get(job_id, {})
        row = {**existing, **job}
        for field, default in defaults.items():
            row[field] = existing.get(field, default)
        by_id[job_id] = row

    return list(by_id.values())
