# Eval: can the cheap model (Haiku) do the reading step as well as Sonnet?

Status: RUN ONCE on October 19, 2026 (Hacker News only; see Result). Written at the user's request; the user wants to see the 100 examples and the
agreement percentage before anything is switched. Until this passes, the reading step stays on the routine session's own
model (Sonnet); `docs/ROUTINE_PROMPT.md` does not name a model, so switching to Haiku would need an explicit change there.

## The question and the rule (decided by the user)

Reading steps (Hacker News comments, X and LinkedIn posts, LinkedIn job cards, newsletter editions) copy title, company,
place and pay out of text. Haiku costs far less than Sonnet. We switch only if, on **100 real items**, the two models
**agree on more than 90%** of them. Agreement is judged on what would reach the Sheet, not on wording (below).

Switch only when ALL of these hold; otherwise stay on Sonnet and report why:
1. Agreement is **over 90%** (more than 90 of the 100 items).
2. Haiku finds at least 90% of the jobs Sonnet found (`in_both` divided by Sonnet's `jobs`): cheap is not worth missing roles.
3. The user has read the disagreements (the report lists every one) and none is a case where Sonnet was wrong and Haiku right
   or the reverse in a way that matters. Agreement alone cannot show that both models missed the same job.

## Why this design (for learning)

- **Same input, same instructions, same checker.** Both models get the identical work file and the identical rules from the
  routine prompt. Both fact files go through the pipeline's own checker (`post_facts.build_result`): a value counts only if it
  appears word for word in the item, then the role/salary/location filter runs. So a model cannot "win" by inventing
  something, and what we compare is what would be delivered.
- **Agreement per item, not per word.** Two models can phrase a quote differently and both be right. So an item AGREES when both
  deliver the same set of (title, company) pairs after normalising case and punctuation. Both delivering nothing is agreement.
- **The sample leans on items that matter.** It takes every post that mentions a collected role (up to half of the 100; where
  reading decides the outcome) and fills the rest with posts that do not (where the right answer is "nothing"; a model that
  invents jobs shows up as rejected facts or disagreement). If fewer than half mention a role, as on the first run (15 of 100),
  most of the sample is the easy "nothing" case, so look at the role posts, not only the overall percentage.
- **Sonnet is the reference, not the truth.** It is the model we trust today, so Haiku is measured against it; step 3 (a human
  reading the disagreements) is what catches shared mistakes.
- **A seed makes it repeatable.** The sample is deterministic (`--seed`), so the same 100 items can be re-run after any change
  to the prompt.

## How to run it (a manual session in JobHunterEnv, or here with candidate files from a real run)

1. Get real candidate/work files from real runs (the HN, X, LinkedIn and newsletter steps each write one; use the work files
   from `ai_queue pull`). Several can be combined.
2. `uv run --locked python -m scripts.eval_reading sample --candidates <work file> [--candidates <another>] --size 100 --seed 1 --output $DIR/eval_sample.json`
3. Read the sample with each model, writing the facts file exactly as in `docs/ROUTINE_PROMPT.md` section 1:
   - Sonnet: the session model reads `$DIR/eval_sample.json` -> `$DIR/facts_sonnet.json`.
   - Haiku: a subagent started with `model: haiku` and the same instructions -> `$DIR/facts_haiku.json`.
   (Use the same prompt text for both, and do not show either model the other's output.)
4. `uv run --locked python -m scripts.eval_reading compare --candidates $DIR/eval_sample.json --a $DIR/facts_sonnet.json --b $DIR/facts_haiku.json --output $DIR/eval_report.json`
5. Share with the user: the 100 sampled items, both fact files, the printed `agreement_percent`, the job counts and the
   `DISAGREE` lines. Save the report next to this file as `docs/evals/results/haiku_reading_<date>.json` and add the verdict
   to the section below.

## Result

First run, October 19, 2026, on 100 real Hacker News "Who is hiring?" posts (15 name a collected role, 85 do not):
**100 of 100 posts agree**, and Sonnet and Haiku each delivered the same **15 jobs** (14 of the 15 role posts delivered one),
with no value rejected for not being in the post. The informative figure is the 15 role posts, all of which agreed; the 85
"nothing here" posts were the easy case. Rules 1 and 2 pass. **Rule 3 (the user reads the posts and differences) is open, so
the verdict is "not yet" and the reading stays on Sonnet.** Four facts differ in location, salary or company wording, which the
score cannot see; in two of them each model read the location better than the other (details in the results file). The run
also exposed a bug in this tool (a fact with an empty apply link was wrongly rejected for Hacker News items; fixed with tests)
and a possible gap in the pipeline's title filter (the plural "Product Managers" is dropped; not changed here).

Full detail, the differences, how to repeat it and the saved inputs:
[`results/haiku_reading_2026-10-19.md`](results/haiku_reading_2026-10-19.md) (report: `results/haiku_reading_2026-10-19.json`).
Not yet tested: X posts, LinkedIn posts and newsletters (the live test comes first).
