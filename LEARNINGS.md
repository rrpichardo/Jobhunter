# Lessons learned in this project

Short, specific, evidence-backed. Newest first. The shared system reads this file at the start of each session
here and at the monthly review. Never put links, secrets or personal data in it.

## 2026-11-08 · claude/readme-about
- **Compare the checked-out branch with the remote main before writing status text, and update every status document in the same change that merges a pull request.** _Evidence: the checkout was 186 commits behind the remote main, and four documents (START_HERE, PENDING, the Codex review queue and the handoff) still called an already-merged pull request unreviewed and the closed one "kept open"; the README said nothing was deployed or built beyond the first stage._
- **Check a claimed review state against GitHub (reviewed commit, merge time, checks) rather than the documents.** _Evidence: the documents were the only source saying "waiting for Codex"; GitHub showed a clean review of the final commit and a merge on October 23._
