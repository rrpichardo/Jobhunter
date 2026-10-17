# M0 writer/recovery implementation plan (draft; begin only after PR #5 merge)

Spec: docs/PLAN.md writer/M0; user approval: in-memory service-account variable fallback if GCP secret type unavailable; no new hosting. Dedicated writer only workbook Editor, no project IAM roles, Sheets only.

The initial draft below is historical. The updated prerequisites/ledger supersede
its credential-factory and account-access assumptions.

Files: jobhunter/sheets.py (normalized records, safe header mapping, RAW upserts/reconciliation/state/run evidence), jobhunter/sheet_lock.py (atomic structural lock), jobhunter/google_auth.py (network-secret client; sanitized failures), scripts/sheets_sync.py (CLI), tests/test_sheets*.py (sanitized model of Google Sheets semantics), docs/M0_WRITER_RUNBOOK.md.

Acceptance: tests fail before behavior; duplicate incoming IDs deduped and duplicate existing IDs/ambiguous headers abort; preserve Status/Notes/My rating; preserve original Date found; support changed header order and between-run sorting; never sort or move rows while writing; new rows Status New/Notes+rating blank; RAW everywhere; bounded chunk writes; uncertain append must reread IDs before retry; verify affected IDs/cells before completion.

State: Sheet _State stores only normalized pending machine records, run marker and nonsecret retry/allowance counters. Journal pending work before Jobs mutation; recover pending work next sync; completion recorded after readback. No second job database. Unsupported protected state or auth cannot be silently replaced.

Lock candidate: one atomic spreadsheets.batchUpdate adds hidden _JobHunterLock sheet with fixed unique sheetId/title plus owner/run/timestamp cells. Google documents atomic all-or-nothing batches and uniqueness errors for existing titles. Only successful owner writes. On ambiguous acquisition, read owner; confirmed own token can continue; absent/foreign/unknown -> abort without blind retry. No expiry/stealing. Release once; on ambiguous deletion never repeat blindly, because a later owner could have acquired the recreated sheet. User manually resolves orphan only after confirming no active owner. This is an inferred candidate requiring live proof, not a _State-marker lock. No new provider or service. References: https://developers.google.com/workspace/sheets/api/guides/batch and https://developers.google.com/workspace/sheets/api/guides/migration.

Test recovery: interruption before journal, after journal before jobs, after append before done, append succeeds but raises timeout, partial chunk completion, duplicate rows, overlap/fixed lock collision, stale marker, failure release unknown, sorting between runs and multi-chunk user-data preservation.

Live gates: Google account access is now working; dedicated service account, workbook sharing and GCP network secret were provisioned with user approval. Actual Python API access and harmless write/lock endpoints still need proof. Do not claim live writer/recovery/lock until real credentials+workbook access. Offline code can proceed after PR #5 integration. PR review/test/merge follow standing policy and maximum3 repair cycles.

## Updated prerequisites and execution ledger

- PR #5 merged at d77842d; start this branch from that revision.
- Google account now accessible; dedicated project and role-free service account
  created, Sheets API enabled, workbook shared Editor after explicit approval.
- GCP network secret type is now available. User provisions key directly into
  proxy-backed secret, host/path restricted and Sheets scope only. Prefer gspread
  with AnonymousCredentials: proxy authenticates after requests leave VM, so no
  key or access token is exposed to Python. This is an implementation candidate
  pending a read-only live test; retain approved in-memory fallback only if needed.
- Ruling: no generated key file is read by an agent or copied into the repository.
  Do not inspect UI while user enters the secret. No new external hosting.
- Ruling: the lock is for compliant single-writer clients, not protection against
  manual lock deletion or editors tampering with it. Manual recovery requires
  confirming every prior writer stopped; no automatic timeout-based lock stealing.
- Next task: prove preferred authentication through actual JobHunterEnv, then
  write failing writer/recovery/lock tests and implement the bounded M0 writer.
