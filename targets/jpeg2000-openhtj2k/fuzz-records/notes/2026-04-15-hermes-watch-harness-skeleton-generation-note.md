# R19 Harness Skeleton Generation + Revision Loop

## Summary
R19 adds a conservative harness skeleton draft layer on top of the existing evaluation/probe/candidate-registry flow.

## What was added
- `scripts/hermes_watch_support/harness_skeleton.py`
- `build_harness_skeleton_draft(repo_root)`
- `write_harness_skeleton_draft(repo_root)`
- Hermes CLI flag: `--draft-harness-skeleton`

## Current behavior
- Skeleton selection prefers:
  1. latest feedback-linked ranked candidate
  2. top ranked candidate from `ranked-candidates.json`
  3. top evaluation candidate as fallback
- Emitted artifacts now include:
  - manifest JSON
  - markdown plan/note
  - draft harness source (`.c` or `.cpp`)
- Skeleton source always stays low-risk:
  - `LLVMFuzzerTestOneInput` stub only
  - minimal input gating helper
  - TODO wiring comment for the selected entrypoint

## Revision loop in this step
- If a previous skeleton exists for the selected candidate and latest feedback is review/reseed oriented, the new draft becomes a `revision`.
- `revision_number` increments from the previous skeleton manifest.
- revision loop notes emphasize:
  - build/linkage review
  - smoke seed replay under sanitizers
  - smallest-safe-diff policy

## Caveat
This is still an artifact-first revision loop, not a closed compile/fix/verify autonomous loop yet.
Next useful step: feed actual build/smoke verification outcomes back into skeleton-specific scoring and targeted patch suggestions.
