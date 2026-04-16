# Hermes Watch Harness Probe Feedback Bridge Checklist

- [x] Inspect short-probe artifact flow and define feedback-bridge insertion point
- [x] Add failing tests for feedback bridge from failed smoke probe
- [x] Add failing tests for feedback bridge from passed probe
- [x] Add failing tests for low-risk CLI mode (`--bridge-harness-probe-feedback`)
- [x] Create `scripts/hermes_watch_support/harness_feedback.py`
- [x] Load the latest harness probe manifest conservatively
- [x] Map probe outcomes to existing refinement buckets/actions
- [x] Record feedback into existing refinement registries under `fuzz-artifacts/automation/`
- [x] Emit probe feedback JSON artifact
- [x] Emit probe feedback markdown artifact
- [x] Wire feedback-bridge CLI path into watcher
- [ ] Add richer outcome mapping for skipped-smoke subcases and ambiguous build states
- [ ] Join feedback bridge with verification/retry lifecycle instead of queue-only insertion
- [ ] Auto-chain feedback output into the next refiner orchestration stage
