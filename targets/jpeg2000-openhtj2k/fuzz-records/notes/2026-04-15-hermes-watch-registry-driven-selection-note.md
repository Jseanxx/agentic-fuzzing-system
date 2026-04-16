# Hermes Watch Upgrade Note — Registry-Driven Next Candidate Selection and Handoff Integration

Date: 2026-04-15

## Why this step
The system already had probe feedback, routing, and a ranked candidate registry, but routing still effectively followed the feedback artifact rather than explicitly consuming ranked candidate state. This step makes the next-candidate choice registry-driven and threads the selected candidate through handoff artifacts and queued refinement entries.

## What changed
- Extended `scripts/hermes_watch_support/harness_routing.py`
- Added `select_next_ranked_candidate(repo_root)`
- Routing decisions now expose:
  - `selected_candidate_id`
  - `selected_entrypoint_path`
  - `selected_recommended_mode`
  - `selected_target_stage`
- `route_harness_probe_feedback(repo_root)` now writes selected candidate metadata back into the relevant refinement registry entry before orchestration/dispatch preparation
- Existing CLI path `--route-harness-probe-feedback` now emits registry-driven selected-candidate data in the handoff artifact

## Current behavior
This is conservative and still intentionally simple:
- `review-current-candidate` keeps the feedback candidate
- other routes select the highest-ranked candidate that is not already marked `review_required`
- if no eligible candidate is found, routing falls back to the top-ranked candidate when available

## Why this matters
This is the first point where the ranked candidate registry becomes part of the actual control plane rather than passive bookkeeping. The loop is now closer to:
- probe outcome
- feedback bridge
- ranked candidate update
- registry-driven next candidate selection
- orchestration/dispatch handoff

## Important limitation
This is not yet a fully candidate-aware scheduler.
It does not yet:
- use separate debt dimensions (seed/smoke/build/review) in selection
- let orchestration queue ordering depend directly on candidate rank
- propagate selected candidate metadata deeply into bridge launch and verification prompts
- maintain historical selection confidence or decay

## Recommended next step
- make orchestration queue selection candidate-aware and registry-first
- then enrich scoring/selection using distinct debt signals and repeated outcome history rather than a coarse action-code gate
