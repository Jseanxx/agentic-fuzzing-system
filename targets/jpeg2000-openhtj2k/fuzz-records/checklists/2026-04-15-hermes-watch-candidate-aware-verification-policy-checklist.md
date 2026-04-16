# Hermes Watch Candidate-Aware Verification Policy Checklist

- [x] Inspect verification/retry policy paths for missing candidate-aware inputs
- [x] Add failing tests for retry policy returning selected candidate metadata
- [x] Add failing tests for review-required candidate escalation
- [x] Add failing tests for retry/escalation artifacts including candidate metadata
- [x] Extend `decide_verification_policy(entry)` with candidate-aware escalation/retry logic
- [x] Extend verification retry artifact with selected candidate metadata
- [x] Extend verification escalation artifact with selected candidate metadata
- [x] Extend policy return payload with selected candidate metadata
- [x] Run targeted and full regression suite
- [ ] Make retry/escalation logic use richer candidate debt dimensions than coarse status strings
- [ ] Feed candidate-aware policy output back into ranked registry updates automatically
- [ ] Let verification policy alter scheduling priority or bridge launch timing per candidate
