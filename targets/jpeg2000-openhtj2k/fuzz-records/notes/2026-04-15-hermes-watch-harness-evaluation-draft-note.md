# Hermes Watch Upgrade Note — Harness Candidate Evaluation Draft

Date: 2026-04-15

## Why this step
The system can already emit target reconnaissance, a target profile auto-draft, and a harness candidate draft. The next low-risk bridge is a short evaluation artifact for the top harness candidates so the pipeline can decide what to build/smoke-check first without jumping straight into harness code generation.

## What changed
- Added `scripts/hermes_watch_support/harness_evaluation.py`
- Added `build_harness_evaluation_draft(repo_root)`
- Added `write_harness_evaluation_draft(repo_root)`
- Added CLI mode: `--draft-harness-evaluation`
- Draft mode writes:
  - harness evaluation manifest JSON
  - harness evaluation markdown plan
- Output location:
  - `fuzz-records/harness-evaluations/`

## Current evaluation draft behavior
This is intentionally conservative and artifact-first:
- starts from harness candidate drafts, not from direct code mutation
- selects the top 1-2 candidates with a shallow priority heuristic
- records expected success signals for each candidate
- records fail-fast criteria for build ambiguity, missing seeds, and immediate smoke crashes
- records low-risk execution plan steps before any harness skeleton generation

## Important limitation
This is **not** real execution or harness synthesis yet.
It does not:
- compile candidates
- verify callable APIs
- generate harness source files
- score candidates using real build/smoke evidence
- close the loop automatically from evaluation failure back into recon/profile updates

## Why this matters
It adds the next artifact in the chain:
- target repo -> recon manifest
- recon manifest -> profile auto-draft
- profile/recon -> harness candidate draft
- harness candidates -> top-candidate evaluation draft

That is the right low-risk step before introducing harness skeleton generation or smoke execution automation.

## Recommended next step after this
- run short real build/smoke probes for the top candidate under strict fail-fast policy
- then use those outcomes to drive harness skeleton generation only for candidates that pass review and smoke assumptions
