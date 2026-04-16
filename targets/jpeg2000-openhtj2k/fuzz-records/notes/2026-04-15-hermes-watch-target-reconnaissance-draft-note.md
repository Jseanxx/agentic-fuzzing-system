# Hermes Watch Upgrade Note — Target Reconnaissance Draft and Auto-Draft Artifact

Date: 2026-04-15

## Why this step
The project now has a profile subsystem and minimal target adapter seam. The next step toward semi-autonomous multi-target fuzzing is a conservative reconnaissance layer that can inspect a new repo, infer likely build/runtime structure, and emit reviewable draft artifacts instead of jumping directly to destructive harness generation.

## What changed
- Added `scripts/hermes_watch_support/reconnaissance.py`
- Added `build_target_reconnaissance(repo_root)`
- Added `write_target_profile_auto_draft(repo_root)`
- Added low-risk CLI mode: `--draft-target-profile`
- Draft mode writes:
  - recon manifest JSON
  - target profile auto-draft YAML
- Output location:
  - `fuzz-records/profiles/auto-drafts/`

## Current reconnaissance behavior
This is intentionally conservative and shallow:
- build system detection via repo markers (`CMakeLists.txt`, `meson.build`, `Makefile`, etc.)
- source file discovery by extension
- stage inference from filenames (`parse`, `decode`, `cleanup`, etc.)
- entrypoint candidate inference from filename keywords
- draft YAML generation with stage candidates, telemetry stage names, and stage-file-map hints

## Important limitation
This is **artifact-first reconnaissance**, not real semantic program understanding.
It does not yet:
- parse ASTs
- inspect symbols
- infer binary exports
- identify real harness APIs with high confidence
- propose code patches automatically

## Why this still matters
It creates the first reusable path for:
- new target repo in
- generate structured target-analysis artifact
- generate target-profile draft
- review/refine before harness generation

That is the right low-risk bridge between current OpenHTJ2K specialization and future multi-target automatic harness iteration.

## Recommended next step after this
- strengthen reconnaissance using symbols/build outputs instead of only filename heuristics
- then add harness-candidate draft generation on top of reviewed target profiles and adapters
