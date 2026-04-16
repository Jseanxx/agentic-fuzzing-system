# R17 Target Intelligence Enrichment + Viability-Aware Candidate Weighting

## Summary
R17 pushes target intelligence slightly closer to the candidate layer by turning recon-derived candidates into viability-scored candidates and carrying that signal into evaluation, registry bootstrap, and refiner queue weighting.

## Added target-intelligence fields
Per harness candidate draft:
- `callable_signal`
- `build_viability`
- `smoke_viability`
- `viability_score`

## Current conservative heuristics
- callable signal inferred from entrypoint/path naming
- build viability inferred from known build system + entrypoint presence
- smoke viability inferred from smoke helper presence + baseline seed availability
- viability score aggregates callable/build/smoke/readiness heuristics

## Where the signal now flows
- harness candidate draft
- harness evaluation ranking
- ranked candidate registry bootstrap
- refiner queue weighting

## Why this matters
This is still heuristic, but it moves the system one step away from pure control-plane bookkeeping and one step toward deciding based on target-side viability.

## Caveat
This is not yet deep target understanding. It is filename/repo-state viability inference, not symbol-graph/API-level harness intelligence.
