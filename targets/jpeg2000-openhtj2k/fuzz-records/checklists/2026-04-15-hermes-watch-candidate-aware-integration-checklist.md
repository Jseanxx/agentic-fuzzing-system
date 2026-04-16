# Hermes Watch Candidate-Aware Prompt/Bridge/Verification Checklist

- [x] Inspect prompt builders, dispatch bundles, and verification outputs for missing candidate metadata
- [x] Add failing tests for delegate request context including selected candidate metadata
- [x] Add failing tests for cron prompt/request including selected candidate metadata
- [x] Add failing tests for verification output preserving selected candidate metadata
- [x] Extend refiner subagent prompt with selected candidate context
- [x] Extend refiner cron prompt with selected candidate context
- [x] Extend delegate dispatch request context with selected candidate context
- [x] Extend cronjob request payload/prompt with selected candidate context
- [x] Extend verification result return payload with selected candidate metadata
- [x] Run targeted and full regression suite
- [ ] Push selected candidate metadata deeper into bridge script prompts/log summaries
- [ ] Use selected candidate metadata inside verification policy decisions
- [ ] Align downstream execution prompts with candidate debt/state from ranked registry
