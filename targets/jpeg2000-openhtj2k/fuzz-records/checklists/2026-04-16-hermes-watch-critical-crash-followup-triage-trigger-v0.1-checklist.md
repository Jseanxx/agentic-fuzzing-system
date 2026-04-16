# Hermes Watch Critical Crash Follow-up Triage Trigger v0.1 Checklist

- [x] fresh fuzz-artifacts/current-status inspected
- [x] highest-leverage gap selected: critical crash policy existed but follow-up triage trigger did not
- [x] failing tests added first
  - [x] `continue_and_prioritize_triage` should trigger follow-up
  - [x] triage command should skip when already in triage mode
  - [x] critical crash policy action should record and auto-run triage trigger
- [x] production code changed minimally in `scripts/hermes_watch.py`
- [x] follow-up command selection split into triage vs regression
- [x] executor skip logic generalized from regression-only to target-mode-aware
- [x] targeted tests passed
- [x] `pytest -q tests/test_hermes_watch.py` passed
- [x] full `pytest -q` passed
- [x] bounded watcher rerun executed for live evidence
- [x] note/checklist/current-status/progress-index updated
- [ ] live artifact with non-duplicate `continue_and_prioritize_triage` or `high_priority_alert` path captured in repo state
