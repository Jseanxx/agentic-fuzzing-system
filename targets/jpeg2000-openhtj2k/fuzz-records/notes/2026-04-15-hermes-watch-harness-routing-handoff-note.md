# Hermes Watch Upgrade Note — Feedback-Driven Candidate Routing and Handoff

Date: 2026-04-15

## Why this step
The system could already bridge short probe outcomes back into refinement registries, but the loop still stopped short of selecting a route and producing the next orchestration handoff. This step adds a routing layer that converts probe feedback into a candidate route label and immediately prepares/dispatches the corresponding refiner handoff artifacts.

## What changed
- Added `scripts/hermes_watch_support/harness_routing.py`
- Added `route_harness_probe_feedback(repo_root)`
- Added CLI mode: `--route-harness-probe-feedback`
- Routing handoff writes:
  - probe routing/handoff JSON
  - probe routing/handoff markdown artifact
- Output location:
  - `fuzz-records/probe-routing/`
- The routing path also reuses existing refiner orchestration/dispatch bundle generation

## Current routing behavior
This is intentionally conservative and action-code driven:
- `shift_weight_to_deeper_harness` -> `promote-next-depth`
- `halt_and_review_harness` -> `review-current-candidate`
- `minimize_and_reseed` -> `reseed-before-retry`
- unknown actions -> `observe-and-hold`

After choosing the route, the system immediately:
- prepares the next refiner orchestration bundle
- prepares the next refiner dispatch bundle
- records a handoff artifact that points at those paths

## Important limitation
This is not yet a full candidate scheduler.
It does not yet:
- maintain a scored ranked candidate pool with promotions/demotions
- auto-launch the bridge/verification stages after dispatch readiness
- distinguish nuanced pass/fail patterns beyond the coarse feedback action code
- rewrite target profiles or adapter weights directly from routing evidence

## Why this matters
This is the first point where probe feedback becomes both:
- a routing decision for the current candidate
- a concrete orchestration handoff for the next refinement stage

That pushes the system closer to a real semi-autonomous improvement loop instead of a collection of adjacent artifacts.

## Recommended next step after this
- promote/demote multiple candidate entries based on routing outcomes instead of only queuing one refinement action
- then connect routing outputs into bridge launch / verification policy so the handoff can continue through the existing lifecycle automatically
