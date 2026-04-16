# WSL fuzzing system status — v2.3

Date: 2026-04-15
Commit: `1d5b676`
Scope: `OpenHTJ2K` / `fuzzing-jpeg2000`

## Version label

Current cold label: **policy-driven semi-automated fuzzing operations system v2.3**

This label is intentionally conservative.
It does **not** mean self-improving autonomous bug-fixing fuzzing.
It means the local WSL system can:

- build / smoke / fuzz
- classify outcomes
- fingerprint and deduplicate crashes
- recommend policy actions
- auto-record known-bad and regression candidates
- auto-trigger and auto-run regression
- sync registry state into real corpus buckets
- deduplicate regression triggers and maintain a simple priority queue

## Newly completed after v2.0-era notes

### 1. Regression auto-run v1
- regression trigger is no longer record-only
- watcher can immediately execute a regression run after trigger creation
- recursion guard added:
  - if already in `regression` mode
  - auto-run is skipped with `skipped-already-in-regression`

### 2. Registry-to-corpus sync v1
- `known_bad.json` -> `fuzz/corpus/known-bad/`
- `regression_candidates.json` -> `fuzz/corpus/regression/`
- copy-based sync, not destructive move
- `bucket_path` recorded in registry
- old placeholder-style `seed_path` values can be repaired from `smoke.log`

### 3. Regression trigger dedup + priority queue v1
- trigger dedup key exists
- same regression seed can collapse into a single queue item
- queue metadata exists:
  - `priority`
  - `queue_rank`
  - `occurrence_count`
  - `first_seen_*`
  - `last_seen_*`
- queue execution now runs the top pending trigger rather than blindly running the newest one
- legacy trigger registry can be normalized/repaired

## What is real now

### Verified on WSL
- build failure path is recorded
- smoke failure path is recorded
- sanitizer crash path is recorded
- duplicate crash tracking works
- policy execution updates registries
- regression auto-run really fires
- corpus sync really copies files into operational buckets
- regression trigger registry can be normalized and deduplicated

### Practical meaning
The system is now beyond "log some runs".
It has become a small operational loop with:

1. detection
2. classification
3. state update
4. prioritized follow-up execution
5. real corpus synchronization

## Still not solved

### 1. Not autonomous code repair
- it still does not modify harnesses or target code safely on its own
- policy execution is still mostly orchestration/stateful automation

### 2. Regression result semantics are coarse
- statuses like `failed` are still overloaded
- the system still needs richer meanings such as:
  - `known-regression-confirmed`
  - `blocked-by-build`
  - `reproduced`
  - `triage-needed`

### 3. Queue concurrency discipline is still weak
- there is no real file lock / multi-process queue discipline yet
- safe enough for single-operator iteration, not strong enough for concurrent controllers

### 4. Harness depth is still limited
Current primary target remains memory-buffer decode through:
- `fuzz/decode_memory_harness.cpp`
- `DecodeOneInput(data, size, verbose)`

This is a reasonable first target for crashes/UAF-style memory safety bugs,
but it is still just one API path.
If OpenHTJ2K has parser-side, tile-level, marker-handling, or multi-component edge cases beyond this path,
those may still be underexplored.

## Why remote Proxmox is now reasonable
Moving to Proxmox is now more justified than before because:

- WSL loop is no longer purely conceptual
- corpus roles are explicit
- regression triggers are executable
- queue behavior exists
- remote SSH path is already proven

But remote work should still be framed as:

**"run longer and wider using the already-validated local operating model"**

not as:

**"assume the system is fully autonomous now"**

## Recommended next remote stance
For sleep-time remote fuzzing, prefer:

1. keep the current decode-memory harness as the first remote target
2. seed with a small curated corpus first
3. separate known-bad / regression / coverage roles from day one
4. use strict sanitizers first, speed second
5. record remote findings back into md + registry structure

## Bottom line
Current state is good enough to justify **careful remote expansion**.
But the honest description is still:

> a policy-driven semi-automated fuzzing operations system, not a fully self-improving autonomous fuzzing agent.
