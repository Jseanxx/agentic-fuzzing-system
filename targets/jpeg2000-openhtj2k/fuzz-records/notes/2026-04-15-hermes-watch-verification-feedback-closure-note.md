# R14 Verification-Policy Feedback Closure Note

## Summary
R14 closes the loop from verification policy back into the ranked harness candidate registry.

## Added behavior
- `apply_verification_failure_policy(...)` now calls candidate-registry closure logic.
- Retry decisions update candidate verification retry debt.
- Escalation decisions update candidate escalation/review debt.
- Candidate score/status are adjusted conservatively and the ranked registry is re-ranked.
- `ranked-candidates.md` is refreshed so the closure remains human-readable.
- Policy result payload now reports whether candidate registry closure ran and where the refreshed registry artifacts live.

## Current debt model in this step
- `candidate-seed-debt` retry:
  - `verification_retry_debt += 1`
  - `seed_debt_count += 1`
  - `status = seed_debt`
  - score penalty applied
- escalation:
  - `verification_escalation_count += 1`
  - `review_debt_count += 1`
  - `status = review_required`
  - score penalty applied

## Caveat
This is still coarse debt accounting. It improves closed-loop state propagation, but it is not yet a rich scheduler with build/smoke/stability/history-aware policy weighting.
