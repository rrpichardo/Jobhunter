# M0 writer/recovery execution plan

Binding specification: docs/PLAN.md §Python batch writer and M0 acceptance.
One implementation owner: Codex on codex/m0-sheet-sync, starting from merged
connection checkpoint PR #6 (fa899c3). The user chose to continue in Codex; keep
CLAUDE_HANDOFF.md current for a later transfer. No new hosting service/account,
paid API or billing activation. Production executes in JobHunterEnv only.

## Established prerequisites

The GCP network secret now exists and was saved with explicit user authorization.
It is restricted to the Sheets host/workbook path, Sheets scope, no impersonation.
User accepted continued use of the disclosed dedicated key; keep values out of
Git/logs/handoff. Initial gspread read passed at0260388. At229a97b, a single atomic
structural request and RAW values request passed on hidden _M0AuthProbe; the
formula-like literal read back unchanged. This is endpoint proof, not a writer,
recovery, lock or schedule test. Read ATTEMPTS.md; do not reset existing counters.

## Implementation and interfaces

1. `sheet_records.py`: normalize the Python-produced M0 row contract; derive
   deterministic keyed cell plans from current headers/IDs. Reject duplicates or
   ambiguous existing data. Preserve existing user columns and first-seen date.
   Tests first failed for missing module, then passed for reordered headers,
   sorted rows, duplicate input, extra user columns and invalid values.
2. `sheet_io.py`: gspread adapter for approved tabs, RAW values and unformatted
   readback. Grow grids by appendDimension only. Bounded caller retries; sanitized
   error code/status/finite Retry-After only, no provider bodies. Atomic lock
   addSheet + owner token updateCells. Isolated adapter tests first failed/passed.
3. `sheet_lock.py`: fixed title/ID lock, fresh random owner token per invocation,
   confirmed ownership after uncertain creation, no expiry/stealing. Ownership
   check before one release attempt; never repeat an uncertain delete. Tests
   cover overlap, unknown acquire and a new owner after uncertain release.
4. `sheet_journal.py`: bounded ASCII JSON chunks (<=40,000 chars/cell, <=1 MiB
   total) and SHA-256 manifest in one atomic `_State` values batch before Jobs
   mutation; verify saved values. Keep only non-secret normalized machine data.
   Completed manifests clear payload chunks. Tests cover multi-cell payloads,
   corruption, input caps and unrelated social-allowance preservation.
5. `sheets.py`: normalize/source evidence, keyed RAW upserts in bounded chunks,
   fresh reads after any uncertain write, verify affected IDs/values. Persist
   pending Run Log before Jobs mutation; only mark complete after all readbacks.
   Recover pending batches under the lock before new input. Test insertion succeeds
   but times out, partial chunks, interrupted journal/Jobs/log, failed source,
   retry exhaustion and long Retry-After. No full eligibility claim.
6. `scripts/sheets_sync.py`: validate artifact/extraction before Google access;
   connect through the network-secret helper; sanitized exit/result only.
   Reject partial extraction; failed-source artifacts may record failure evidence.
7. Runbook and evidence: exact commands, lock recovery and row-move limitations;
   read-only opposite-agent review, Linux/Windows CI, real cloud writer/recovery/
   overlap checks, fresh review after substantive fixes. Merge only after gates.

## Rulings and completion ledger

- New jobs use deterministic blank-row ranges rather than the append endpoint.
  This still inserts new records; after uncertain success it rereads IDs and
  plans remaining changes, avoiding blind append duplication. Tests model the
  same insertion-success-but-timeout scenario required by the specification.
- Google documents all Sheets requests as atomic and recommends <=2 MiB payloads:
  https://developers.google.com/workspace/sheets/api/limits . Journal batches use
  <=1 MiB of serialized content; ordinary batches have an additional size cap.
- The structural lock serializes compliant callers; it is not fencing against
  editors manually deleting it. Recovery requires confirming all previous writers
  stopped. No automatic stale-lock stealing or extra storage provider.
- Code and behavior tests exist for tasks 1–6. Full suite currently passes 107
  tests/10 subtests locally. No production writer cloud test or review yet.
- Still outstanding: fresh whole-change Claude review, Linux/Windows CI, actual
  M0 row delivery/repeat write and fixture-based recovery/concurrency tests.
  Scheduling/routine verification remains required for complete M0/V0.
