# Hermes Watch Upgrade Note — Ranked Candidate Registry and Feedback-Based Promotion/Demotion

Date: 2026-04-15

## Why this step
The system could already route probe feedback into refiner handoff artifacts, but candidate state itself was still implicit. This step adds an explicit ranked candidate registry so probe outcomes can promote or demote candidates instead of only queuing refinement actions.

## What changed
- Added `scripts/hermes_watch_support/harness_candidates.py`
- Added `update_ranked_candidate_registry(repo_root)`
- Added CLI mode: `--update-ranked-candidate-registry`
- Registry update writes:
  - ranked candidate registry JSON
  - ranked candidate registry markdown artifact
- Output location:
  - `fuzz-records/harness-candidates/`

## Current registry behavior
This is intentionally conservative and score-step driven:
- bootstrap from the latest harness draft when no registry exists
- passed probe feedback (`shift_weight_to_deeper_harness`) -> +15 and `promoted`
- failed review feedback (`halt_and_review_harness`) -> -15 and `review_required`
- reseed feedback (`minimize_and_reseed`) -> -5 and `seed_debt`
- re-rank candidates by score after each update

## Important limitation
This is not yet a full candidate scheduler.
It does not yet:
- track multiple debt dimensions separately (seed/smoke/review/build)
- use richer evidence from build/smoke details instead of coarse feedback action codes
- update routing/orchestration paths to always pick the top ranked candidate automatically
- maintain historical score traces or confidence intervals

## Why this matters
This is the first time candidate state is explicit and durable across the new semi-autonomous loop:
- probe outcome updates feedback
- feedback updates ranked candidate state
- ranked state can now become the substrate for future candidate selection

That is a necessary step before safe harness skeleton generation or broader automatic iteration.

## Recommended next step after this
- route and orchestration should consume this ranked registry directly for next-candidate selection
- then add richer promotion/demotion rules using separate build/smoke/seed debt signals instead of a single coarse score delta
