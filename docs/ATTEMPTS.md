

### Multi-source probe and delivery (JobHunterEnv, October 18, 2026)

- Built the source registry, per-source parsers and `scripts.source_probe`. The actual cloud
  run reached 35 sources and recorded 9 as needs setup; 136 AI-PM matches from 24 sources
  were delivered and verified (V0_VERIFICATION.md). No source was blocked and no
  429/challenge occurred, so no stop rule fired and no retry was made.
- LinkedIn and X were **not attempted**: their dedicated accounts and cookies do not exist
  (the user's step), so they remain `needs setup`, not a completed test. This consumes no
  attempt from the social-auth blocker counter.
- Gmail: connector `list_labels` shows no `JobHunter` label; forwarding/label setup is open.

