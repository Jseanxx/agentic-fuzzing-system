# Hermes Watch Leak State Rehydration v0.1 Checklist

- [x] latest stale leak canonical state mismatch confirmed (`current_status.json`, `run_history.json`, `crash_index.json`)
- [x] failing regression test added for stale leak rehydration without history duplication
- [x] failing regression test added for CLI repair path exit success
- [x] existing run `fuzz.log` reparsing path verified
- [x] stale crash fingerprint record replaced with canonical leak fingerprint
- [x] latest run `status.json` repaired
- [x] `fuzz-artifacts/current_status.json` repaired
- [x] `fuzz-artifacts/automation/run_history.json` repaired in-place
- [x] `fuzz-artifacts/crash_index.json` repaired in-place
- [x] backward-compatible repair CLI alias kept
- [x] `python -m py_compile scripts/hermes_watch.py tests/test_hermes_watch.py`
- [x] `python -m pytest tests/test_hermes_watch.py::HermesWatchFingerprintTests tests/test_hermes_watch.py::HermesWatchAutonomousSupervisorTests -q`
- [x] `python -m pytest tests/test_hermes_watch.py -q`
- [x] `python -m pytest tests -q`
- [x] real repo latest run rehydrated via CLI
- [ ] `FUZZING_REPORT.md` stale wording rewrite/backfill
- [ ] bounded rerun confirms naturally regenerated report/state stay leak-aware
