# M0 Sheet writer and recovery

The writer is a proposed implementation until its PR review and live tests pass.
It is not a scheduled deployment or the complete V0 collector. Use the actual
JobHunterEnv cloud environment; no local production process is needed.

## Inputs and authentication

The GCP network secret is saved in JobHunterEnv for this workbook's Sheets API
path, with the Sheets scope and no impersonation. Python uses AnonymousCredentials;
the proxy authenticates requests after they leave the VM. Initial read and isolated
RAW/structural endpoint checks passed; see V0_VERIFICATION.md and ATTEMPTS.md.
No private key, access token or credential file belongs in the VM or these commands.

Required non-secret environment settings:

```text
JOBHUNTER_GOOGLE_AUTH_MODE=network-secret
JOBHUNTER_SPREADSHEET_ID=1kG1QeLhYmiImPW4pMtEDIHI6I-dK1Ztig_77B8mGrPw
```

Generate the input with `scripts.validate_extractions`, following
M0_EXTRACTION_PROMPT.md and retaining the trusted original harvest digest. Do not
have a model construct normalized cell updates. The input artifact must be in a
private directory outside the checkout. No raw mail, credentials or cookie data.

After the proposed revision is approved, run:

```sh
uv sync --locked
uv run --locked python -m scripts.sheets_sync \
  --input /private/run/records.json --run-id m0-example-001
```

Use equivalent absolute paths on Windows during development. IDs contain only
letters, digits, hyphen or underscore (1–80 characters). A run ID identifies an
immutable input batch; reusing it for changed data fails. Omit it for a new UUID.
`--chunk-size` is 1–100 cell ranges per request, with a separate payload-size cap.
Exit 0 means current job/source/run readback verified; exit 2 records a failed
source or a sanitized sync failure, never successful deployment. Exit 130 means
interrupted work may remain. A failed harvest artifact with no jobs may be sent
through this same CLI to record failed-source evidence and recover prior pending
work; incomplete Claude extraction batches are rejected before Google access.

## Guarantees and operating constraints

- Jobs are matched by Job ID after reading current headers and rows. Sorting
  between runs works. Duplicate existing IDs, ambiguous headers and nonempty
  unkeyed rows stop the sync. Incoming duplicates use the last record.
- Existing Status, Notes, My rating and Date found are excluded from updates.
  New rows initialize Status=New and blank Notes/My rating. Extra user columns on
  existing rows are preserved. Every value write uses RAW, including formula-like
  job text. This is candidate collection, not a full eligibility decision.
- Do not sort, insert, delete or move underlying Jobs rows during a sync. Use
  filter views while writing; edits to existing user-owned cells remain supported.
- Every write attempt starts from a fresh identity map. New jobs use explicit
  blank-row ranges, not a blind append retry. After an uncertain insertion, read
  IDs again before deciding which cells still need writing. Retries are capped
  at three, respect Retry-After and stop if the requested wait exceeds 60 seconds.
- Pending normalized machine records and source evidence are journaled as bounded
  JSON chunks plus a hash/manifest in one atomic `_State` values request before
  Jobs mutation. No user notes or secret state are journaled. Complete manifests
  retain run identity/digest; their payload chunks are cleared after readback.
- Run Log gets a pending row before Jobs mutation. If the API later stops working,
  that row and journal remain incomplete; the CLI reports the sanitized failure.
  Do not claim the failure reason was durably saved if Google was unavailable.
  Recovery replays pending batches before a new batch and updates the same IDs.

## Lock and interrupted runs

All callers must use the same workbook lock. It atomically creates hidden
`_JobHunterLock` (fixed sheet ID 1874202601) and its random owner/timestamp in one
structural batch. An existing ID/title blocks another caller. After an uncertain
acquire, only a matching owner read permits writing; there is no automatic retry
of lock creation. Lock release checks ownership and submits at most one deletion.
An uncertain deletion is read back, never repeated against a possible later owner.

There is no lease expiry or lock stealing. The `_State` run marker/journal is not
an atomic lock. A crash may leave the structural lock in place. `writer_locked`,
`lock_acquisition_unconfirmed`, `lock_release_unconfirmed` or `lock_ownership_lost`
requires an operator check. Confirm **every prior writer is stopped**, inspect the
non-secret owner/timestamp and pending manifests, then explicitly authorize a
single manual lock removal. Do not delete it because it looks old or while another
session might resume. Hidden sheets do not protect against manual tampering.

With no active writer/lock, rerun the same unchanged input/run ID or start a fresh
valid harvest batch. Pending batches recover first; completed run IDs verify
without rewriting. If an input artifact vanished before it was journaled, report
that loss and re-harvest; do not claim durable recovery from ephemeral local files.

## Remaining live acceptance checks

Before integrating this writer milestone, verify in JobHunterEnv: real posting
write and Run Log, repeated write/no duplicate, Status/Notes/rating preservation,
row sorting between runs, multiple chunks, success-but-timeout reconciliation,
interruptions before/after Jobs writes, and overlapping independent writers.
Use sanitized fixture jobs for destructive failure injection and replay; don't
repeat social collection. Isolated endpoint proof alone does not satisfy these.
Scheduled M0 and full-source V0 remain separate outstanding gates.
