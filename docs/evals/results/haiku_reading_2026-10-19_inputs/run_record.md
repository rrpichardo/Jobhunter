# Run record, October 19, 2026 (what the two helper agents did)

A record made during the session, not something the saved inputs let you recompute. Everything else in
`../haiku_reading_2026-10-19.md` can be re-derived from the files in this folder.

## The pool (checked against the pool file at 21:55 UTC the same day)

- 266 top-level comments in the 28-day window, captured 2026-10-19 20:10 UTC, none truncated.
- All 266 are from one thread, "Ask HN: Who is hiring? (October 2026)" (story 49922569), posted 2026-10-01 to 2026-10-15.
  The collection tool also selected the September thread (story 49522897), but none of its comments fall inside the window.
- 15 of the 266 mention a collected role (the shared role scan, `jobhunter.postings.ROLE_TEXT`).
- The pool file is not saved here: it holds third-party email addresses. Its SHA-256 is
  `cfe07fc01bf089be31c865985a8cfc92100e0f59374a5cea9236c4e58e0b27cf`.

## The two helpers (scan of their saved activity logs, 21:55 UTC)

| | Sonnet helper | Haiku helper |
| --- | --- | --- |
| Tool calls | 12: 11 shell commands and the final hand-back message | 12: 11 shell commands and the final hand-back message |
| What the 11 shell commands did | 10 reads of the sample, 10 posts at a time (`eval_sample.json` only), then 1 command that wrote its facts file | the same |
| Mentions of the other model's facts file | 0 | 0 |
| Final write step | a list of 19 hand-typed fact entries; no regular expressions, no search, no loop over the posts | the same, 19 entries |
| Tokens (as reported by the harness) | 115,457 | 135,630 |
| Time (as reported by the harness) | 122 s | 138 s |

Both helpers received the same instructions (`instructions_template_both_models_received.txt`, with only the output file name
differing) and ran at the same time (about 20:10 to 20:13 UTC). The hand-typing matters: the instructions said to read every
post and not to write code that picks titles by pattern, and the logs show both complied.

## What this does not prove

Two readings by two models that differ in 11 of 19 facts are consistent with independent work, and the logs show neither opened
the other's file, but nothing here rules out shared influence from the identical instructions.
