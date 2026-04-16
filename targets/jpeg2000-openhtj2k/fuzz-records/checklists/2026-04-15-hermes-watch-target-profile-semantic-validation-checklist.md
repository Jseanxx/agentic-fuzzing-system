# Hermes Watch Target Profile Semantic Validation Checklist

- [x] Inspect profile schema usage for stage/hotspot/trigger/telemetry consistency
- [x] Add failing tests for hotspot stage reference consistency
- [x] Add failing tests for trigger action consistency
- [x] Add failing tests for telemetry stage counter / stage_file_map consistency
- [x] Add failing tests for stage depth rank uniqueness
- [x] Extend `validate_target_profile(...)` with semantic stage checks
- [x] Extend `validate_target_profile(...)` with hotspot reference checks
- [x] Extend `validate_target_profile(...)` with trigger/action reference checks
- [x] Extend `validate_target_profile(...)` with telemetry consistency checks
- [x] Keep warning/fatal split (`unknown-stage-counter-name` warning; broken refs fatal)
- [x] Preserve validation output in summary/status/report via existing validation plumbing
- [ ] Add action/output contract validation
- [ ] Add trigger-condition field-level validation per trigger type
- [ ] Add hotspot file/function severity enum validation
- [ ] Split validation code into dedicated module once stabilization phase ends
