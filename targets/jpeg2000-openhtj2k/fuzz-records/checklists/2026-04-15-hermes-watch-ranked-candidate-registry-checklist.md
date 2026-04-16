# Hermes Watch Ranked Candidate Registry Checklist

- [x] Inspect current probe-feedback/routing artifacts and identify a stable candidate-registry insertion point
- [x] Add failing tests for promotion on passed probe feedback
- [x] Add failing tests for demotion on failed probe feedback
- [x] Add failing tests for low-risk CLI mode (`--update-ranked-candidate-registry`)
- [x] Create `scripts/hermes_watch_support/harness_candidates.py`
- [x] Bootstrap ranked candidates from latest harness draft when registry is absent
- [x] Apply feedback-driven promotion/demotion state updates to candidate entries
- [x] Re-rank candidates after score changes
- [x] Emit ranked candidate registry JSON
- [x] Emit ranked candidate registry markdown artifact
- [x] Wire ranked candidate registry update path into watcher
- [ ] Add multi-signal scoring instead of simple fixed step promotion/demotion
- [ ] Track separate seed debt / smoke debt / review debt dimensions per candidate
- [ ] Drive next-candidate selection directly from this registry in routing/orchestration paths
