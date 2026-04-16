# Hermes Watch Registry-Driven Next Candidate Selection Checklist

- [x] Inspect current ranked candidate registry and routing/handoff integration points
- [x] Add failing tests for using ranked top candidate in promote-next-depth handoff
- [x] Add failing tests for preserving current candidate on review-current-candidate route
- [x] Add failing tests for CLI path continuing through registry-driven route output
- [x] Extend `scripts/hermes_watch_support/harness_routing.py` with ranked-candidate selection
- [x] Surface selected candidate metadata in routing decisions and handoff artifacts
- [x] Inject selected candidate metadata into queued refinement entries before orchestration prep
- [x] Expose `select_next_ranked_candidate(repo_root)` through watcher wrapper
- [x] Verify routing/handoff now consumes registry state instead of feedback-only candidate identity
- [x] Run targeted and full regression suite
- [ ] Replace coarse action-code mapping with richer multi-signal selection policy
- [ ] Feed selected candidate metadata into downstream bridge/verification execution prompts
- [ ] Make orchestration queue selection itself candidate-aware instead of action-only queue order
