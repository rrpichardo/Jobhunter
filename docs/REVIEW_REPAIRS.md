# Codex repairs awaiting Claude review

The user authorized Codex to fix the ten findings posted on PRs #40–#50 and submit one PR for Claude while Claude is
unavailable. This is a repair handoff, not a deployment. PENDING section 0 remains the authoritative decision/status list.

## Review the fix delta

- Base snapshot: `codex/review-findings-base`, exactly `e3eef3fa9a98bc804befc16e2e840486c4820c46` (the pre-repair combined run branch).
- Head: `codex/repair-review-findings`. The PR description records the full pushed head SHA; re-read it before reviewing.
- Request: Claude reviews this delta read-only, reports findings with file/line/scenario, and names the exact head reviewed.
  Codex owns implementation and any fixes during this repair round. The existing Claude GitHub integration is the review route;
  a green/skipped action without an actual current-head report is not approval. No same-agent review is requested.
- This PR must never target main. Neither the combined branch nor the snapshot is an integration PR for the feature stack.
  The combined branch is fast-forwarded to the repair head so its code and documents stay consistent for future authorized runs.

## Repairs and original PRs

| Original PR | Repair | Relevant changes |
|---|---|---|
| #40 | Dispose of temporary X session after workbook/reservation failures | `scripts/x_collect.py`, resource-lifecycle regressions |
| #43 | Close the authenticated LinkedIn browser on the same startup failures | `scripts/linkedin_collect.py`, resource-lifecycle regressions |
| #44, #45 | Preserve the earliest discovery time for each secondary source in same-ID merges | `jobhunter/postings.py`, two-source regressions |
| #46 | Put the installed pinned uv first on PATH for all copied runbook commands | `docs/LIVE_RUN_PROMPT.md` |
| #49 | Require complete, unique sample-ID coverage before comparing models | `scripts/eval_reading.py`, safe error code, eval tests/docs |
| #50 | Emit only trusted candidate IDs and explicitly allowed rejection codes | `jobhunter/post_facts.py`, trace tests/docs |
| #47 | Canonical verified-requisition identity; retain distinct roles at generic links | `jobhunter/post_facts.py`, newsletter tests |
| #47 | Reconcile unique verified legacy newsletter rows while retaining their original IDs and user fields | `jobhunter/sheet_records.py`, preservation/repeat/ambiguity tests |
| #48 | Compare resolved output paths before any session/reservation/request | `scripts/linkedin_collect.py`, alias-path regression |

The consolidated regressions are in `tests/test_review_repairs.py`. No source limits, salary rules, role-plural rules,
reply policy, scheduling decision or LinkedIn access decision was changed. The original eleven PR heads remain as reviewed.

## Existing newsletter rows

New verified requisitions use `alirohde:v2:<canonical-key hash>`. A unique existing `alirohde:<16-hex>` row at that same
verified requisition keeps its old Job ID, Status, Notes, My rating and Date found. Matching is repeated on every sync,
so refreshing a tracking link does not cause the following run to append a duplicate. Multiple matching verified rows
raise `ambiguous_existing_job_identity`; resolve their identity and user fields manually before retrying. No automatic
merge/deletion/renaming of existing rows is performed.

A general careers link never proves identity, even with the same title and company. Such old rows are left intact;
incoming distinct identities are retained with a possible-duplicate/needs-review note. Existing uncertain rows must be
reviewed by the operator; the fix does not infer that two generic-link rows are the same job or the same recruiting cycle.

## After review

1. Resolve actionable Claude findings in new Codex commits, rerun affected checks, request Claude on the resulting full SHA.
   Carry the attempt counters in ATTEMPTS forward; the user authorized this additional round, not a reset of historical limits.
2. After the repair delta is approved, apply the relevant repairs and regressions to each original feature branch, respecting
   its dependencies and the merge-conflict recipes. The consolidated test file imports the combined features, so port the
   applicable tests to their feature suites when backporting; do not blindly cherry-pick it onto a branch missing those modules.
3. Obtain the reviews required for each resulting head and green CI before any feature PR merges; old reviews do not cover
   the backported/integrated revision. Do not merge the snapshot/combined stack into main to avoid that work.
4. Keep PENDING section 0 and the combined run branch current after each push. A18, A3 and all other unanswered choices remain open.
5. The next separately authorized real run must still copy `trace:` lines unchanged into its final report and show
   `empty:company` for the missing-company cases. One live attempt per social source per New York day still applies.
