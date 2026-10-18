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
- Each bounded retry rereads the identity map. Only a definitively rejected
  mutation (such as HTTP 429) may be retried. An ambiguous request is never
  resubmitted merely because desired cell values appear present or absent.
  The adapter atomically includes a unique receipt in global lock cell C1 with
  each structural/value mutation. Matching owner plus that exact receipt confirms
  application after a lost response. Stale/absent receipts or failed reads leave
  a sticky unknown outcome: stop all mutations and retain the global lock.
  Retries are capped at three, respect Retry-After and stop above 60 seconds.
  HTTP redirects, auth refresh retries and transport retries are disabled.
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
requires an operator check. `sheet_mutation_unconfirmed` retains the lock:
stop all writers/schedules, establish that the server-side request has finished,
then inspect and reconcile its exact outcome before any manual unlock. Stopping
only the client, an arbitrary wait, or a stale read is insufficient proof. Never
steal a lock or remove it because it looks old. Manual unlock requires an explicit
operator decision after all writers and in-flight requests are accounted for.
Hidden sheets do not protect against manual tampering.

With no active writer/lock, rerun the same unchanged input/run ID or start a fresh
valid harvest batch. Pending batches recover first; completed run IDs verify
without rewriting only while their expected Jobs/Sources rows still match.
A newer run can legitimately change those rows; replay of an old completed ID
then reports `completed_run_changed`. Use a fresh run ID for a new batch; do not
edit an old immutable payload. Verified writes with an unconfirmed release report
`writes_verified_lock_release_unconfirmed`; an original failure/interrupt is
preserved if cleanup also fails. If an input artifact vanished before it was journaled, report
that loss and re-harvest; do not claim durable recovery from ephemeral local files.

## Remaining live acceptance checks

Before integrating this writer milestone, verify in JobHunterEnv: real posting
write and Run Log, repeated write/no duplicate, Status/Notes/rating preservation,
row sorting between runs, multiple chunks, success-but-timeout reconciliation,
interruptions before/after Jobs writes, and overlapping independent writers.
Use sanitized fixture jobs for destructive failure injection and replay; don't
repeat social collection. Isolated endpoint proof alone does not satisfy these.
Scheduled M0 and full-source V0 remain separate outstanding gates.

## Poisoned pending run: manual quarantine

A pending run that can never be replayed (corrupt journal cells, a payload that
now fails validation) blocks every later sync, by design: pending work is never
silently dropped. Only an operator, with no other writer active, may run:

```sh
uv run --locked python -m scripts.sheets_sync --quarantine-run <RUN_ID>
```

It refuses a completed run (`run_not_pending`), never creates the `_State` tab, takes
the normal global lock and renames the run's `_State` Key cells from
`m0/run/<RUN_ID>/...` to `m0/quarantined/<RUN_ID>/...`. Values are untouched, so
nothing is discarded and the evidence stays for audit. Later syncs then ignore the
run, and that run ID is refused (`run_id_quarantined`). Its Run Log row stays
`pending`, and any Jobs rows it already wrote stay as they are. Re-harvest and
submit the data under a fresh run ID. Quarantine only after reading the failure
code; it does not fix the cause.

## Handoff limitations

PR #7 is superseded by the Claude-owned replacement PR. Per-run source history
(Sources currently overwrites its rows) is still absent and is required before
full V0 acceptance. No live application check has run, and nothing here is
deployed. See CLAUDE_HANDOFF.md.

Internal `GspreadStore(namespace='_M0Test_<8–32 lowercase letters/digits>')`
uses isolated hidden data tabs and the same global lock/receipt. It is not exposed
by the production CLI. The live harness must first reject an existing namespace;
its isolation and failure-injection checks have not been run against Google.
