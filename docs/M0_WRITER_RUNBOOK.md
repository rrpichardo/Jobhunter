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
- Multi-source delivery reconciles matching canonical employer links against
  existing Jobs rows. It retains the existing Job ID and original Source, and
  records first-seen discovery dates in More details. Distinct requisitions from
  the same source remain separate. `ambiguous_existing_job_identity` means more
  than one existing row could match; reconcile those rows manually while keeping
  user notes before retrying. The writer never deletes or combines existing rows.
  Automatic cross-source merging requires a known ATS requisition identity or
  matching explicit Greenhouse `gh_jid` application parameters. Shared unknown
  custom/generic links keep incoming rows separate with possible-duplicate notes,
  even when several other-source rows share the link. Multiple conflicting
  verified identities remain an error rather than choosing which user data wins.
- A source blocked partway through detail collection remains `blocked` with its
  actual HTTP/error evidence. Jobs validated before that failure may still be
  delivered when the artifact explicitly accounts for them. That does not turn
  the source into a success or permit further requests to the blocked source.
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

## Live test harness (JobHunterEnv only)

`scripts/live_harness.py` runs the remaining live acceptance checks against Google.
Each scenario gets a fresh hidden `_M0Test_<12 hex>` namespace and never reads or
writes the real Jobs, Sources, Run Log or _State tabs. A guard rejects any request
outside that namespace or the shared lock tab. No source or social fetches happen,
calls are paced (default 1.5 s apart, `--interval`), and fixture tabs are kept.
The harness never unlocks: if a lock already exists it stops untouched.

```sh
uv run --locked python -m scripts.live_harness                      # clean suite
uv run --locked python -m scripts.live_harness --scenario overlap   # one scenario
```

Clean scenarios (each must end with the lock released by the writer itself):
`chunks`, `repeat`, `preserve`, `sorted`, `timeout_after_apply`,
`timeout_after_apply_structural`, `interrupt_after_apply`, `overlap` (two independent
processes; exactly one must win, the other must report `writer_locked`).
Opt-in only: `timeout_before_apply` and `interrupt_before_apply` deliberately leave
the global lock in place (exit 3). Run them only with operator agreement, since the
lock blocks the real writer until an operator decides how to clear it.
Read each scenario's PASS/FAIL lines in the real command output.

## Source probe and multi-source delivery

`scripts/source_probe.py` makes one polite GET per source in `sources/v0_sources.yaml` (no
retries; 401/403/406/429 mark the source `blocked` and stop it at once), parses it with
`jobhunter/postings.py`, applies the PLAN filter (PM title, AI signal or AI-tagged company,
US/remote/unknown location, no interns) and keeps at most 8 matches per source and 150 in total.
The Brief description is an exact leading excerpt (300 characters) of source text, chosen by
Python, never by a model. Sources needing keys, accounts or a labeled mailbox are recorded
`needs setup` with no request. YC, a16z, Getro and HN are listing-only: counted and recorded as
`OK-zero-jobs`, nothing delivered, until a detail fetch exists. Guessed company boards that
answer 404 are dropped as non-responders. No social, Gmail or logged-in access happens here.

Y Combinator (the same jobs Work at a Startup lists, without its login), Built In and the Getro
VC boards (Accel, Primary) are detail sources: the listing is parsed, up to 8 shortlisted PM
titles per source get one polite GET of their own job page for the description, employer and
place, and a refusal (401/403/406/429) stops that source at once. a16z and Hacker News are
still count-only. The fetched pages were checked against each site's robots.txt.

Cross-source duplicates are merged only when two different sources link the same employer
posting (the same Greenhouse/Lever/Ashby requisition, or the same URL once tracking parameters
are dropped; job-identifying parameters such as `gh_jid` are kept). The company-board row wins
and lists the other sources in More details. Company-and-title similarity alone never merges:
it adds a "Possible duplicate ... needs review" note and keeps both rows. A source never merges
its own postings.

```sh
uv run --locked python -m scripts.source_probe --output /private/run/probe.json
uv run --locked python -m scripts.sheets_sync --input /private/run/probe.json --run-id m1-probe-001
```

The artifact uses `schema_version: 2` (`sources` list plus `jobs`); `sheets_sync` writes every
source's evidence and all jobs in one locked run. For schema 2 exit 0 means the readback was
verified; failed, blocked and needs-setup sources are recorded evidence, shown as
`source_problems_recorded=N`. The Run Log status reads
`complete-with-source-failure` whenever any source is not OK or OK-zero-jobs, including `needs setup`.

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
its isolation and failure-injection checks have not been run against Google;
the harness above passed its eight clean scenarios in JobHunterEnv (V0_VERIFICATION.md).
