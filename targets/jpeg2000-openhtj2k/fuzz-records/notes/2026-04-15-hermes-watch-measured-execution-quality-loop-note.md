# R18 Measured Execution Quality Loop + Evidence-Aware Registry Weighting

## Summary
R18 upgrades the candidate registry from viability-only and debt-only weighting to a measured execution loop that credits or penalizes candidates using observed probe/verification outcomes.

## Added measured-execution fields
- `probe_pass_count`
- `probe_fail_count`
- `build_pass_count`
- `build_fail_count`
- `smoke_pass_count`
- `smoke_fail_count`
- `verification_verified_count`
- `verification_unverified_count`
- `execution_evidence_score`

## What now updates evidence
- probe feedback bridge via registry update
- verification-policy closure via candidate-registry closure

## Effective score formula in this step
- effective score = raw score + execution evidence score - debt penalty

## Queue weighting impact
- refiner queue weighting now rewards candidates with positive measured execution evidence
- viability and debt still matter, but measured evidence can now push a candidate upward or downward

## Caveat
This is still a conservative evidence model built from pass/fail counters, not coverage deltas or crash-family novelty yet.
