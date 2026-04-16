# Hermes Watch Harness Short Probe Checklist

- [x] Inspect evaluation-draft artifact flow and define short-probe insertion point
- [x] Add failing tests for harness probe draft generation
- [x] Add failing tests for short probe execution path
- [x] Add failing tests for low-risk CLI mode (`--run-short-harness-probe`)
- [x] Create `scripts/hermes_watch_support/harness_probe.py`
- [x] Infer a single top candidate from the evaluation artifact
- [x] Generate conservative build probe commands from detected build systems
- [x] Infer a single baseline seed candidate from common seed/corpus directories
- [x] Detect low-risk smoke helper script (`scripts/run-smoke.sh` or `run-smoke.sh`)
- [x] Execute build probe first and fail-fast before smoke probe
- [x] Emit probe manifest JSON
- [x] Emit probe markdown artifact with probe result summary
- [x] Wire short-probe CLI path into watcher
- [ ] Add timeout-enforced subprocess execution instead of relying on ambient runner behavior
- [ ] Add richer smoke command inference beyond helper-script detection
- [ ] Feed failed probe outcomes back into adapter/profile refinement automatically
