# Artifact Classification v1 — 2026-04-14

## What was added
watcher now classifies outcomes into a clearer artifact/event category.

## Categories currently recognized
- `crash`
- `leak`
- `timeout`
- `no-progress`
- `build-failed`
- `smoke-failed`
- `fuzzer-exit`

## Classification rules (v1)
### crash
- sanitizer crash signatures such as `ubsan`, `asan`, `libfuzzer`
- reason: `sanitizer-crash`

### leak
- crash signature kind is `leak`
- reason: `sanitizer-leak`

### timeout
- watcher timeout outcome or timeout-like crash kind
- reason: `watcher-timeout` or `sanitizer-timeout`

### no-progress
- watcher stopped because coverage/corpus progress stalled
- reason: `stalled-coverage-or-corpus`

### build-failed
- build stage failed
- reason: `build-or-config-error`

### smoke-failed
- smoke stage failed on baseline inputs
- reason: `baseline-input-failed`

### fuzzer-exit
- nonzero exit without a clearer signature
- reason: `nonzero-exit-without-clear-signature`

## Where it appears
- `fuzz-artifacts/current_status.json`
- per-run `status.json`
- per-run `FUZZING_REPORT.md`
- Discord summary text (when configured)

## Verified now
- triage UBSan repro is classified as:
  - `artifact_category: crash`
  - `artifact_reason: sanitizer-crash`

## Limits
- this is still rule-based, not semantic
- mixed-signal runs may still need smarter prioritization in later versions
