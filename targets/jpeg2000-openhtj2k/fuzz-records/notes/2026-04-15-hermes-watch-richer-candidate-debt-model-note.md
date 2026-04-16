# R15 Richer Candidate Debt Model + Debt-Aware Scheduler Weighting

## Summary
R15 upgrades candidate state from coarse single-status handling into a richer debt-aware substrate and uses that substrate during next-candidate selection.

## Added candidate-state fields
- `seed_debt_count`
- `review_debt_count`
- `build_debt_count`
- `smoke_debt_count`
- `instability_debt_count`
- `verification_retry_debt`
- `verification_escalation_count`
- `pass_streak`
- `fail_streak`
- `debt_penalty`
- `effective_score`

## Registry update behavior
- probe feedback now increments debt buckets based on action + bridge reason
- failed smoke review increments smoke debt and fail streak
- passed deeper-shift feedback increments pass streak and resets fail streak
- registry markdown now exposes debt and effective score for human review

## Scheduler behavior
- `select_next_ranked_candidate(...)` now ranks eligible candidates by effective score, not raw score alone
- debt-heavy candidates can be skipped even when their raw score is higher
- `review-current-candidate` route is still preserved as an explicit override

## Verification closure behavior
- verification retry/escalation updates now also refresh debt penalty/effective score
- closure still remains conservative and artifact-first

## Caveat
This is still a heuristic debt model. It is better than raw-score-only scheduling, but it is not yet target-smart or coverage-aware scheduling.
