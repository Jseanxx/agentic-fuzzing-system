# Hermes Watch Upgrade Note — Harness Probe Outcome Feedback Bridge

Date: 2026-04-15

## Why this step
The system could already run a very small fail-fast build/smoke probe for a top harness candidate, but those outcomes were not yet connected back into the refinement substrate. This step adds the bridge that turns probe outcomes into queued refinement work and reviewable feedback artifacts.

## What changed
- Added `scripts/hermes_watch_support/harness_feedback.py`
- Added `bridge_harness_probe_feedback(repo_root)`
- Added CLI mode: `--bridge-harness-probe-feedback`
- Feedback bridge writes:
  - probe feedback JSON
  - probe feedback markdown artifact
- Output location:
  - `fuzz-records/probe-feedback/`
- The bridge also records entries into existing refinement registries under:
  - `fuzz-artifacts/automation/`

## Current feedback-bridge behavior
This is intentionally conservative and reuses existing refinement buckets:
- build probe failed -> `halt_and_review_harness`
- smoke probe failed -> `halt_and_review_harness`
- smoke probe skipped with no seed candidates -> `minimize_and_reseed`
- probe passed cleanly -> `shift_weight_to_deeper_harness`

## Important limitation
This is not a full adaptive loop yet.
It does not yet:
- distinguish many nuanced skipped-smoke or ambiguous-build cases
- feed directly into verification/retry lifecycle stages
- auto-launch the next refinement orchestration step
- update target profiles or adapters directly from feedback evidence

## Why this matters
This is the first true bridge from executed micro-probes back into the semi-autonomous refinement substrate:
- recon -> profile draft
- profile -> harness draft
- harness draft -> evaluation draft
- evaluation -> short probe
- short probe -> queued refinement feedback

That closes an important part of the loop without jumping into unsafe autopilot.

## Recommended next step after this
- connect feedback entries into the existing refiner orchestration/verification pipeline automatically
- then use verified probe feedback to gate harness skeleton generation or candidate demotion/promotions
