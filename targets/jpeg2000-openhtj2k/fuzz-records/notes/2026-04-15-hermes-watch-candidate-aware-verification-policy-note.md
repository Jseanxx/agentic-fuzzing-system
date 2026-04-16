# Hermes Watch Upgrade Note — Candidate-Aware Verification Policy and Retry/Escalation Integration

Date: 2026-04-15

## Why this step
The system could already carry selected candidate metadata through routing, prompts, dispatch, and verification output, but verification policy decisions still ignored that candidate context. This step makes retry/escalation policy candidate-aware and includes candidate metadata in retry/escalation artifacts.

## What changed
- Extended `decide_verification_policy(entry)` in `scripts/hermes_watch.py`
- Candidate-aware rules now include:
  - `review_required` candidate -> escalate immediately
  - `seed_debt` candidate -> retry with candidate-seed-debt reason
- Verification retry/escalation artifacts now include:
  - `selected_candidate_id`
  - `selected_entrypoint_path`
  - `selected_candidate_status`
- `apply_verification_failure_policy(...)` now returns selected candidate metadata in its result payload

## Current behavior
This is still conservative and status-driven:
- exhausted retries still escalate
- delegate shape/quality gaps still escalate
- `review_required` candidates escalate immediately
- `seed_debt` candidates retry
- other missing-evidence cases still default to retry

## Why this matters
This is the first point where candidate state affects retry/escalation policy instead of just selection and prompting. That improves loop coherence: the system is not only candidate-aware upstream, it now starts to behave differently downstream based on candidate state.

## Important limitation
This is not yet a rich candidate-aware scheduler policy.
It does not yet:
- use repeated candidate-specific outcome history
- distinguish build debt vs smoke debt vs seed debt separately beyond a simple status field
- automatically feed retry/escalation outcomes back into the ranked registry
- tune schedule timing or dispatch priority per candidate

## Recommended next step
- make ranked candidate registry consume verification policy outcomes directly
- then introduce richer debt/state dimensions so retry/escalation decisions are based on more than a single coarse candidate status
