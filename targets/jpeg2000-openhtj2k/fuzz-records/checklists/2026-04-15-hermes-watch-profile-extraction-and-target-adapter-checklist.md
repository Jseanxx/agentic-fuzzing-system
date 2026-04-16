# Hermes Watch Profile Extraction + Minimal Target Adapter Checklist

- [x] Inspect extraction boundaries for target profile subsystem and hardcoded target assumptions
- [x] Add failing tests for minimal target adapter behavior
- [x] Create `scripts/hermes_watch_support/profile_loading.py`
- [x] Create `scripts/hermes_watch_support/profile_validation.py`
- [x] Create `scripts/hermes_watch_support/profile_summary.py`
- [x] Create `scripts/hermes_watch_support/target_adapter.py`
- [x] Add package glue under `scripts/hermes_watch_support/__init__.py`
- [x] Add `scripts/__init__.py` so support modules import cleanly from tests and CLI
- [x] Replace inline profile logic in `hermes_watch.py` with extracted wrappers/import-backed calls
- [x] Introduce minimal `TargetAdapter` contract with OpenHTJ2K default implementation
- [x] Route build/smoke/fuzz commands through adapter
- [x] Route report target + notification labels through adapter
- [x] Keep behavior compatible for current OpenHTJ2K default path
- [ ] Split refiner/orchestration concerns into dedicated modules
- [ ] Add true multi-target adapter selection beyond OpenHTJ2K fallback
- [ ] Add adapter E2E tests for smoke-success/final-summary paths
