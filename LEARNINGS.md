# Lessons learned in this project

Short, specific, evidence-backed. Newest first. The shared system reads this file at the start of each session
here and at the monthly review. Never put links, secrets or personal data in it.

## 2026-11-08 · claude/readme-latest
- **When code groups or merges records, test every ordering of the same input and compare the answers, and test the same item under different link spellings.** _Evidence: a tool whose nine tests all passed counted one job as two (or one) depending on input order, and counted one Greenhouse job twice when one link had a tracking tag; both were found only by running real-shaped inputs, then locked in with shuffle tests._

## 2026-11-08 · claude/docs-status-followup
- **Before editing files in a shared checkout, run a status check for uncommitted changes and the current branch, and do the work in a separate worktree if another session has edits there.** _Evidence: the checkout switched to another branch with uncommitted edits to the same four status documents while a pull request touching them was open, so the two sets of edits conflicted in two files and duplicated a note in two others._

## 2026-11-08 · claude/readme-about
- **Compare the checked-out branch with the remote main before writing status text, and update every status document in the same change that merges a pull request.** _Evidence: the checkout was 186 commits behind the remote main, and four documents (START_HERE, PENDING, the Codex review queue and the handoff) still called an already-merged pull request unreviewed and the closed one "kept open"; the README said nothing was deployed or built beyond the first stage._
- **Check a claimed review state against GitHub (reviewed commit, merge time, checks) rather than the documents.** _Evidence: the documents were the only source saying "waiting for Codex"; GitHub showed a clean review of the final commit and a merge on October 23._
