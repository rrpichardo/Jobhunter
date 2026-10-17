"""Isolated review probe. No network access; never merge into production."""


def prepare_sheet_rows(existing_rows, incoming_jobs):
    """Return one row per Job ID, preserving existing user-owned fields.

    Jobs with different requisition IDs must remain separate even when their
    titles and companies match. Existing Status, Notes, and My rating belong
    to the user and must survive a refresh of machine-owned fields.
    """
    by_id = {row["Job ID"]: dict(row) for row in existing_rows}
    seen = set()

    for job in incoming_jobs:
        identity = (job["Company"], job["Job title"])
        if identity in seen:
            continue
        seen.add(identity)

        row = dict(job)
        row["Status"] = "New"
        row["Notes"] = ""
        row["My rating"] = ""
        by_id[job["Job ID"]] = row

    return list(by_id.values())
