# Hermes Watch Upgrade Note — Profile Extraction and Minimal Target Adapter

Date: 2026-04-15

## Why this step
The watcher had accumulated enough profile loading/validation logic that continuing to add autonomy directly into `scripts/hermes_watch.py` would increase monolith pressure and make multi-target evolution harder. The next structural step was to extract the target profile subsystem and introduce a minimal target adapter contract while preserving current OpenHTJ2K behavior.

## What changed
- Extracted profile loading into `scripts/hermes_watch_support/profile_loading.py`
- Extracted profile validation into `scripts/hermes_watch_support/profile_validation.py`
- Extracted profile summary building into `scripts/hermes_watch_support/profile_summary.py`
- Added `scripts/hermes_watch_support/target_adapter.py`
- Added minimal `TargetAdapter` dataclass and `get_target_adapter(...)`
- Kept OpenHTJ2K as the default adapter implementation
- Switched watcher build/smoke/fuzz commands to adapter-driven commands
- Switched report target string and notification label generation to adapter-driven values
- Added tests proving the watcher can use a custom adapter in the build-failed path

## What did NOT change
- No real multi-target selection logic yet beyond default OpenHTJ2K fallback
- No automatic target reconnaissance yet
- No harness generation/refinement loop yet
- No refiner pipeline extraction yet

## Why this matters for the long-term goal
This creates the first real seam between:
1. generic control-plane behavior
2. target-specific runtime behavior

That seam is required before the system can realistically evolve into:
- new target in
- target analysis
- harness candidate generation
- fuzzing + crash feedback
- harness revision
- repeated iteration toward meaningful crashes

## Risks / debt still present
- `hermes_watch.py` is still large; extraction only started
- Adapter selection is still effectively single-target
- Validation and adapter logic are improved, but full multi-target autonomy is still upstream of adapter E2E coverage and reconnaissance modules

## Recommended next step after this
- Add adapter E2E tests
- Expand adapter contract slightly only where current watcher still hardcodes target assumptions
- Then start target reconnaissance/profile-draft generation on top of the adapter/profile substrate
