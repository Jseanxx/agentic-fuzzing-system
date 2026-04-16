# AFL++ overnight switch status

Date: 2026-04-15
Purpose: overnight defensive fuzzing focused on high-value memory-safety crashes

## What changed

### New AFL++ scripts
- `scripts/build-aflpp.sh`
- `scripts/run-aflpp-mode.sh`

### New AFL++ seed buckets
- `fuzz/corpus-afl/parse/`
- `fuzz/corpus-afl/cleanup/`
- `fuzz/corpus-afl/decode/`

### Sanitizer stance for AFL++ overnight
- primary: ASAN
- rationale: prioritize dangerous memory-safety crash classes over broader but noisier instrumentation
- AFL++ compatibility adjustment:
  - `ASAN_OPTIONS` uses `symbolize=0`

## Harness choice

### Primary overnight target
- `open_htj2k_parse_memory_harness`

Why:
- parser-side memory bug signal is strong
- fast target compared to full decode lifecycle
- quick AFL++ dry run already produced many crash artifacts
- suitable for first overnight campaign on Proxmox

### Secondary target (not primary overnight right now)
- `open_htj2k_cleanup_memory_harness`

Why not primary first:
- meaningful, but current signal-to-speed ratio looks lower than parser harness
- better as follow-up or secondary comparative campaign

## Short AFL++ validation result

Remote host: `proxmox-js`
User: `js`

Short parse AFL++ run:
- completed under timeout validation
- AFL++ forkserver initialized correctly
- parse corpus loaded
- 30-second validation already reported many crashes saved

This is enough evidence to justify an overnight parse-focused AFL++ run.

## Current overnight job

Remote command shape:
- `timeout 8h bash scripts/run-aflpp-mode.sh parse`

Execution state at handoff:
- launched in background via SSH to `proxmox-js`
- intended to keep running until timeout or manual stop

## Caution

High crash count in AFL++ does not mean high unique finding count.
Morning triage must focus on:
- deduplication
- crash type classification
- file/line/function
- whether findings are distinct parser-side memory-safety issues
