# Hermes Watch Target Reconnaissance Draft Checklist

- [x] Inspect where reconnaissance can plug into the current profile/adapter substrate
- [x] Add failing tests for reconnaissance summary generation
- [x] Add failing tests for draft artifact emission
- [x] Add failing tests for low-risk CLI path (`--draft-target-profile`)
- [x] Create `scripts/hermes_watch_support/reconnaissance.py`
- [x] Implement conservative build system detection
- [x] Implement source file sampling and stage candidate inference
- [x] Implement entrypoint candidate inference from filenames
- [x] Implement target profile auto-draft YAML renderer
- [x] Emit recon manifest JSON + draft profile YAML under `fuzz-records/profiles/auto-drafts/`
- [x] Wire low-risk artifact-only CLI path into watcher
- [ ] Improve reconnaissance beyond filename heuristics (AST/symbol/build graph level)
- [ ] Infer harness entrypoints from actual exported APIs / binaries
- [ ] Attach confidence scores per inferred stage/entrypoint
