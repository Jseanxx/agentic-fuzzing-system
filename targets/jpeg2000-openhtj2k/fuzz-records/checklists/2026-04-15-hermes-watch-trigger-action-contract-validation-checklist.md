# Hermes Watch Trigger/Action Contract Validation Checklist

- [x] Inspect existing trigger and action shapes from target profile
- [x] Add failing tests for trigger-condition field validation
- [x] Add failing tests for action contract validation
- [x] Validate known action types against allowed enum
- [x] Validate `requires_human_review` is boolean
- [x] Validate action `outputs` is a non-empty string list
- [x] Validate `coverage_plateau` condition field types
- [x] Validate `shallow_crash_dominance` condition field types
- [x] Validate `timeout_surge` condition field types
- [x] Validate `corpus_bloat_low_gain` condition field types
- [x] Validate `stability_drop` condition field types
- [x] Validate `deep_write_crash` condition field types
- [x] Validate `deep_signal_emergence` condition field types
- [x] Keep broken trigger/action contracts as fatal validation issues
- [ ] Add per-action output name whitelist validation
- [ ] Add per-trigger numeric range validation (e.g. percentages, ratios > 0)
- [ ] Split validator into dedicated module after stabilization phase
