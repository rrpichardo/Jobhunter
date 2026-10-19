# Traceability: what happens to every item, and where you can see it

Written October 19, 2026, after the first live run, when about a quarter of the X facts were rejected and nothing said why.

**The rule.** Every item that enters a run must end in exactly one of these places, and the run must be able to say which and why:
delivered to the Sheet, held for the next run, dropped by the collection filter with a reason, or rejected with a reason.
Nothing is estimated: numbers in a report are copied from tool output.

## Where each step shows itself

| Step | What it shows | Where it lasts | Gap today |
| --- | --- | --- | --- |
| Collect (boards, X, LinkedIn, Hacker News, newsletter) | Counts printed by the collector (the X and LinkedIn collectors, once merged, print their query counts and an error word). | The run session's transcript. The Sheet's **Sources** tab keeps the latest counts and error word per source. | The transcript is the only place the per-search lines survive. |
| Queue (`ai_queue pull`) | `queue:` line: new, already read, held, expired, oldest unread age. | The memory of what was read or is held is kept in the Sheet's hidden `_State` tab. | none |
| Read and check (`social_posts validate`, `hn_hiring validate`) | **New (E4):** a `trace:` line saying how many facts were read, valid, duplicates, rejected (by reason code), how many posts were unreadable, how many valid facts the collection filter dropped (by reason) and how many were delivered or held; plus a `trace_rejected:` line with up to ten post ids and their reasons. | The run session's transcript, and the result file inside the run folder (`trace` and `rejections` keys, post ids and reason codes only; no post text). | The Sheet has no column for the reasons (see "Next steps"). The run folder is temporary. |
| Probe (`source_probe`) | A table per source: status, fetched, matched, delivered, a note; `duplicates_merged`. | Transcript, and the Sources tab (counts). | For job boards the reason a job was dropped by the collection filter is not printed, only the counts. |
| Write (`sheets_sync`) | `sync_verified: run_id=... batches=... unique_jobs=...` after a read-back. | The Sheet's **Run Log** tab (run id, start, end, jobs input, unique, status). | none |
| Report | The run's final message. | The session transcript in the Claude app. | none, provided it copies the `trace:` lines (the routine prompt now requires it). |

## Reason codes (fixed words, never post text)

Rejected fact: `invalid_post_facts` (wrong shape), `unknown_post`, `not_text:<field>`, `too_long:<field>`, `empty:<field>`,
`not_in_post:<field>` (a value is not word for word in the post), `link_not_in_post_links`, `link_not_https`, `malformed_fact`.
Dropped by the collection filter: `role_not_in_scope`, `place_excluded`, `pay_below_floor`.
`<field>` is one of `title`, `company`, `location`, `salary`, `description_quote`, `apply_url`.

How the numbers add up for one read: `facts = valid + duplicates + rejected facts`, and `valid = delivered + dropped by the filter`.
The older `rejected=` on the first output line also counts unreadable posts, which is why it can exceed the rejected facts.

## Next steps (not built; each needs your go and a Codex review)

- **E5: a durable trace in the Sheet.** A small hidden tab or a Sources column holding the latest reason counts per source, so
  the answer survives after the session. Needs a change to the Sheet writer and its tests.
- **E6: reason counts for job boards.** Print why `source_probe` dropped jobs (role, place, pay) per source.
- **Pay forms.** The pay check reads forms like `USD 50,000 per year` or `50,000 - 60,000 USD YEAR` but not `$50k-$60k` or `$190k-$220k`,
  so those jobs are kept as "pay unresolved" instead of being checked against the floors. This is safe (it keeps rather than
  drops) but it means the pay floors rarely act on X and Hacker News posts. Decide whether plain `$Nk-$Mk` should count as annual USD.
