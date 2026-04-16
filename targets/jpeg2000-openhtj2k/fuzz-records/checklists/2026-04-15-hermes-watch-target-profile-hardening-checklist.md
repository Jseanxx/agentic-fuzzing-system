# Hermes Watch Target Profile Loader Hardening Checklist

- [x] Inspect current `load_target_profile()` failure behavior and main-path coupling
- [x] Add failing tests for malformed YAML fallback
- [x] Add failing tests for wrong top-level YAML type fallback
- [x] Add failing tests for invalid section-shape repair
- [x] Harden `load_target_profile()` to return degraded mapping instead of raising on parse/type failures
- [x] Normalize known profile sections (`meta`, `target`, `current_campaign`, `stages`, `hotspots`, `telemetry`, `triggers`)
- [x] Mark degraded loads with structured error metadata (`__load_error__`, detail)
- [x] Extend target profile summary with `load_status` / `load_error`
- [x] Persist target profile load status/error into status snapshots
- [x] Persist target profile load status/error into `FUZZING_REPORT.md`
- [x] Verify `main()` treats malformed target profile as non-critical during build-failed path
- [ ] Add explicit quarantine/backup of malformed profile files
- [ ] Add schema-version validation beyond shape repair
- [ ] Add profile warning registry/history for repeated degraded loads
