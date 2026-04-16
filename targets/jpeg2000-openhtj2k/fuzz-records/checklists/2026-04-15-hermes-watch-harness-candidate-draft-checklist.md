# Hermes Watch Harness Candidate Draft Checklist

- [x] Inspect reconnaissance artifact flow and define harness-draft insertion point
- [x] Add failing tests for harness candidate draft generation
- [x] Add failing tests for harness draft artifact emission
- [x] Add failing tests for low-risk CLI mode (`--draft-harness-plan`)
- [x] Create `scripts/hermes_watch_support/harness_draft.py`
- [x] Generate conservative harness candidates from entrypoint/stage heuristics
- [x] Emit harness draft manifest JSON
- [x] Emit harness draft markdown plan artifact
- [x] Auto-chain from target profile auto-draft to harness draft generation
- [x] Add artifact-only CLI path for harness draft generation
- [ ] Add code-aware harness skeleton generation
- [ ] Add buildable smoke harness stub generation under review gate
- [ ] Add candidate scoring from real build/smoke probes instead of pure heuristics
