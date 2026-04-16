# R16 Registry-First Scheduler Refinement + History-Aware Queue Weighting

## Summary
R16 upgrades the refiner pipeline from registry-order execution to registry-first weighted selection across the queue lifecycle.

## Added behavior
- shared registry selector now ranks entries across all refiner registries
- queue weighting considers:
  - action-specific base weight
  - ranked candidate effective score
  - candidate status bonuses
  - recent run-history signals (shallow crash dominance / timeout pressure)
- queue metadata written back into entries:
  - `queue_weight`
  - `queue_reasons`
  - `queue_rank`
  - `selected_effective_score`

## Scheduler stages now using weighted cross-registry selection
- executor selection
- prepared dispatch selection
- ready bridge selection
- armed launch selection
- verifiable selection

## Current history-aware heuristics
- repeated shallow-crash dominance boosts deeper-harness and review work
- timeout-heavy recent history boosts slow-lane work
- candidate effective score and debt-aware status still contribute directly

## Caveat
This is still heuristic scheduling, not measured optimization. It is a stronger scheduler substrate, but it is not yet coverage-aware or crash-novelty-aware planning.
