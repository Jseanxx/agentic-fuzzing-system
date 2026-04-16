# Hermes Watch Notification Hardening Checklist

- [x] Investigate current `send_discord()` failure behavior and call sites
- [x] Add failing tests for best-effort notification handling
- [x] Add `send_discord_best_effort(...)` wrapper that catches exceptions
- [x] Make raw `send_discord(...)` return structured status metadata (`sent` / `skipped`)
- [x] Ensure build-failed path treats notification failure as non-critical
- [x] Ensure smoke-failed path treats notification failure as non-critical
- [x] Persist notification status/error metadata into status snapshots
- [x] Persist notification metadata into `FUZZING_REPORT.md`
- [x] Route progress notifications through best-effort wrapper
- [x] Route final summary notifications through best-effort wrapper
- [ ] Quarantine/retry/backoff for repeated notification failures
- [ ] Dedicated notification failure registry/history
- [ ] File locking / concurrency-safe notification state writes
