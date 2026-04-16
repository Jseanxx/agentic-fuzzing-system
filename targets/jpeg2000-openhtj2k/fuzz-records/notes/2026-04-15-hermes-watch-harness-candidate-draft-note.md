# Hermes Watch Upgrade Note — Harness Candidate Draft Generator

Date: 2026-04-15

## Why this step
The system can now produce a target reconnaissance artifact and a profile auto-draft. The next low-risk bridge toward semi-autonomous fuzzing is generating a reviewable harness candidate draft from those artifacts before attempting code mutation or harness synthesis.

## What changed
- Added `scripts/hermes_watch_support/harness_draft.py`
- Added `build_harness_candidate_draft(repo_root)`
- Added `write_harness_candidate_draft(repo_root)`
- Added CLI mode: `--draft-harness-plan`
- Draft mode writes:
  - harness candidate manifest JSON
  - harness candidate markdown plan
- Output location:
  - `fuzz-records/harness-drafts/`

## Current harness draft behavior
This is conservative and heuristic-driven:
- starts from reconnaissance entrypoint candidates and stage candidates
- derives candidate harness entrypoint paths
- suggests a recommended mode (`parse`, `decode`, `deep-decode`, or exploratory-auto-draft)
- records smoke seed and build assumptions as text notes
- explicitly marks all candidates as requiring human review before code generation

## Important limitation
This is **not** harness code generation yet.
It does not:
- emit buildable harness source files
- patch target code
- confirm entrypoints are callable APIs
- validate candidates with real smoke/build probes

## Why this matters
It adds the next artifact in the future loop:
- target repo -> recon manifest
- recon manifest -> profile auto-draft
- recon/profile -> harness candidate draft

That means the system can now move one step deeper toward your final loop without skipping into unsafe autopilot.

## Recommended next step after this
- add code-aware harness skeleton generation for reviewed candidates
- then add short build/smoke evaluation plans for the top 1-2 candidate harnesses
