# Hermes Watch Target Profile Schema Validation Checklist

- [x] Inspect current target profile loader/summary path and define validation boundary
- [x] Add failing tests for valid/warning/fatal validation states
- [x] Add failing tests for main-path warning/fatal persistence in status/report
- [x] Add `validate_target_profile(...)`
- [x] Add warning/fatal split for schema-level issues
- [x] Treat loader degradation as fatal validation
- [x] Flag missing `schema_version` as warning
- [x] Flag unsupported `schema_version` as fatal
- [x] Flag missing `target.current_campaign.primary_mode` as fatal
- [x] Flag empty `stages` as fatal
- [x] Flag missing `meta.name` as warning
- [x] Add runtime profile gating (`runtime_target_profile`) so fatal profiles do not drive semantic logic
- [x] Persist validation status/severity/codes into status snapshots
- [x] Persist validation status/severity/codes into `FUZZING_REPORT.md`
- [ ] Add full semantic schema validation for hotspot/stage/trigger substructures
- [ ] Add explicit quarantine/backup for fatally invalid profiles
- [ ] Add registry/history for repeated warning/fatal profile loads
