# Hermes Watch Harness Evaluation Draft Checklist

- [x] Inspect harness draft artifact flow and define evaluation-draft insertion point
- [x] Add failing tests for top-candidate evaluation draft generation
- [x] Add failing tests for evaluation artifact emission
- [x] Add failing tests for low-risk CLI mode (`--draft-harness-evaluation`)
- [x] Create `scripts/hermes_watch_support/harness_evaluation.py`
- [x] Rank/select top harness candidates conservatively
- [x] Emit expected success signal + fail-fast criteria per candidate
- [x] Emit low-risk execution plan steps per candidate
- [x] Emit evaluation manifest JSON
- [x] Emit evaluation markdown plan artifact
- [x] Auto-chain from harness draft generation into evaluation draft generation
- [x] Add artifact-only CLI path for harness evaluation generation
- [ ] Add scoring informed by real build/smoke probes instead of heuristic-only ranking
- [ ] Attach confidence/uncertainty metadata to each execution assumption
- [ ] Feed evaluation outcomes back into profile/adapter refinement automatically
