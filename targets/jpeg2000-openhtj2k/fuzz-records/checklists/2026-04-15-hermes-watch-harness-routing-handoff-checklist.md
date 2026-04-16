# Hermes Watch Harness Routing + Handoff Checklist

- [x] Inspect probe-feedback artifacts and existing refiner orchestration hooks
- [x] Add failing tests for passed-probe routing into mode refinement handoff
- [x] Add failing tests for failed-probe routing into harness review handoff
- [x] Add failing tests for low-risk CLI mode (`--route-harness-probe-feedback`)
- [x] Create `scripts/hermes_watch_support/harness_routing.py`
- [x] Load latest probe feedback manifest conservatively
- [x] Map feedback action codes to candidate routing labels
- [x] Reuse existing refiner orchestration + dispatch bundle generation for handoff
- [x] Emit probe routing handoff JSON artifact
- [x] Emit probe routing handoff markdown artifact
- [x] Wire routing/handoff CLI path into watcher
- [ ] Distinguish deeper pass/fail patterns beyond coarse action-code mapping
- [ ] Route directly into bridge/launch phases when policy allows
- [ ] Use routing output to demote/promote ranked candidate lists instead of single-entry queues only
