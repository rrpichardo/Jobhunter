# Haiku vs Sonnet on the reading step: result of the first run (October 19, 2026)

Plain-language summary first, details after. The plan and the rule are in
[`../HAIKU_READING_EVAL.md`](../HAIKU_READING_EVAL.md).

## Answer in one paragraph

On 100 real Hacker News hiring posts, Haiku and Sonnet gave **the same answer on all 100** and found **the same 15 jobs**.
Rule 1 (agreement over 90%) and rule 2 (Haiku finds at least 90% of Sonnet's jobs) both pass with room to spare.
**Nothing is switched yet.** Rule 3 is the user's: read the posts and the differences below and say whether any matters.
Until then the reading step stays on Sonnet.

## What was run

| Step | Done by | What happened |
| --- | --- | --- |
| 1. Collect | code | All top-level comments from the two "Ask HN: Who is hiring?" threads in the last 28 days: **266 comments** (posted 2026-10-01 to 2026-10-15). The normal "keep only comments that name a role" filter was switched off for this one run (see "How to repeat"), so the pool also holds posts with no role. |
| 2. Sample | code | `scripts.eval_reading sample --size 100 --seed 1`: all **15** posts that name a collected role (there are only 15 in the pool), plus **85** random posts that name none. |
| 3. Read | two models | One helper on Sonnet and one on Haiku read all 100 posts with the **identical instructions** (the daily routine's own rules, saved in `haiku_reading_2026-10-19_inputs/instructions_both_models_received.txt`). They ran at the same time. Haiku's activity log never mentions Sonnet's file, and 11 of the 19 facts differ in at least one field, so the two readings are independent. Each wrote 19 facts. |
| 4. Check | code | The pipeline's own checker: a value must appear word for word in the post, then the collection filter (role, location, salary) applies. |
| 5. Compare | code | `scripts.eval_reading compare`: a post "agrees" when both models delivered the same set of (job title, company), or both delivered nothing. |

## Numbers

| Measure | Value |
| --- | --- |
| Posts compared | 100 |
| Same answer from both models | **100** (100.0%) |
| Jobs delivered: Sonnet / Haiku / found by both | 15 / 15 / 15 |
| Share of Sonnet's jobs that Haiku also found | 100% |
| Facts proposed by each model | 19 (15 delivered, 4 filtered out by the collection filter) |
| Facts rejected because a value was not in the post | 0 for Sonnet, 0 for Haiku |
| Tokens used by the helper (as reported, includes re-reading the input) | Sonnet 115,457, Haiku 135,630 |
| Time | Sonnet 122 s, Haiku 138 s |

The four filtered-out facts are the same for both models: two titles that are not a collected role (a Technical Program
Manager and a bare "product management"), one Product Manager/Business Development listing, and one Toronto role (outside
US and Latin America).

## Where the two models still differ (the score cannot see these)

The agreement score compares job title and company only. Four facts differ in another field:

| Post | Field | Sonnet wrote | Haiku wrote | Effect |
| --- | --- | --- | --- | --- |
| 3 (AI Product Manager) | location | `San Francisco, CA` | `San Francisco, CA & New York City, NY` | delivered either way; Haiku's is more complete |
| 12 (Product Manager, DevTools & AI Reliability) | location | `REMOTE (Europe / US Eastern)` | `remote UTC-3 to UTC+3` | delivered either way; the two phrases read differently |
| 11 (Principal Product Manager, AI Products) | salary | `$213k-$288k + equity...` | `$213k-$288k + equity` | same numbers |
| 14 (Senior Product Manager, Auth0 AI and Identity) | company | `Okta (Auth0)` | `Okta` | filtered out (Toronto) either way; would count as a disagreement if it were delivered |

Also, 10 of the 19 quotes are worded differently because each model picked its own excerpt; both are word for word from the
post, so the checker accepts either.

## A bug in the test tool, found and fixed during this run

`scripts/eval_reading.py` fell back to an empty link for a fact whose apply link was left empty. Hacker News comments have no
`url` field, so such facts became invalid postings and were counted as rejections. Both models left the link empty on 2
facts, so the first run showed 13 jobs and 2 rejected facts each. The pipeline falls back to the comment's own link, and the
tool now does the same (commit `ad92a97`, with a regression test `test_a_hacker_news_fact_with_no_apply_link_...`). The
numbers above are from the fixed tool; the saved report reproduces from the saved inputs.

## What this does and does not show

- It shows that, on this sample, Haiku read as well as Sonnet: same posts, same jobs, no invented values.
- It does not show how Haiku handles X and LinkedIn posts, newsletters or job cards: the sample is Hacker News only.
- Fifteen jobs is a small number. A perfect score on 15 is a good sign, not proof. A second run on a different month, or on
  X and LinkedIn posts after the live test, would add confidence.
- Agreement cannot show a job both models missed. All 15 posts that name a role got a job from both models, and a post that
  names no role cannot produce a delivered job under the collection filter, so there is no silent post to chase here.

## Decision (rule from the plan)

| Rule | Result |
| --- | --- |
| 1. Agreement over 90% | pass (100%) |
| 2. Haiku finds at least 90% of Sonnet's jobs | pass (15 of 15) |
| 3. The user has read the disagreements and the sampled posts | **open** (no whole-post disagreements; four wording differences above) |

**Verdict: not yet.** The reading step stays on Sonnet (`docs/ROUTINE_PROMPT.md` is unchanged) until the user answers rule 3.

## How to repeat

The tool refuses input files that sit inside the checkout, so copy the saved inputs to a folder elsewhere first.

1. Re-score the saved run: copy `haiku_reading_2026-10-19_inputs/` to a folder outside the checkout, then
   `uv run --locked python -m scripts.eval_reading compare --candidates <copy>/eval_sample.json --a <copy>/facts_sonnet.json --b <copy>/facts_haiku.json --output <new file outside checkout>`.
   The output equals `haiku_reading_2026-10-19.json`.
2. A new run: fetch the unfiltered pool with a one-off script that sets `jobhunter.hn_hiring.ROLE_WORDS` to
   `re.compile('')` before calling `scripts.hn_hiring.main(['candidates', '--output', <new file>, '--candidate-safety-stop', '100000'])`,
   then follow the steps in `../HAIKU_READING_EVAL.md`. The Hacker News threads move on, so a later run draws different posts.
