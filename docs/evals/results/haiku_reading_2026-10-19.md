# Haiku vs Sonnet on the reading step: result of the first run (October 19, 2026)

Plain-language summary first, details after. The plan and the rule are in
[`../HAIKU_READING_EVAL.md`](../HAIKU_READING_EVAL.md). An independent review of this page (October 19) corrected several
statements in an earlier version; the corrections are folded in below.

## Answer in one paragraph

On 100 real Hacker News hiring posts, Haiku and Sonnet gave **the same answer on all 100** and found **the same 15 jobs**.
Read that with care: **85 of the 100 posts name no role**, so "nothing here" was the easy, correct answer for both. The
informative part is the **15 posts that name a role**: the two models agreed on all 15 and on every job in them. Rules 1 and 2
pass. **Nothing is switched yet.** Rule 3 is the user's: read the posts and the differences below (posts 3 and 12 matter most).
Until then the reading step stays on Sonnet.

## What was run

| Step | Done by | What happened |
| --- | --- | --- |
| 1. Collect | code | All top-level comments in the last 28 days from the Hacker News "Ask HN: Who is hiring?" threads: **266 comments**, all from the October thread (the September thread's comments are older than 28 days), posted 2026-10-01 to 2026-10-15. The normal "keep only comments that name a role" filter was switched off for this one run (see "How to repeat"), so the pool also holds posts with no role. |
| 2. Sample | code | `scripts.eval_reading sample --size 100 --seed 1`: all **15** posts that name a collected role (the pool holds only 15, fewer than the 50 the plan asks for), plus **85** random posts that name none. Positions 1 to 15 in the sample are the role posts. |
| 3. Read | two models | One helper on Sonnet and one on Haiku read all 100 posts with the **same instructions** (the daily routine's own rules; the template is saved in `haiku_reading_2026-10-19_inputs/instructions_template_both_models_received.txt`, with only the output file name differing per model). They ran at the same time and each was told not to open the other's file. Each wrote 19 facts. |
| 4. Check | code | The pipeline's own checker: a value must appear word for word in the post, then the collection filter (role, location, salary) applies. |
| 5. Compare | code | `scripts.eval_reading compare`: a post "agrees" when both models delivered the same set of (job title, company), or both delivered nothing. |

## Numbers

| Measure | Value |
| --- | --- |
| Posts compared | 100 |
| Same answer from both models | **100** (100.0%) |
| Jobs delivered: Sonnet / Haiku / found by both | 15 / 15 / 15 |
| Role posts that delivered a job | 14 of 15 (the 15 jobs come from 14 posts: post 10 lists two roles; post 14 was filtered, see below) |
| Share of Sonnet's jobs that Haiku also found | 100% |
| Facts proposed by each model | 19 (15 delivered, 4 filtered out by the collection filter) |
| Facts rejected because a value was not in the post | 0 for Sonnet, 0 for Haiku |

Recorded in the run session and **not reproducible from the saved inputs**: the pool figures (266 comments, the date range),
the helpers' tokens (Sonnet 115,457, Haiku 135,630, as reported; they include re-reading the input), their times (122 s and
138 s), and the check that Haiku's activity log never opened Sonnet's file. The rest of this page can be re-derived from the
saved files.

## The four filtered-out facts (the same for both models)

| Post (comment) | Title the models wrote | Why the pipeline filtered it |
| --- | --- | --- |
| 23 ([49994263](https://news.ycombinator.com/item?id=49994263)) | Senior Technical Program Manager | not a collected role |
| 33 ([49927389](https://news.ycombinator.com/item?id=49927389)) | `product management` (a bare phrase) | not a title the filter accepts |
| 5 ([49931033](https://news.ycombinator.com/item?id=49931033)) | Product Managers and Business Development | the plural "Product Managers" does not match the title filter (see next section) |
| 14 ([49968954](https://news.ycombinator.com/item?id=49968954)) | Senior Product Manager, Auth0 AI and Identity Products | Toronto, Canada is outside US and Latin America |

## A possible gap in the title filter (not caused by either model)

Post 5 (PlantingSpace) lists the opening "Product Managers and Business Development". Both models proposed it, and the
pipeline dropped it for both: `role_family('Product Managers')` is `None` while `role_family('Product Manager')` matches. The
singular is what job boards use, so this matters mostly for free-text posts. Whether plural titles should count is a scope
choice for the user; it is recorded in `docs/PENDING.md` and not changed here.

## Where the two models still differ (the score cannot see these)

The agreement score compares job title and company only. Four facts differ in another field. Read these for rule 3:

| Post (comment) | Field | Sonnet wrote | Haiku wrote | Which is better |
| --- | --- | --- | --- | --- |
| 3 ([49922593](https://news.ycombinator.com/item?id=49922593), Shepherd) | location | `San Francisco, CA` | `San Francisco, CA & New York City, NY` | **Sonnet.** The post puts the AI Product Manager "in SF"; New York is for the engineering roles. Haiku copied the company-wide header line. |
| 12 ([49922769](https://news.ycombinator.com/item?id=49922769), Checkly) | location | `REMOTE (Europe / US Eastern)` | `remote UTC-3 to UTC+3` | **Haiku.** The PM role's own line says "remote UTC-3 to UTC+3"; Sonnet copied the header shared by all roles. The checker reads Sonnet's text as US and Haiku's as unresolved, so Sonnet's wording marks a UTC-3 to UTC+3 role as US-compatible. |
| 11 ([49927132](https://news.ycombinator.com/item?id=49927132), Komodo Health) | salary | `$213k-$288k + equity...` | `$213k-$288k + equity` | Same numbers. The "..." is in the post; Sonnet kept it. |
| 14 ([49968954](https://news.ycombinator.com/item?id=49968954), Okta) | company | `Okta (Auth0)` | `Okta` | Both fine. Filtered (Toronto) either way, but it would have counted as a disagreement if it had been delivered. |

So each model read one location better than the other. Both delivered the job in each case, and neither model is
consistently better on this evidence. Also, 10 of the 19 quotes are worded differently because each model picked its own
excerpt; both are word for word from the post, so the checker accepts either.

## A bug in the test tool, found and fixed during this run

`scripts/eval_reading.py` fell back to an empty link for a fact whose apply link was left empty. Hacker News comments have no
`url` field, so such facts became invalid postings and were counted as rejections. Both models left the link empty on 2
facts, so the first run showed 13 jobs and 2 rejected facts each. The pipeline falls back to the comment's own link, and the
tool now does the same, chosen by id field so a malformed X or LinkedIn item without a `url` fails loudly instead of getting a
Hacker News link (commits `ad92a97` and a follow-up, with regression tests). The numbers above are from the fixed tool.

## What this does and does not show

- It shows that, on this sample, Haiku read as well as Sonnet: same posts, same jobs, no invented values.
- **The headline is weaker than "100 of 100" sounds.** 85 posts name no role, and in production the Hacker News step never
  sends such posts to a model at all. Rule 1 would still have passed if the models had disagreed on 9 of the 15 role posts (91%).
  The informative figures are 15 of 15 role posts agreeing and rule 2 (15 of Sonnet's 15 jobs; the bar works out to at least 14).
- Limits: all 100 posts come from one thread (42 posted on 10-01, 22 on 10-02); one run per model, so no repeat-run
  variance; the sample is not random (every role post plus random filler), and both models read the 15 role posts first.
- Fifteen jobs is a small number. A perfect score on 15 is a good sign, not proof. A second run on another month, or on X and
  LinkedIn posts after the live test, would add confidence. The user declined a bigger run on October 19 ("with 100 we are good").
- Not tested: X posts, LinkedIn posts, newsletters and job cards. The sample is Hacker News only.
- Agreement cannot show a job both models missed. Every role post got a fact from both models, and the one role opening
  that was lost (post 5, plural title) was lost by the title filter, not by the models. A post that names no role did not
  produce a delivered job here; the production prefilter is what stops one from being sent.

## Decision (rule from the plan)

| Rule | Result |
| --- | --- |
| 1. Agreement over 90% | pass (100%, with the caveat above) |
| 2. Haiku finds at least 90% of Sonnet's jobs | pass (15 of 15) |
| 3. The user has read the disagreements and the sampled posts | **open** (no whole-post disagreements; four field differences above, posts 3 and 12 first) |

**Verdict: not yet.** The reading step stays on Sonnet (`docs/ROUTINE_PROMPT.md` does not name a model; the routine session's
own model does the reading) until the user answers rule 3.

## Privacy note

The saved sample holds public Hacker News text. Third-party email addresses in it (28 of them, including two personal Gmail
addresses) are replaced with `[email removed]`; the report is byte-identical after that. The first push of this branch
(commit `6cbc3ec`) still contains the original addresses in its history. The repository is private and the text was public, and
history was not rewritten; say so if you want that done.

## How to repeat

The tool refuses input files that sit inside the checkout, so work from copies elsewhere. Run every command from the repository
root, and give `--output` a new file name in an existing folder outside the checkout.

1. Re-score the saved run: copy `haiku_reading_2026-10-19_inputs/` to a folder outside the checkout, then
   `uv run --locked python -m scripts.eval_reading compare --candidates <copy>/eval_sample.json --a <copy>/facts_sonnet.json --b <copy>/facts_haiku.json --output <copy>/report.json`.
   The output is byte-identical to `haiku_reading_2026-10-19.json`.
2. A new run: fetch the unfiltered pool with this one-off script, saved outside the checkout and run with
   `PYTHONPATH=. uv run --locked python <script> <new output file>`:

   ```python
   import re, sys
   import jobhunter.hn_hiring as h
   h.ROLE_WORDS = re.compile('')          # keep every in-window top-level comment (eval only)
   from scripts import hn_hiring
   raise SystemExit(hn_hiring.main(['candidates', '--output', sys.argv[1], '--candidate-safety-stop', '100000']))
   ```

   Then draw the sample and read it with each model as in `../HAIKU_READING_EVAL.md`. The Hacker News threads move on, so a
   later run draws different posts.
