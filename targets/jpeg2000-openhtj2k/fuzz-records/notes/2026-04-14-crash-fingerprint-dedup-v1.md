# Crash Fingerprint / Dedup v1 Note — 2026-04-14

## What was added
`hermes_watch.py` now computes a crash signature and updates a shared crash index.

## Signature fields
- `kind`
  - example: `ubsan`, `asan`, `leak`, `libfuzzer`, `timeout`
- `location`
  - first matched source location, normalized as `basename:line`
- `summary`
  - normalized sanitizer summary text
- `artifact_path`
- `artifact_sha1`
- `fingerprint`
  - format: `kind|location|summary`

## Shared index
- path: `fuzz-artifacts/crash_index.json`

Stored fields per fingerprint:
- `first_seen_run`
- `last_seen_run`
- `occurrence_count`
- `artifacts`
- `kind`
- `location`
- `summary`
- `artifact_sha1`

## Verified behavior
- same triage crash reproduced twice
- second run marked as duplicate
- `current_status.json` now includes:
  - `crash_fingerprint`
  - `crash_kind`
  - `crash_location`
  - `crash_summary`
  - `crash_artifact`
  - `crash_artifact_sha1`
  - `crash_is_duplicate`
  - `crash_occurrence_count`
  - `crash_first_seen_run`
- `FUZZING_REPORT.md` now includes a `Crash Fingerprint` section

## Known limits of v1
- fingerprint is stack/summary based, not a full semantic root-cause classifier
- dedup is exact-string based after normalization; similar bugs with different summary text may split into separate fingerprints
- no artifact minimization or cross-host/global dedup yet
- no automatic policy action yet beyond recording duplicate state
