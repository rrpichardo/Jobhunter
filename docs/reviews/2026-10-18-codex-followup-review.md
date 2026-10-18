# Codex follow-up review — PR #11 at 19e9e77

Date: 2026-10-18 UTC. Reviewed checkout: `/tmp/jobhunter-postmerge-review`.

- Base: `36539f47ee6c550c9cf5e2f521831a17ad13f16c`.
- Exact reviewed HEAD: `19e9e7734ec9e946a5a8f62987b3904bc528f031`.
- HEAD was verified before and after checks. The checkout stayed clean; no tracked files were edited.

**Verdict: changes needed — two confirmed P2 salary-filter issues remain.** The provenance and explicit-remote repairs address their original reproduced failures, with no additional provenance/replay/user-cell defect found in the reviewed paths. The original salary issue is partly repaired: 401k and an unrelated unqualified USD bonus no longer qualify, but a locally annual-labelled bonus still does, and valid explicit salary forms regress.

This independent Codex re-review occurs **before PR #11 merges**, following the earlier post-merge review of main `36539f4`. It does not retroactively supply a pre-merge review for PRs #8–#10. The original changes-requested report at `/workspace/scratch/jobhunter-codex-final-review.md` is unchanged. This is a Codex-session review, not the GitHub Codex bot.

## Confirmed actionable findings

### 1. P2 — Preserve explicitly annual USD salary formats when binding currency and period

Location: `jobhunter/postings.py:142–147`.

Concrete scenario: an on-site Colombia or Dominican Republic posting supplies `USD $70,000 - $90,000 per year`. The new currency/amount regex does not allow the dollar sign after USD, so it finds no salary expression and returns False. Likewise, `USD 70,000 - 90,000 a year` and `USD 70,000 - 90,000 (annual)` fail the period-adjacency regex. All three express an annual USD range above the floor and previously matched.

Impact: the repair newly drops qualifying regional on-site/hybrid roles. These examples have explicit currency and annual period; they do not require inference or relaxed treatment of unknown units.

Reproduction evidence: the standalone script `/workspace/scratch/jobhunter-codex-followup-repro.py` loads the baseline function from the exact base commit and compares it with the function at reviewed HEAD. Each expression produces `base=True head=False`. Calls through `collection_location_match('Colombia (on-site)', salary)` also return False at HEAD. The script assertions pass.

Retain supported explicit dollar and annual-period notation while continuing to bind currency, amount and period to the same pay expression; add regressions for these three forms.

### 2. P2 — Exclude locally annual-labelled bonus figures from the salary exception

Location: `jobhunter/postings.py:144–154`.

Concrete scenario: salary text is `USD 50,000 - 60,000 per year + USD 100,000 annual bonus`. The first range is below the floor. The later USD 100,000 matches `annual_after` because the next word is `annual`, and the parser never checks that the amount is explicitly labelled a bonus. It therefore accepts this unrelated amount as qualifying annual salary.

Impact: an on-site regional role still qualifies without a salary range reaching USD 70,000. A labelled bonus cannot establish the salary exception. This is the same class of remaining false positive as the original benefits/bonus finding, despite the repair correctly rejecting `401k` and `USD 100,000 bonus` without an adjacent annual token.

Reproduction evidence: the standalone script asserts:

```text
regional_salary_match('USD 50,000 - 60,000 per year + USD 100,000 annual bonus') == True
collection_location_match('Colombia (On-site)', same_text) == True
```

Both assertions pass at the exact reviewed HEAD. Distinguish salary/base pay from locally labelled bonus/commission figures. Preserve a genuinely qualifying salary range even if an unrelated bonus follows it.

## Verification actually run

```sh
cd /tmp/jobhunter-postmerge-review
/tmp/jobhunter-review-tools/bin/uv run --locked --cache-dir /tmp/jobhunter-uv-cache python -m pytest -q
```

Result: **318 passed, 10 subtests passed in 0.64s**, exit 0, independently rerun. The passing suite does not cover the findings above.

```sh
/tmp/jobhunter-review-tools/bin/uv run --locked --cache-dir /tmp/jobhunter-uv-cache python /workspace/scratch/jobhunter-codex-followup-repro.py
```

Result: exit 0. Beyond the salary findings, this script independently exercises the actual writer through `GspreadStore` and `FakeWorkbook`, not a live Google connection:

- A same-harvest direct/aggregator merge retains both full source timestamps, including an alternate timezone.
- Five subsequent direct-only runs keep identical provenance text, one Jobs row, Status, Notes, My rating and Date found; no replay growth occurs.
- A 10:30 +02:00 observation correctly replaces a 09:00 UTC observation as earlier.
- Legacy date-only evidence remains date-only; an old `Also listed by` source with an unknown historical time is retained without an invented timestamp.
- Both the original 401k expression and the later USD bonus expression without a local annual token are now rejected.

```sh
git diff --check 36539f47ee6c550c9cf5e2f521831a17ad13f16c 19e9e7734ec9e946a5a8f62987b3904bc528f031
git status --porcelain=v1
git rev-parse HEAD
```

Result: diff check exit 0; empty working-tree status; exact HEAD `19e9e7734ec9e946a5a8f62987b3904bc528f031`.

## Scope and limits

Read current `AGENTS.md`, full `docs/PLAN.md`, `docs/REVIEW_WORKFLOW.md` and `CLAUDE.md`. Inspected the implementation/test diff against the exact base, all of current `jobhunter/sheet_records.py`, surrounding posting/parser/dedupe/row-building behavior in `jobhunter/postings.py`, added tests in `tests/test_postings.py` and `tests/test_cross_source_sync.py`, and changed attempt/handoff/verification documentation. Existing writer/lock/journal behavior was reviewed in the prior cumulative report and its regression suite was rerun here; this follow-up focuses on the PR #11 repairs rather than repeating that entire review.

The original remote omissions now propagate Lever `workplaceType=remote` and WWR's remote-source contract, preserve source location and expose work-mode evidence. Their current regressions pass. No full employer eligibility is asserted.

Accepted bounds remain separate: eight detail pages per source, 150 jobs globally, conservative ambiguous-location handling, operator reconciliation of conflicting verified identities, and unknown historical source times. Durable per-run source history, current-head live verification, cloud scheduling, browser/session restoration and deployment/observation evidence remain existing open gates. They are not counted as new findings in this report.

No live source/Google network, secret inspection, external posting, pushes, merges or tracked-file edits occurred. Only this follow-up report and its reproduction script outside Git were written. These offline checks do not establish deployment or external runtime behavior. No unverified hypothesis or optional improvement is counted as a finding.
