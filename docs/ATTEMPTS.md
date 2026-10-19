# Implementation attempt log

## October 19 Codex review rounds on the Claude-written stack (#19 to #30)

- Round 1: Codex reviewed every Claude-written PR at its exact head and found seven problems (R1 to R7) in #19,
  #21, #24, #25, #26 (and the same lost-post bug in #27). Fixes were made as separate PRs on the reviewed heads
  (#32 to #37), not on the original branches.
- Round 2: Codex approved #37 and found eight further problems in #32 to #36 (hard cases the first fixes missed,
  such as numeric or mistyped ids, the clock-change edge of the New York day, and a wrong claim in the docs).
- Round 3: fixed and re-reviewed. Codex approved #33, #34, #35, #36 and #37. #32 needed a fourth pass for two
  small items (the runbook did not pass the digest; a test was slow) and was then approved.
- The usual cap is three repair/review cycles per milestone. The user explicitly asked for as many rounds as
  needed until Codex approves, so the cap was exceeded on #32 on purpose. Several Codex runs ended with
  "unknown error" and were repeated; those are failed runs, not review cycles.
- Everything above is offline test evidence. Nothing ran against the real workbook or in JobHunterEnv, and
  none of these PRs is merged.

## October 18 social continuation handoff — no live social attempt

- User prioritized LinkedIn profile hiring-post search alongside job listings,
  then X, then the real cloud test; then requested handoff before implementation.
- Actual JobHunterEnv read-only preflight at `5200ac01773ee51f7ddf18ea6b13267ac7911ac6`
  verified nonempty credential booleans and empty Chromium launch via image's
  Node Playwright; no cookie injection, LinkedIn/X/Gmail requests or Sheet writes.
  Python collector packages absent; no collector selected or implemented yet.
  See latest CLAUDE_HANDOFF.md for exact outputs and continuation sequence.
- This is not a new failed authentication attempt or consumed live daily allowance.
  Existing blocker/review counters, including Gmail UI3/3, remain unchanged.

## October 18 milestone closure — PR #16

- Cycle 9 Claude review of `110ea30d7cc4f97ac78a76ea6a05ea405db11632`
  returned no actionable findings. It confirmed the final boundary repair and
  ran 577 tests / 10 subtests, plus parser/location comparisons. Required CI
  passed at that exact head; actual JobHunterEnv locked tests also passed.
  Evidence: https://github.com/rrpichardo/Jobhunter/pull/16#issuecomment-6255774750 .
- PR16 merged as `1df1e7ccbc7579b149085993ded07ca8f9829df7`;
  post-merge local tests passed 577/10, diff check and worktree clean. Older
  pending-review/stop checkpoints below are historical, superseded by the
  user's continued-repair authorization and this clean review/merge.
- One bounded actual-cloud public-source smoke and identical repeat both
  passed on the merge SHA (`pr16-broad-001`). Readback verified one added real
  non-AI PM job, no duplicates or user-field changes, one Run Log row and no
  lock. V0_VERIFICATION.md records the immutable artifact digest and limits.
  This successful validation is not a failed blocker attempt.
- Gmail filter UI remains independently exhausted at 3/3; no retry or reset.
  No Gmail message ingestion, social restoration or scheduled run was proved.

## October 18 broader collection and Gmail intake milestone

- Cycle 8 Claude reviewed `c4c82f952f2b1130ecc664eadc4c60763fb7f1dd`,
  confirmed the real JSearch path fixed, and found one low-severity mode-label
  boundary issue: `Remote, or Colombia` lost its alternative meaning. Twelve
  failing regressions reproduced prefix/suffix conjunction and double-separator
  cases; boundary checks now preserve ambiguity while normal prefixes still work.
  Full local suite: 577 tests / 10 subtests, diff check clean. Fresh exact-head
  cycle-9 Claude review and current CI remain required before merge.

- Cycle 7 Claude reviewed `323eb70ce27ac5b16831995c4c8eea3f8308971e`,
  confirmed prior repairs and found JSearch's actual `Remote, country` producer
  format was treated as an alternative mode. Eight failing regressions include
  a real parser-to-preference-to-row fixture path. Attached comma-prefix modes
  now normalize; comma suffixes and `or Remote` alternatives stay unresolved.
  Full local suite: 565 tests / 10 subtests, diff check clean. Fresh exact-head
  cycle-8 Claude review and CI remain required before merging.

- Cycle 6 Claude reviewed `e158c6beb4089f0ff4bc74effb52e3112b1d274a`,
  confirmed earlier fixes but found comma-separated unknown alternatives could
  satisfy70k and long-dash remote labels became unresolved. Regressions failed
  before repair. Known regional hierarchy forms normalize before comma splitting;
  unknown qualifiers remain unresolved and collected, not asserted eligible.
  Long dashes, Remoto and parenthesized known-city mode qualifiers are handled.
  Latest full local suite: 557 tests / 10 subtests, diff check clean. Fresh
  exact pushed-head cycle-7 Claude review and CI remain required before merge.

- Cycle 5 Claude reviewed `07de188e9a6fa03b168b6c4658aa4f8600031ecf`,
  confirmed prior repairs and found country-less city/department forms (Bogotá,
  DC; Medellín, Antioquia; etc.) were still dropped or assigned US. Regressions
  reproduced those plus missing-comma US alternatives, unknown alternative
  places/mode-only alternatives and unrecognized standalone locations. Repairs
  retain ambiguous cases as unresolved, with no claim of salary eligibility.
  Latest full local suite: 540 tests / 10 subtests, diff check clean. Fresh
  cycle-6 pushed-head Claude review and current CI are required before merge.

- Cycle 4 Claude review of `38082751bb0deeb7eb15e577e91bfe1a12b36097`
  confirmed the earlier examples fixed but reproduced optional-department text
  swallowing a second US locality at additional separators, and Bogotá DC/CO
  spellings being treated as US. Thirteen failing regressions reproduced these
  cases before repair. Replaced arbitrary department text with explicit known
  department/capital-district forms; unknown regional forms remain unresolved.
  Current local full suite: 518 tests / 10 subtests passed, diff check clean.
  Fresh cycle-5 pushed-head Claude review and CI remain required before merge.

- User explicitly said **"do it until is fixed"** after the PR16 cycle-cap
  question, authorizing continued repairs and fresh Claude reviews for PR16.
  This supersedes its stop checkpoint below; it does not reset counters or
  extend the separate Gmail UI blocker. Cycle 4 is the next actual review.
- Cycle-3 mixed-location findings reproduced in 11 failing regressions. Repair
  normalizes explicit regional city/country pairs anywhere before inspecting US
  locality codes, so CO/PA/AR codes outside those pairs remain US evidence and
  mixed listings stay unresolved. Original source location text is preserved.
  Full local suite: 505 tests and 10 subtests passed; diff check clean. Fresh
  pushed-head Claude review and CI are still required before merge.

- Cycle 3 Claude review of `9e1f2ff0de4b9a3163e689ce99831d9f81f46f16`
  confirmed email links, standalone Colombian suffixes and detail priority fixed,
  but found two mixed-region defects: US-first regional city/CO/DO combinations
  can be dropped at the US floor, and ambiguous CO/PA/AR US city codes can falsely
  satisfy the LATAM floor. Examples and locations are posted on PR16. Claude ran
  486 tests / 10 subtests successfully; passing tests do not resolve findings.
- **Three repair/review cycles exhausted; PR16 remains open and unmerged.**
  User authorization requested for exactly one additional fix/Claude-review
  cycle. Do not repair this blocker again until that answer arrives. PR15's
  prior exception does not extend to PR16. Gmail UI remains independently 3/3.
- Final code revision above also passed actual JobHunterEnv locked tests,
  486/10, exit 0, exact SHA and clean tree confirmed in expanded tool output.
  Linux/Windows CI passed. No new live source/Gmail/social fetch or Sheet write
  occurred during that final check; no production Gmail or scheduling proof.

- Cycle 2 Claude review of `67ca7f8fa9710fbf877a8cb28e85b1fd826dd990`
  confirmed earlier repairs but found LinkedIn `/comm/` email URLs, mixed US
  city/LATAM locations, Colombian department/work-mode suffixes and detail-fetch
  shortlist ordering still needed repairs. All four reproduced in failing tests;
  repaired suite: 486 tests and 10 subtests passed, diff check clean. Fresh
  cycle 3/3 is required on the pushed repair; do not merge an unreviewed repair.

- Cycle 1 Claude review of pushed `4d429652e72f4bc50482987222e375eed283bdf4`
  found repeat-email identity, Colombian geography, unresolved low salary,
  partial-error caps, cross-card evidence, capped role ordering and Next step
  ownership issues. Posted to PR16. Regressions reproduced the issues before
  repair. Current repair requires fresh pushed-head Claude review, cycle 2/3.
- Repairs isolate one visible HTML job card per extraction and reject unsupported
  layouts (including plaintext) rather than fall back to an entire message.
  LinkedIn numeric requisition URLs discard tracking and have stable identity
  across message/title changes. Caps/counts reconcile even after partial errors.
  Mixed US/LATAM availability and country-less city names remain unresolved;
  known pay below 70k is below every allowed floor. Unknown salary checks live
  in More details, leaving Next step blank per the plan.

- User authorized another agent to finish Gmail routing and broaden collection
  beyond AI PM. Agent stopped at an account usage limit; root resumed as the sole
  implementation owner on `codex/salary-preferences`. No counters reset.
- Python now recognizes the approved role families and applies annual USD salary
  floors of 140,000 US/remote-from-US and 70,000 LATAM including remote. Missing
  salary is retained with Check first in More details rather than asserted eligible.
  Existing source/request/batch caps remain unchanged.
- Added a message-scoped Gmail intake boundary with injected connector/extractor
  interfaces, verified metadata rules and exact fact evidence. It can join the
  probe payload and existing writer in synthetic tests. Real connector payload
  binding and a production CLI route are not implemented; no Gmail deployment.
- Fresh `.venv/bin/python -m pytest -q`: 458 tests and 10 subtests passed.
  The first full run failed only the keyed-source query expectation; updated
  exact assertions to the approved broader query, retaining request-count/key
  placement checks. `git diff --check` passed.
- Actual cloud Gmail check used the existing connector in session
  `session_01Kydab84oh1GMjzuFahVswG`. Expanded `mcp__Gmail__list_labels` output
  confirms exact `JobHunter` label, zero messages and threads. No message reads
  or inbox fallback. Local dedicated-account alert metadata search had no matches.
- Gmail forwarding-checkbox blocker remains 3/3. Next: receive a real alert,
  confirm precise metadata rules, user manually completes forwarding action,
  then verify fresh label-scoped message extraction and Sheet delivery in cloud.
- Earlier repair verification: 475 tests and 10 subtests passed; diff check passed.
  Cycle 2 is consumed; fresh cycle 3/3 is required on the pushed repair revision.
  Passing local tests do not establish current CI/review or cloud proof.

## October 18 PR #15 cycle 3 result — further work authorized

- Claude reviewed exact `8fc2a7c12a8129b0e27f8f9472a62db0cee52ef6`, confirmed
  the automatic-review old-limit finding resolved, and manually checked jq on three
  timestamp scenarios. It did not run the suite. Current-head local verification
  passed 386 tests / 10 subtests, Bash syntax and diff checks; Linux, Windows and
  the Claude action are green. A green action is not the actual review report.
- One actionable low-severity documentation issue remains: REVIEW_WORKFLOW says
  to post the request before starting the watcher; a fast usage-limit reply in
  between is intentionally ignored and can become a timeout. Proposed docs-only
  repair: start the watcher before a manual request and explain pre-start replies
  for automatic reviews. No new code repair has been made for this finding.
- Three watcher review/repair cycles were exhausted. User then explicitly said
  not to worry about the cap for this PR, authorizing continued watcher repair
  and review. This exception does not reset other source/setup blocker counters.
  The docs now start the watcher before a manual request and explain pre-start
  automatic-review replies. Obtain fresh exact-head Claude review and CI before
  merging; non-blocking severity alone is not resolution.

## October 18 Gmail filter UI — three attempts exhausted

- Forwarding destination registration is verified; destination `JobHunter` label
  exists. Global forwarding remains disabled. No JobHunter filter is installed.
- Three source-filter UI investigations encountered unexpected navigation: the
  existing tab first returned to settings during a narrow search, then switched
  to Drafts at the forwarding-checkbox action. A fresh owned tab using DOM-only
  controls also switched to Drafts at that action. The agent stopped without
  saving any filter; no fourth investigation is authorized.
- Stop this UI blocker until the user manually selects the forwarding action or
  a relevant tool/UI capability changes. Prepared conservative sender/subject
  rules are not installed or delivered-mail proof. Dedicated-account alerts still
  need enabling; user-assisted old-main-account subscription cleanup is deferred.

## October 18 PR #15 watcher — review/repair cycle 2

- After the reported session-limit reset, Claude CLI reviewed exact head
  `341560c2f8af5ba2a34e779329d20f6d216df8e0`. It confirmed the stale-head fix
  and found an actionable remaining old-limit case: automatic review for a new
  commit need not create a new human request. An old request then kept the old
  usage-limit reply inside the script's time window. No reviewer suite execution
  is claimed; Claude inspected the diff and exercised jq expressions.
- A regression reproduced exit 2 for that earlier-round reply before repair.
  The window now starts no earlier than the watcher start, even with an old human
  request. Historical replies and same-second timestamp ambiguity are ignored;
  completed exact-head review receipts are still recognized. Seven focused tests
  and the full 386-test / 10-subtest suite pass. Bash syntax and diff checks pass.
- The prior head's Linux/Windows CI and rerun Claude action are green, but do not
  cover this repair. Push the new revision and obtain fresh Claude review and CI.
  Cycle counters carry forward: the next fresh review is cycle 3 / 3 for this
  watcher milestone. A further repair/review cycle requires user authorization.

## October 18 PR #14 watcher — review/repair cycle 1

- Codex reviewed Claude head `5cf687c1e3cfde90def9eab9f2cd2f74f8b3b633`:
  P1 stale-head clean result and P2 earlier-request usage-limit termination.
  `scripts/wait_codex_review.sh 14 <head> 1` returned findings (exit 1).
- Codex took over repairs on `codex/review-watcher-fixes`. Three regression
  failures reproduced both defects, including a push during response retrieval.
  The watcher now compares the live head before polling and before clean exit,
  and dates usage-limit replies against the latest human review request (or the
  wait start if none exists). Five focused tests pass; full offline suite:
  384 tests / 10 subtests passed. Bash syntax and diff checks passed.
- This fix set requires opposite-agent Claude review of its pushed full SHA;
  the original Codex review does not approve the new Codex-authored repairs.
  Linux/Windows CI and current review are still required. No runtime/deployment
  proof or source collection was performed. Claude's previous review action
  failed with `is_error:true`, not a completed review; do not bypass a required check.
- Another process switched the shared checkout to main and merged PR #14 at
  `6c29058d00327b607a95a54a7058d8bfd4bf5e47` during repairs. The repair commit
  was preserved on `codex/review-watcher-repairs`, follow-up PR #15; no repair
  implementation was pushed directly to remote main. The authenticated Claude
  CLI review attempt returned a session limit and no review. Resume opposite-agent
  review after the limit resets; this is outstanding, not approval.

## October 18 source cycle13 — Claude salary-modifier follow-up

- Claude's exact5710dd3 review found no blocking issue but noted the concrete
  "bonus up to" salary bypass and a benefits-included false exclusion. Four
  regressions failed for capped bonus, sign-on bonus, target-bonus labels and a
  qualifying salary with benefits included. Current-clause compensation labels
  now distinguish those amounts without requiring the label to touch the figure.
- Remote/provenance implementation is unchanged. Full locked suite: 330 tests
  and 10 subtests passed; diff whitespace check passed. Only Claude is requested
  to review these Codex-authored changes, per the user's exclusive review rule.
  No same-agent approval gate is requested. CI/Claude review still precede merge.

## October 18 review ownership clarified by the user

- The user explicitly requires Codex to review Claude's changes and Claude to
  review Codex's changes only. PR11 fixes are Codex-authored, so Claude is the only
  reviewer required for this follow-up. No further Codex self-review is requested.
- The earlier independent reports remain historical evidence. The planned
  additional Codex review after 609a137 was not issued and does not consume a
  delivered review cycle. Source cycle12 now tracks the latest Claude re-review;
  no cycle13 Codex request is pending. CI and implementation tests remain required.

## October 18 pre-merge salary re-review

- Claude reviewed exact PR11 head19e9e77 and confirmed the original fixes, with
  salary-format caveats. Independent Codex source cycle11 found two P2 salary
  issues before merge: explicit dollar/a-year/parenthesized annual forms regressed,
  and an explicitly annual-labelled bonus still qualified below-floor salary.
  Full report: reviews/2026-10-18-codex-followup-review.md. No PR11 merge occurred.
- Five additional regression cases failed before repair. Qualifying monetary
  ranges now retain explicit dollar signs and annual-period notation, including
  gross pay, while locally labelled bonuses/commissions/benefits cannot establish
  the salary exception. A genuinely qualifying base salary still qualifies when
  a separate bonus follows it. Preserved attribution/remote code is unchanged.
- Full locked suite: 325 tests and 10 subtests passed. Source cycle12 tracks the
  Claude re-review of the new exact head. An additional Codex review was planned,
  then cancelled by the user's opposite-agent-only direction before it was issued.
  Historical counts and the user's unlimited repair-cycle direction remain intact.
  A pending request is not approval; CI and Claude review precede this merge.

## October 18 independent Codex review after integration

- The automated cycle-3 request for 99b1154 failed on a usage limit. A later
  manual Codex review at 6a61f35 found bugs, but was not final-head approval and
  its full report was retained outside the PR. Final pre-merge reports for #8–#10
  were Claude reports. Do not describe the failed bot request as successful or a
  post-merge review as satisfying a gate before merge.
- An independent Codex reviewer in the app reviewed merged main
  36539f47ee6c550c9cf5e2f521831a17ad13f16c and reproduced three P2 defects. Full
  scope and evidence: reviews/2026-10-18-codex-postmerge-review.md. The old main
  suite passed 304 tests/10 subtests; passing tests did not cover the defects.
- The source counter previously recorded cycle 7. Additional events, retained
  rather than reset: 8 = pushed-head Claude integration acknowledgement at
  3f237dd; 9 = this independent post-merge Codex review; 10 = requested follow-up
  Claude review; 11 = requested independent Codex follow-up review. The user had
  explicitly authorized "do as many as needed". Pending requests are not approvals.
- Codex is the implementation owner on codex/fix-postmerge-review. Failing-first
  regressions reproduce dropped Lever/WWR remote evidence, erased same-harvest
  attribution, benefits/bonus values qualifying below-floor annual pay and missing
  precise discovery timestamps. Legacy dates remain dates; unknown historical
  source times are not invented. Source times compare actual instants.
- Full locked follow-up suite: 318 tests and 10 subtests passed. All three fixes
  were initially assigned both reviews; the user's later clarification requires
  Claude review only for these Codex-authored fixes, together with CI.
  No live source calls, Google writes or deployment were performed.

## October 18 integration authorized

- The user now directs "commit merge and push", superseding the earlier no-push
  restriction for this reviewed repair stack. No additional runtime collection or
  deployment is authorized by that instruction. Historical counters are retained.
- Final local patch reports found no actionable findings: writer cycle 8 at
  52da0f1 and source cycle 7 at 5d20ae0; see CLAUDE_HANDOFF.md for links and scope.
  Fresh locked checks before integration passed 160 writer tests/10 subtests and
  304 full-stack tests/10 subtests. Current pushed-head CI/review remains the gate.
- Integrate #8, then #9, then #10 using preserved commit history. #7 is superseded.

## October 18 source cycle 7 — common work-mode separators

- Claude's cycle-6 review confirmed the three retained findings resolved. Two
  common work-mode separator cases still dropped US leads; both failed first.
  Known hybrid/on-site modes now accept parentheses or ordinary dash/slash/comma
  separators. The suffix must still fully match; a trailing foreign country does
  not establish US location. Hybrid/Remote already passed via the remote rule.
- Added the review's maintenance note to recheck state/ISO collisions when the
  regional country list changes. Locked full suite: 304 tests and 10 subtests
  passed, with a clean whitespace check. Fresh review requested; no live calls,
  pushes or merges to main. Historical counters remain under the user's waiver.

## October 18 source cycle 6 — propagated input diagnostic

- Propagated writer cycles 7/8 while retaining schema-2 dispatch. Source cycle 5
  review confirmed the first US-city fix, then identified ambiguous AR/PA country
  codes and US ZIP/spelled-state formats. Six regressions failed first. Regional
  shortcuts now require nonambiguous state codes or full state names, with only a
  ZIP and known on-site/hybrid suffix accepted. AR/CO/DC/PA alone do not prove US
  in a regional location; explicit US country or full state names resolve it.
- Reproduced the review's malformed-artifact diagnostic with unhashable Source and
  source_id fields. Schema-2 validates their string type before aggregation, giving
  safe validation codes before Google access rather than catching programmer bugs.
- Locked full suite: 301 tests and 10 subtests passed; diff whitespace check passed.
  No live calls or pushes. Fresh static review covers this complete follow-up.

## October 18 source review cycle 5 — US location collisions

- Claude reviewed local `dda10ef` and found US cities named for regional
  countries were excluded. Three regressions failed for Panama City, FL; Mexico,
  MO; and Peru, IL. Terminal US state codes now preserve those leads while DC/CO
  alone cannot bypass the Colombia salary condition. Explicit US country evidence
  remains accepted. Original location and eligibility rules are unchanged.
- Multiple existing verified identities still stop for operator reconciliation,
  preserving user data. Current provider parsers always emit their configured
  source ID; speculative future invariant failures are not a reproduced bug.
- Propagated writer cycle 6 locally. Locked full suite: 289 tests and 10 subtests
  passed; diff whitespace checks passed. Fresh Claude patch review is required.
  The user authorized further cycles; no push, merge to main or live run occurred.

## October 18 current local source follow-up

- The user superseded the three-cycle pause with "do as many as needed" while
  retaining the no-push/no-merge direction. Keep the historical counts: source
  review 1 was Codex at `a17bae4`, review 2 was Claude's first `5487aa5` patch
  review, and review 3 covered the `5976ca3` patch. Earlier wording calling that
  last review "cycle 2" counted repair iterations, not all reviews; this entry
  corrects the total rather than resetting it. Current source follow-up is cycle 4.
- The requested whole-PR Claude checks now cover #7 `9f4fd58` retrospectively,
  #8 `e3536e4`, #9 `32a54b8`, and #10 `a17bae4` plus the local patch. All were
  static reviews; Claude did not run the tests. Original #7 findings repaired by
  #8 remain historical. Current code still needs fresh review after these repairs.
- Reproduced and fixed the third-custom-source batch stop: unknown links always
  retain separate flagged rows, with deterministic review references. Multiple
  conflicting verified requisitions still require operator reconciliation.
- Reproduced and fixed Colombia's `DC` bypass, New Mexico's false exclusion,
  punctuated/underscore annual salary tokens, missing same-source repost flags,
  and matching custom Greenhouse `gh_jid` links across sources/runs. Country and
  pay units remain explicit; no COP/DOP conversion or eligibility inference.
- Known AI titles are prioritized inside the existing bounded detail budget;
  omitted detail and global-limit counts are recorded in the artifact/summary.
  This remains partial coverage, not a promise that every description-only AI
  signal was examined. No source request limits were raised.
- Text-only YC/Getro detail pages cannot establish a missing regional salary, so
  those on-site candidates no longer consume detail requests. Provider parser
  recursion errors are isolated to that source, and response bodies are streamed
  with a decoded-byte limit rather than downloaded whole before the size check.
- The natural deeply nested JSON fixture was handled by the current parser runtime;
  an injected parser RecursionError established the error-boundary regression.
  Do not claim a particular live provider response triggered that exception.
- Writer diagnostic follow-up and evidence clarifications were propagated locally.
  Locked full candidate suite: 283 tests and 10 subtests passed; no live calls,
  pushes, merges to main or deployments. Further Claude review is outstanding.

## October 18 path diagnostic follow-up — writer cycle 8

- Claude confirmed missing-file classification and noted Path.expanduser/resolve
  can raise ValueError/RuntimeError. Both boundary regressions failed first.
  Input-read failures of those classes now become invalid_sync_input while known
  safe ValueError codes (including invalid_json and artifact_too_large) re-raise.
  Later writer errors retain unexpected_sync_error. No lock or retry logic changed.
- Locked writer suite: 160 tests and 10 subtests passed. Fresh local static review
  requested under the user's unlimited repair-cycle instruction; no push/live run.

## October 18 input diagnostic follow-up — writer cycle 7

- Claude confirmed the unexpected writer failure fix, then reproduced that missing
  input files inherited the new unexpected-error label. A failing regression
  confirms this happens before Google access. File-read OS errors now map to
  `invalid_sync_input` at the read boundary; the existing artifact checkout-path
  error has an explicit safe label. Later unexpected writer errors remain distinct.
- Locked suite: 158 tests and 10 subtests passed. No remote or live writes. User's
  unlimited local repair-cycle direction applies; fresh static review requested.

## October 18 retrospective diagnostic follow-up — writer cycle 6

- Claude's context-complete retrospective review of superseded #7 found a CLI
  diagnostic that still applied to current #8: an unexpected writer failure was
  mislabeled invalid input. A regression failed after an injected post-mutation
  exception; the CLI now emits fixed `unexpected_sync_error`, retaining recovery
  guidance and suppressing raw exception details. No retry policy changed.
- The retrospective adapter/engine coverage concern is already addressed by the
  current fake-workbook live-harness tests, including applied/unapplied timeout
  cases. Pending replay follows recorded journal order; operators must not edit
  hidden recovery state. The one-megabyte journal bound remains intentional.
- Locked writer suite: 157 tests and 10 subtests passed. Local review cycle 6 is
  covered by the user's "do as many as needed" direction; no pushes or live calls.

## October 18 user continuation instruction — review limits superseded

- After the source milestone reached its original three-review cap, the user
  explicitly directed "do as many as needed" for local fix/review cycles.
  Continue the necessary cycles while retaining the historical counters. This
  removes the prior numeric pause for this repair task; it does not authorize
  further pushes, merges, new services or deployment.
- Whole-PR Claude reviews were requested for #7, #8, #9 and #10, including already
  pushed heads. #7 is superseded; its retrospective findings are not instructions
  to revive it. #8 review at `e3536e4` found the missing `run_not_pending` CLI label.
  A failing CLI regression reproduced it, then the error was allowlisted.
- The reported sticky-lock-on-429 issue was not reproduced: 429 is already a
  rejected 4xx, and the existing fresh-receipt retry regression passed. Never
  treat a stale receipt as rejection proof for genuinely uncertain writes.
- This is writer repair/review cycle 5, authorized by the user's updated direction.
  No live calls ran; fresh Claude review of the local diagnostic fix is required.

## October 18 Codex review repairs — user-authorized extension

- Codex reviewed exact writer head `6a61f356d1e472f34ea6242a3c0b76bb02a88f6b`
  (the previously undelivered cycle 3). It reproduced reuse of a quarantined run ID
  when the damaged journal has no manifest. The #7 completed-Run-Log recovery issue
  is already fixed in #8 and is not a new outstanding repair.
- The user then instructed "Implement the changes", authorizing one additional
  writer fix/review cycle (4). Prior counters remain intact; this does not authorize
  an unlimited extension. Codex is the sole active implementation owner.
- Added an end-to-end regression: remove a pending run's manifest, quarantine its
  remaining chunks without changing their values, and refuse that ID before Jobs
  mutation. It failed on the reviewed code. Preparation now checks any quarantined
  key for the identity, including orphan chunks. Locked full suite: 155 tests and
  10 subtests passed; `git diff --check` passed. Fresh Claude review is required.
- This repair does not repeat live collection or Google writes, change deployment
  status, or satisfy the outstanding cloud/schedule acceptance gates.

### Source review repairs — local candidate for PR #10

- Initial Codex review covered source head
  `a17bae48313ab9b94ba13c97f4bba165dd327305`. The user requested implementation of
  its findings, then directed finishing locally without further pushes pending
  Claude Code review. This is the first source repair/review cycle; writer cycle 4
  above remains shared across #7/#8 and is not reset by these stacked branches.
- Regressions first reproduced cross-run duplicate rows, distinct URL paths being
  merged, South/Latin America passing the US filter, omitted Lever responsibility
  sections, and detail-page blocks being reported as HTTP 200 success.
- Reconciliation now retains the original Sheet ID/source, Date found and user
  fields when another source supplies the same employer link. First-seen source
  dates are retained in More details. Automatic cross-source reconciliation uses
  verified ATS requisition links; shared custom/generic links stop as ambiguous.
  Same-source distinct requisitions remain
  separate; ambiguous existing cross-source rows stop for operator reconciliation.
  No live rows are merged, deleted or repaired automatically.
- The collector and writer share URL identity logic. Paths/query keys/ports remain
  distinct; tracking is removed. Lever combines introduction, responsibility lists
  and additional description sections. The subsequent user location preference
  below supersedes the original blanket South/Latin America rejection.
- Detail HTTP/transport failures now retain their actual status/error.
  Already validated jobs can be delivered with
  explicit selected/valid-count evidence. Run Log retains the source-failure state.
- Stacked documentation conflicts were resolved by preserving both sides' counters
  and evidence. This does not change recorded cloud outcomes or deployment status.
- Local full suite: 234 tests and 10 subtests passed; `git diff --check` passed.
  No live source requests, Google writes or schedule tests ran. Fresh Claude review
  of the complete candidate is outstanding; do not treat old review badges as
  covering this patch. No further push is authorized by the current user direction.

### User location clarification and local review follow-up

- Keep remote South/Latin America leads regardless of salary. For on-site/hybrid
  roles in that region, only Colombia and the Dominican Republic qualify when an
  explicitly annual USD salary range reaches 70,000. Unknown currency/pay units,
  COP/DOP amounts and total compensation do not prove this exception. The threshold
  uses range overlap, consistent with PLAN.md. No role is labeled eligible here.
- Retain explicit Ashby remote metadata without replacing the original location.
  Built In now retains its actual structured salary currency instead of inventing
  USD; this matters when applying the regional salary exception.
- Supplementary Codex review found a generic-link ambiguity in the first local
  repair candidate: distinct requisitions could overwrite one historical row.
  A failing regression reproduced it. Such unverified cross-source links now stop
  before Jobs mutation; known ATS identities still reconcile across runs. This
  is not the required Claude review or an approval to push.
- Complete local candidate after the user's preferences and ambiguity repair:
  locked full suite passed 265 tests and 10 subtests; `git diff --check` passed.
  Remotive, RemoteOK, Himalayas and Jobicy retain their remote-only collection
  contract, and Ashby's explicit remote flag is preserved. Original locations are
  kept; missing pay currency/period is not invented. No live collection or Sheet
  writes ran. Claude review of this exact local candidate remains outstanding.

### Claude review of local patch and source repair cycle 2

- Claude reviewed the proposed `5487aa5` patch statically on PR #10, comment
  https://github.com/rrpichardo/Jobhunter/pull/10#issuecomment-6246077240 . It did not
  reconstruct the tree, verify the hash, or run tests; no such reviewer verification
  is claimed. Its medium finding was that a single unknown/custom-link match could
  block an entire daily run. That supersedes the initial conservative hard stop.
- Added failing regressions and fixed it: one uncertain custom-link match is now
  retained as a separate row with a stable possible-duplicate note. The collector
  also retains distinct unverified custom-link requisitions instead of merging
  them. Multiple existing candidates still stop before choosing between user data.
- Fixed the low finding about regional detail slots: a nonempty stub salary must
  satisfy the collection preference before fetching. Missing salary may still
  justify a bounded detail lookup for Colombia/the Dominican Republic. Tests prove
  a known USD 40k role does not consume a detail slot ahead of a matching role.
- Kept partial-source `failed` evidence after individual HTTP/transport failures:
  jobs still deliver, and valid/rejected counts explain the partial result. This
  preserves actual failure diagnostics rather than relabeling a failed request.
  Claude described that policy as defensible. Its informational YC salary-format
  concern remains a live-source verification limitation: ambiguous currency/units
  never qualify as USD annual pay by assumption; no new live fetch was performed.
- Source repair/review cycle 2 requires a fresh Claude review of the corrected local
  patch. Writer cycle 4's code is unchanged. Locked suite: 267 tests and 10 subtests
  passed; diff whitespace check passed. No further pushes, merges or deployment.

This is the durable log for implementation blockers and milestone repair cycles.
Read it before retrying work. Maximum: three distinct attempts per blocker and
three repair/review cycles per milestone. Counters survive handoffs and restarts.
Do not store secrets, raw email, cookies, or personal account data here.

The production daily routine never edits this document. Runtime source failures,
retry evidence, and daily social-collection allowances belong in protected cloud
run state and the Sources/Run Log records specified in the plan.

## Documentation handoff

- PR: https://github.com/rrpichardo/Jobhunter/pull/3
- Repair cycle 1: Claude reviewed `136dc4f`, found no blocking problems, and requested
  clearer follow-up wording, social verification limits, and an explicit attempt-log
  location. These clarifications were applied and submitted for re-review; see the
  PR for the final review result and reviewed revision.
- V0 application implementation has not started. No implementation blockers or
  runtime success claims are recorded yet.

## Record format for future blockers

For each blocker, record a stable name, affected requirement, attempt number/date,
sanitized evidence, the distinct approach tried, outcome, and next required action.
At the attempt limit, stop that blocker and state what changed condition or user
direction is required to resume. Do not reset a counter merely by renaming it.

## Bootstrap prerequisite PR #4 — October 17, 2026

- Branch: `codex/bootstrap-cloud-readiness`. Acceptance is locked setup, Linux and
  Windows CI, current Claude Code review, and an explicit capability inventory.
  This prerequisite PR does not complete M0 or authorize dependent implementation.
- Review cycle 1: local Claude Code Sonnet reviewed `e7c9c75` against `b37e483`;
  no actionable findings. Review posted to PR #4. Installation/test CI passed on
  both required platforms. New cloud evidence documentation will require review
  of the final revision; do not apply the old review to newer content.
- Existing GitHub Claude review workflows were preserved. Draft-PR check status
  alone is not treated as substantive feedback; local review text is recorded.

### Cloud credential delivery — attempt 1 / 3

- Requirement: secure service-account temporary file for Python Google auth.
- Approach/evidence: inspected JobHunterEnv UI and official cloud environment docs;
  bounded actual cloud probe found no established secret-file provider. Ordinary
  environment variables are explicitly visible; proxy secrets attach HTTP headers.
- Outcome: unresolved, not an authentication failure (no credential provisioned).
- Next action: identify and prove a supported protected credential delivery route
  within the existing approved budget before creating/provisioning a private key.

### Cloud persistent state and concurrency — attempt 1 / 3

- Requirement: protected state across distinct daily sessions and one atomic writer.
- Approach/evidence: inspected official routine/environment docs and actual cloud
  tool capabilities. New sessions and ephemeral VMs do not prove protected shared
  storage; no cross-session atomic lock was established.
- Outcome: unresolved. No session data or recovery artifacts have been stored.
- Next action: verify a supported durable store/lock and scheduler concurrency
  mechanism. Do not use a Sheet marker as an atomic lock or Git for secret state.

### Interactive cloud social authentication — attempt 1 / 3

- Requirement: user authenticates dedicated cloud LinkedIn/X sessions, then restores
  them across routine runs. Accounts remain not created per confirmed setup.
- Approach/evidence: actual cloud capability probe reports Chromium/Playwright
  installed but no LinkedIn MCP or supported user-operated login flow established.
- Outcome: setup unresolved; no live social request made, no challenge encountered.
- Next action: prove supported interactive cloud auth and protected persistence
  before asking the user to create/authenticate the dedicated accounts.

These are distinct unresolved prerequisites, not exhausted retries. The initial
cloud public Greenhouse fetch succeeded and is recorded in V0_VERIFICATION.md.

## October 17 continuation

- PR #4 merged as `7f77cb5` after Linux/Windows CI and fresh local Claude review of
  `4e104fa`. Post-merge `uv sync --locked` and the complete suite passed (6 tests,
  10 subtests). The user granted standing authorization for future Codex milestone
  merges after passing checks and a current Claude review; AGENTS.md records it.
- Existing automatic review plugin skips PRs once Claude has commented, so a
  green job alone is insufficient for updated revisions. Fresh local Claude
  reviews are available; preserve exact reviewed SHAs and post results to each PR.
- User confirms **no existing external cloud resources**. A proposed Cloudflare
  Free workaround was questioned as outside the plan and is not authorized.
  No Cloudflare implementation, account, or service activation is planned.

### Cloud prerequisites — attempt 2 / 3 (each existing blocker)

- Distinct approach: checked official provider alternatives and self-hosted runner
  availability instead of repeating the earlier live public-network probe.
- Credential delivery: Anthropic request-header secrets do not document provision
  of the private-key file required by the planned service-account auth. Google
  workload federation requires an identity provider credential that this runtime
  has not been shown to issue. No secret was provisioned or inspected.
- Persistent state/concurrency: no hosted Pro protected cross-session volume or
  atomic writer primitive established. Official self-hosted runners are documented
  for Team/Enterprise and require infrastructure, so they are not an approved
  substitute for the current Pro setup.
- Interactive cloud social auth: no documented user-operated browser handoff or
  session-restore mechanism established. A headless browser installation alone
  still does not satisfy the requirement. No social fetch/account setup attempted.
- Outcome: all three remain open. Do not count new-service research as an approved
  architecture change or perform another identical probe. Next action is a
  provider-supported mechanism within the approved plan; if none can be verified,
  report the specific limitation and obtain a scope decision. Independent Python
  implementation/testing can continue. One distinct attempt remains per blocker.
- Primary references: https://code.claude.com/docs/en/cloud-environments,
  https://code.claude.com/docs/en/routines,
  https://code.claude.com/docs/en/self-hosted-environments,
  https://docs.cloud.google.com/iam/docs/workload-identity-federation.

## M0 source/extraction code stage

- Branch `codex/m0-thin-pipeline`; acceptance and module interfaces are in
  `docs/superpowers/plans/2026-10-17-m0-data-path.md`.
- Initial tests observed failing before production modules existed; source,
  validation, HTTP and CLI tests now pass. A test-file parenthesis typo was fixed
  before its intended missing-module failures were verified; assertions unchanged.
- This stage has no Sheet writer, recovery, production auth or daily schedule.
  Review cycle 1 has not yet started; live code-path proof remains outstanding.

### User clarification after attempt 2

- User supplied local-login → direct cookie settings → fresh cloud restore as the
  intended social bootstrap. Adopt it without adding infrastructure. Interactive
  login inside the cloud VM is no longer required. This changes that prerequisite;
  it is not proof of authenticated collection, and counters are not reset.
- Non-secret pending work, markers and daily social allowances may live in Sheet
  `_State`; no secret cross-run session volume is needed under this approach.
  Atomic serialization and safe state reconciliation remain separate open gates.
- Cookie provisioning and tool compatibility still need testing, with no secret
  values printed or inspected. Current repo has no `.mcp.json`; select and pin the
  package before claiming a declared cookie-compatible MCP exists.
- Keep three attempts total per blocker across collector options.
  The proposed three fresh attempts per tool would reset the
  existing shared cap, so that portion of the suggestion was not adopted.
- Read-only primary-doc check: twscrape supports `auth_token` / `ct0` cookie
  activation (https://github.com/vladkens/twscrape). Its default indefinite account
  waits and rate-limit rotation are not approved runtime behavior. No live social
  request or authentication attempted; this is compatibility research, not a third
  attempt to provision/authenticate the missing accounts.

### M0 review/repair cycle 1

- Claude Code read the complete plan and reviewed `f913601` against `7f77cb5`.
  Review posted on PR #5. It reproduced protocol/proxy failures, per-item schema
  failure, absent-total coverage and input hygiene problems; it also ran all 43
  tests/10 subtests successfully without installing anything.
- Fixed with regressions: sanitize all HTTP errors and retain attempt/status/wait
  evidence; quarantine malformed items without dropping valid jobs; preflight
  output paths before fetching; unknown completeness when total is absent; strict
  URL whitespace and canonical board case; bounded nested JSON; explicit empty/
  partial extraction count/status; trusted-reference SHA-256 check; atomic
  exclusive artifact publication; remove obvious hidden markup from source text.
- Atomic publication regression was also run against the prior implementation
  and failed before the fixed full suite passed. No assertion was weakened.
- The source API's public post ID remains the M0 key; the official API documents
  its uniqueness (https://docs.greenhouse.io/job-board.html). Broader cross-source
  or multiple-post/requisition reconciliation is not implemented or claimed by
  this one-post M0 stage. Speculative repost equivalence is not inferred.
- Artifact hash checks depend on a trusted reference retained outside source
  artifacts; they are not protection against an agent changing both file and
  reference. HTML cleaning does not execute CSS or prove rendered visibility.
- `uv run --locked python -m pytest -q`: 57 passed, 10 subtests passed. The full
  changed revision, including user-supplied cookie/bootstrap documentation, must
  receive a fresh review and affected cloud checks before merge.

### M0 review/repair cycle 2 and new setup direction

- Claude reviewed `aaed72b` and confirmed original findings resolved. New findings:
  Windows newline translation broke returned digests; nested server JSON could
  escape error handling; lone surrogates lost evidence; inconsistent-empty and
  duplicate-ID paths lost failure metadata; some storage wording was stale.
- Fixes: publish exact binary JSON bytes (ASCII escaping supports surrogates) and
  hash those same bytes; catch server JSON recursion; preserve schema-error attempt/
  HTTP evidence; report positive-total/empty lists as failed; align current setup
  and handoff wording with user-approved Sheet state and credential bootstrap.
- Regression failures were reproduced before fixing; the digest byte-equality test
  also runs on Windows CI. Full local suite: 61 tests, 10 subtests passed.
- Actual cloud recheck at `aaed72b` passed locked installation, 57 tests/10 subtests,
  a new single-request Greenhouse harvest (655 valid, 0 rejected, 15 PM candidates,
  1 selected, complete-response) and trusted-digest validation (1 record, exit 0).
  Commands and outputs were inspected in the UI. This predates the binary-output
  fix; recheck affected tests and saved-data validation without another live fetch.
- User approved the Google credential-variable fallback with workbook-only Editor,
  no project IAM roles, Sheets API only, in-memory loading or private 0600 temp-file
  cleanup. First inspect compatible GCP secret types. Re-inspection confirmed Add
  secret disabled, so types could not be inspected; no key/variable was entered.
- Review cycle 3 is the final allowed review/repair cycle for this PR. Submit the
  fixed current revision for review; do not merge unresolved actionable findings.

### M0 cycle 3 result — blocked from merge

- Claude reviewed `2a7e7dfa1af561cc017d8abade5474e6a47e7183`, ran 61 tests/10
  subtests, and confirmed the cycle-2 fixes. One remaining actual edge case:
  non-finite Retry-After values (`inf` / `1e999`) flow into failure metadata and
  prevent strict JSON serialization, losing the source-failure artifact.
- PR #5 remains unmerged. The three-cycle cap has been reached. The next action
  is a user decision to authorize one additional fix/review cycle or leave the
  PR open. Do not automatically reset/increase the cap or advance dependent code.
- Proposed bounded repair: reject non-finite retry delays, preserve finite HTTP
  status/attempt evidence, and add a CLI-level regression. Require another Claude
  review of the resulting exact head plus Linux/Windows checks before merging.

### Google Cloud setup access — attempt 1 / 3

- Inspected the selected account's Google Cloud console for the planned service
  account setup. Console reports Cloud access unavailable; no project/API/billing
  or credential changes made. No personal account identifiers are recorded here.
- User directed switching to another existing Google account. Account chooser is
  open; the specific account selection is pending. Do not create another account
  or attempt to bypass the access restriction. This is distinct from credential
  injection compatibility; its counter does not reset the earlier blockers.

### M0 cycle 4 — explicit one-cycle extension authorized

- User authorized exactly one additional fix-and-Claude-review cycle for PR #5.
  This extends the milestone counter to 4; it does not reset prior cycles or
  authorize a fifth cycle.
- Reproduced the missing failure artifact with CLI regressions for `inf` and
  `1e999` Retry-After values before the fix. Ignore non-finite or negative header
  delays and retain bounded local backoff; valid finite delays remain honored.
- Added CLI coverage for infinity, overflow, NaN and negative headers, checking
  three attempts, bounded waits and retained HTTP 429 evidence.
- `uv run --locked python -m pytest -q`: 65 passed, 10 subtests passed.
  `git diff --check` passed. Fresh exact-head Claude review and CI remain required.
- The user selected a different existing Google account and signed in. The
  Cloud console now opens successfully; an existing free trial is shown. No
  billing settings were changed, and no credentials have been created or entered.

### M0 first-stage integration and Google setup progress

- Cycle 4 review of `0f7b43659a496c80a25079dd9107ccda1439e154`: Claude
  Code Sonnet found no unresolved actionable findings. Linux/Windows CI passed.
- Actual JobHunterEnv replay at that exact head: locked sync exit 0; Python
  3.12.3 / uv 0.13.1; 65 tests and 10 subtests passed; saved harvest/extraction
  accepted the original trusted digest, 1 validated record, exit 0. No new live
  fetch, Sheet write or social access. Tool command outputs inspected in UI.
- PR #5 merged under standing authorization at `d77842d`; main tests passed
  again. This completes only the first M0 harvest/extraction stage.
- Dedicated Google project created outside the organization without selecting
  a billing account. Sheets API enabled. Dedicated writer service account created
  with no project roles. User explicitly confirmed workbook-only Editor sharing
  (notifications off) and JSON key creation. UI confirmed shared workbook and
  downloaded key; agent did not open/read the key.
- Reinspection now shows Add secret enabled and a GCP access token (with Service
  Account Key) type. This supersedes the earlier disabled-control evidence.
  Prepared host sheets.googleapis.com, workbook-specific path prefix and Sheets
  scope, with no impersonation. User is entering JSON directly; save and live
  Python compatibility remain outstanding. Do not use the variable fallback
  unless this preferred mechanism proves unavailable/incompatible.

### M0 writer branch — authentication foundation (not deployed)

- New feature branch `codex/m0-sheet-writer` starts from merged PR #5.
- Wrote failing connection/configuration/sanitization tests, then the explicit
  network-secret-only gspread connection helper. Full locked suite: 70 tests,
  10 subtests passed; diff whitespace check passed. No real Google API call.
- User is saving the preferred GCP secret directly. Pause screen inspection
  during private input. Next live action after user confirms saved/closed:
  read-only Python workbook access in actual JobHunterEnv, with metadata counts
  only in output. Do not print headers, auth/session internals, keys or tokens.
- Independent read-only helper checked the proposed sheet-creation lock against
  Google's atomic batch and unique ID/title documentation. It is a candidate for
  compliant writers, not a supported lock primitive or protection against human
  lock deletion. Live overlap proof remains mandatory. No writer code yet.

### Connection checkpoint PR #6 — review cycle 1 / 3

- PR #6: https://github.com/rrpichardo/Jobhunter/pull/6 . Claude reviewed exact
  `0260388`, found no blocking bug, and identified actionable safe-diagnostic and
  handoff consistency issues. Its plan-mode restrictions prevented running tests;
  local and Linux/Windows CI passed 70 tests/10 subtests independently. No invented
  reviewer test execution is claimed.
- Add allowlisted error categories / numeric HTTP status so a bounded failed auth
  attempt is diagnosable without provider bodies. New test first failed, then the
  full locked suite passed 71 tests/10 subtests. Clarify preferred auth in plan,
  user-authorized key use, write-endpoint proof still needed, and current counters.
- Credential-delivery attempt 3 / 3 now tests the newly available GCP network
  secret after the relevant external capability changed. No counter reset:
  earlier two delivery investigations remain recorded. Secret configuration
  succeeded; actual Python connectivity is being checked once. If incompatible,
  stop this blocker and report evidence/next action rather than trying repeatedly.
- User pasted the key into chat and expressly accepted disclosure and authorized
  continued use. Agent recommended replacement; user direction supersedes the
  earlier mandatory-rotation handoff. No key value is stored in repository or logs.
  Direct native JSON copy/paste saved the restricted GCP secret; non-secret
  workbook/auth-mode variables saved too. No application Sheet write occurred.
- Fresh current-revision review is required after these fixes (cycle 2 / 3).

- Credential delivery attempt 3 result: **initial read access succeeded** in
  JobHunterEnv at `0260388`. One bounded connection attempt (workbook open plus
  worksheet metadata read), `RESULT=success tab_count=1`, exit 0, tree clean.
  Actual command output expanded/verified. This resolves initial delivery/read
  connectivity, not write endpoints, recovery or serialization. No Google writes.
- Cycle 2 / 3 is the fresh review of the safe-discriminator and handoff fixes.
  Local locked suite: 71 tests/10 subtests passed. No secret value in tracked files.

## M0 writer/recovery implementation — continuation

- PR #6 merged at `fa899c32de3267507c51658274d5bc2509ef7193` after exact-head
  Claude cycle-2 review, 71 tests/10 subtests locally and in JobHunterEnv, plus
  Linux/Windows CI. Main rerun passed 71 tests/10 subtests. Code is a connection
  foundation only. User then directed Codex to continue rather than hand off now.
- New owner branch: `codex/m0-sheet-sync`; Codex remains sole implementer.
- Write-endpoint proof attempt 1 / 3 succeeded in actual JobHunterEnv at229a97b:
  one atomic addSheet/updateCells structural call created hidden `_M0AuthProbe`
  (sheet ID 2026101801), and one RAW values batch wrote a harmless literal.
  FORMULA readback exactly matched `=jobhunter_probe_literal`; it was not executed
  as a formula. All reported booleans true, exit 0, clean tree. Tool output
  expanded/verified. No retry, user cells unchanged, probe tab retained.
  This proves endpoint compatibility, not application writer/recovery/concurrency.
- Wrote failing planner, lock and adapter tests, then implementations. Planner
  tests preserve user fields/first seen, reordered headers, sorted rows, duplicate
  identities, ambiguous headers and RAW-ready literal values. Lock tests cover
  overlap and uncertain acquisition/deletion. Adapter tests prove atomic owner
  creation, RAW range writes, append-only grid growth and sanitized HTTP evidence.

- Journal, engine and CLI now pass test-first behavior checks, including bounded
  retries, exact long-delay stop, explicit pending Run Log before job mutation,
  same-ID repeat verification, multi-chunk replay and corruption rejection.
- `uv run --locked python -m pytest -q`: 107 tests/10 subtests passed locally;
  diff whitespace check passed. Application writer live proof and fresh Claude
  review remain outstanding; no milestone completion or deployment claim.

### M0 writer review/repair cycle 1 / 3

- First whole-change Claude Code review is being requested for the writer branch.
  It must cover the current committed head, not just the connection checkpoint.
  No existing review covers the new journal/lock/writer. Record findings and
  preserve this counter across handoffs; no review success is assumed in advance.


### User-requested Claude Code handoff — writer cycle 1 remains open

- Review of 4c9800c completed; actual findings posted on PR #7 at
  https://github.com/rrpichardo/Jobhunter/pull/7#issuecomment-6243645600 .
  Current fixes address control/line-ending validation, scoped journal checks,
  delayed-write safety with atomic unique receipts, hidden HTTP resubmissions,
  original-error preservation and release-outcome diagnostics. Read-only Astra
  analysis supported the receipt design; no second implementation owner edited.
- Internal test namespace added after its regression test failed as expected.
  Global lock remains shared. Full local suite:125 passed,10 subtests passed.
  Fresh current-head review is still outstanding; cycle2 has NOT been started.
- Remaining cycle-1 work: manual poisoned-journal quarantine/recovery, preventing
  completed Run Log downgrade on replay, additional uncertainty tests. Per-run
  source history and all application live checks remain outstanding.
- User now requests stopping for a committed/pushed handoff and PR. Preserve
  draft #7; no merge or deployment claim. CLAUDE_HANDOFF.md has exact next actions.
- Billing: user chose to leave existing free-trial link unchanged; dialog canceled,
  project linkage rechecked. No billing setting changed. Do not repeat this ask.

- Final handoff verification: `uv run --locked python -m pytest -q` passed
  125 tests/10 subtests; `git diff --check` passed. No new live API collection,
  writer mutation, or scheduled proof was attempted during handoff preparation.
- Reciprocal review: AGENTS.md/CLAUDE.md require Codex review for Claude work.
  User signed into ChatGPT in Richard. Official review settings load but show no
  repositories, including Jobhunter search; no saved Codex Cloud environments.
  Automatic review remains blocked on repository connection, not user sign-in.
  No permission, credits, billing or automatic-review setting changed. Local
  installed `codex review --help` verified; manual review route documented.

### Claude Code takeover of writer milestone — review cycle 2 / 3 requested

- Claude Code is now sole implementation owner. Branch `claude/m0-sheet-sync` starts
  at checkpoint `9f4fd58` (PR #7 head); replacement PR supersedes draft #7. Counters
  are carried over, not reset: writer review cycle 1 / 3 was consumed by the review
  of `4c9800c`; this push is the fix set for it and requests **cycle 2 / 3**
  from Codex (reciprocal review; no self-review).
- Finished the remaining cycle-1 fixes, tests first (3 failed before the code):
  a recovered run whose final Run Log row already landed is no longer rewritten to
  `pending`; manual `--quarantine-run` renames a poisoned run's `_State` keys without
  discarding values and refuses reuse of that run ID. Added receipt tests: failed
  receipt read, definitive 429 followed by a fresh-receipt retry, 408/500/503 treated
  as unknown, and an interrupt through the engine retaining the lock.
- `.venv/bin/python -m pytest -q`: 136 passed, 10 subtests. Still open: per-run
  source history, the paced live harness, actual JobHunterEnv proof, scheduled M0.

- Codex GitHub review of `d76caef` was started but not delivered (user reports its
  usage limit was reached). A same-model Claude `/engineering:code-review` was run on
  the user's instruction; it is **not** the required Codex review and does not count
  as approval. It produced minor findings, fixed in the next commit (completed runs
  cannot be quarantined, original Completed time kept on recovery, quarantine no
  longer creates `_State`, cell-count cap). Suite: 139 passed, 10 subtests.
  The new head still needs Codex review; no merge until it is obtained. The review
  counter stays at cycle 2 / 3 because these are self-review fixes, not a Codex cycle.

- Codex completed its review of `d76caef` (cycle 2 / 3): one P2 finding, refuse to
  quarantine completed runs; already fixed in `99b1154`. Cycle 3 / 3 (final) was then
  requested from Codex for `99b1154`. No further cycle remains for this milestone
  without a user decision. The earlier "never returned" note above is superseded.

### Writer live harness result (JobHunterEnv, October 18, 2026)

- Codex cycle 3 / 3 for `99b1154`: the GitHub reviewer answered only that its usage
  limit was reached (resets Oct 18, 12:12 AM per the local CLI). A local
  `codex review` fallback hit the same limit. **No cycle-3 review was delivered; no
  fourth cycle was started.** Request the same review again after the reset; do not
  buy credits or change plan.
- Built `scripts/live_harness.py` (commit `c5e2398`); the actual cloud run passed all
  eight clean scenarios, exit 0. Details: V0_VERIFICATION.md. Counters unchanged:
  this is a test of the existing writer, not a new blocker attempt.
- The saved real-posting data from the earlier cloud session no longer exists (the
  container was reclaimed, as the handoff warned). The user then approved one fresh
  bounded public harvest with an independently retained hash; see the next section
  once recorded.

### Real posting write result (JobHunterEnv, October 18, 2026)

- One fresh bounded Greenhouse harvest (655 items, 1 selected) was approved and run
  because the earlier saved data was lost. Real write `m0-real-001` and its identical
  repeat both exited 0 with one Jobs row and one Run Log row; lock released afterwards.
  Evidence and the retained digest are in V0_VERIFICATION.md. No new attempt-counter
  blocker was consumed; scheduled M0 remains the next gate.

### Multi-source probe and delivery (JobHunterEnv, October 18, 2026)

- Built the source registry, per-source parsers and `scripts.source_probe`. The actual cloud
  run reached 35 sources and recorded 9 as needs setup; 136 AI-PM matches from 24 sources
  were delivered and verified (V0_VERIFICATION.md). No source was blocked and no
  429/challenge occurred, and no retry was made.
- LinkedIn and X were **not attempted**: their dedicated accounts and cookies do not exist
  (the user's step), so they remain `needs setup`, not a completed test. This consumes no
  attempt from the social-auth blocker counter.
- Gmail: connector `list_labels` shows no `JobHunter` label; forwarding/label setup is open.
