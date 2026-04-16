# Hermes Watch Upgrade Note — Registry-First Scheduler and Candidate-Aware Handoff

Date: 2026-04-15

## Why this step
The system already had ranked candidate state plus routing/handoff artifacts, but routing still did not truly behave like a registry-first scheduler. This step makes the next-candidate choice come from ranked candidate state and threads that choice into the refinement registry entry before orchestration and dispatch preparation.

## What changed
- Extended `scripts/hermes_watch_support/harness_routing.py`
- Added `select_next_ranked_candidate(repo_root)`
- `build_probe_routing_decision(repo_root)` now includes selected candidate metadata from the ranked registry
- `route_harness_probe_feedback(repo_root)` now writes selected candidate metadata back into the chosen refinement queue entry before orchestration and dispatch bundle creation
- Existing CLI path `--route-harness-probe-feedback` now emits candidate-aware handoff data

## Current scheduler behavior
This is still intentionally conservative:
- `review-current-candidate` keeps the feedback candidate
- otherwise select the highest-ranked candidate not currently marked `review_required`
- if no such candidate exists, fall back to the top-ranked candidate

## Why this matters
This is the first step where the ranked candidate registry is part of actual handoff control rather than passive bookkeeping. The loop is now closer to:
- probe outcome
- feedback bridge
- ranked candidate update
- registry-first candidate selection
- candidate-aware routing/handoff
- orchestration/dispatch preparation

## Important limitation
This is not a full scheduler yet.
It does not yet:
- let orchestration queue ordering depend directly on candidate rank or debt
- model build debt / smoke debt / seed debt separately in selection
- push selected candidate metadata through bridge launch and verification prompts deeply
- decay or rebalance scores over time

## Recommended next step
- make refiner orchestration queue selection itself candidate-aware and registry-first
- then enrich selection with multi-dimensional debt signals so the scheduler is not only status-gated
