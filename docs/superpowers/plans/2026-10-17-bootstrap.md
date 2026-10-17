# Reproducible setup and cloud readiness implementation plan

**Goal:** Establish the reproducible development prerequisite for M0; do not
represent this PR as completed M0 or V0 deployment.

**Spec:** `docs/PLAN.md`, especially dependency installation, cloud handoff, and M0;
`docs/IMPLEMENTATION_PROMPT.md` steps 1–2. The user explicitly requested execution
of this existing plan. Preserve its design rather than creating a replacement.

**Architecture:** One implementation owner edits configuration and documentation.
Read-only lower-cost agents inspect requirements and existing experiments in
parallel. Production remains Claude Code cloud; no local operational substitute.

**Files:** `pyproject.toml`, `uv.lock`, `.python-version`, `.gitignore`,
`.github/workflows/checks.yml`, `README.md`, setup/attempt/evidence documents.

## Acceptance and steps

- [x] Pin uv and Python 3.12; resolve the six mandated runtime libraries and pytest
  into a committed lock. Do not install unverified social integrations.
- [x] Verify `uv sync --locked`, runtime imports, and the full existing offline
  test suite locally. No new behavior is added, so no new behavior tests are needed.
- [x] Run the same installation/import/test checks in Linux and Windows CI.
- [x] Inspect actual Claude routine/environment UI without credentials in logs;
  record supported capabilities separately from unknown or blocked ones.
- [x] Record source/access inventory and precise next actions; keep all M0 live
  gates (Greenhouse → extraction → Sheet, recovery, schedule, persistence) open.
- [ ] Commit and open a prerequisite milestone PR; obtain Claude Code review of
  the current code revision, resolve findings within the repository cycle limit,
  and rerun affected checks. Ask for merge direction once the PR is reviewable.

## Review focus

- A passing probe suite must not be described as application/cloud success.
- CI must install from the committed lock on both required operating systems.
- Existing probes and the user's untracked files must be preserved.
- No secrets or personal account details enter repository evidence.
- No daily routine is enabled before its application and recovery checks exist.

## Progress

- Read-only research complete; no competing implementation editors.
- In-place feature branch `codex/bootstrap-cloud-readiness` preserves the existing
  checkout and untracked file. No separate worktree was needed for this config PR.
