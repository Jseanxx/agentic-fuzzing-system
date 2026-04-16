# Hermes Watch Registry-First Scheduler Checklist

- [x] Inspect ranked candidate registry and current routing/handoff path
- [x] Add failing tests for registry-top selection during promote-next-depth handoff
- [x] Add failing tests for preserving current candidate on review-current-candidate route
- [x] Add failing tests for CLI path exposing selected candidate metadata in handoff artifacts
- [x] Extend `scripts/hermes_watch_support/harness_routing.py` with registry-first candidate selection
- [x] Expose `select_next_ranked_candidate(repo_root)` through watcher wrapper
- [x] Inject selected candidate metadata into refinement registry entries before orchestration prep
- [x] Ensure routing/handoff artifacts include selected candidate metadata
- [x] Run targeted and full regression suite
- [ ] Make orchestration queue ordering candidate-aware instead of action-only search order
- [ ] Feed selected candidate metadata into bridge launch / verification prompts
- [ ] Replace coarse status exclusion with richer debt-aware scheduler policy
