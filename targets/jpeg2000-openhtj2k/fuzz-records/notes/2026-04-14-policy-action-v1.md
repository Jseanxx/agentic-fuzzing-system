# Policy Action v1 — 2026-04-14

## What was added
watcher now chooses a **policy action** from the classified outcome.

This is not full automation yet, but it is the first step from:
- merely recording outcomes

to:
- recording outcomes **plus a structured next-action recommendation**

## Output fields
These fields now appear in status/report output:
- `policy_priority`
- `policy_action_code`
- `policy_recommended_action`
- `policy_next_mode`
- `policy_bucket`

## Current policy actions
### build-failed
- `action_code: fix-build-before-fuzzing`
- priority: `high`
- next_mode: `regression`
- bucket: `build`

### smoke-failed
- `action_code: promote-seed-to-regression-and-triage`
- priority: `high`
- next_mode: `triage`
- bucket: `regression`

### new crash
- `action_code: triage-new-crash`
- priority: `high`
- next_mode: `triage`
- bucket: `triage`

### duplicate crash
- `action_code: record-duplicate-crash`
- priority: `medium`
- next_mode: `coverage`
- bucket: `known-bad`

### leak
- `action_code: triage-leak-and-consider-coverage-policy`
- priority: `medium`
- next_mode: `coverage`
- bucket: `triage`

### timeout
- `action_code: inspect-slow-path-or-timeout-policy`
- priority: `medium`
- next_mode: `triage`
- bucket: `triage`

### no-progress
- `action_code: improve-corpus-or-harness`
- priority: `medium`
- next_mode: `coverage`
- bucket: `coverage`

### unclear nonzero exit
- `action_code: inspect-nonzero-exit`
- priority: `medium`
- next_mode: `triage`
- bucket: `triage`

## Verified behavior
- duplicate triage crash now produces:
  - `policy_action_code: record-duplicate-crash`
  - `policy_next_mode: coverage`
  - `policy_bucket: known-bad`

## Meaning
이제 watcher는 단순한 recorder가 아니라,
**정책 기반 반자동 운영 추천기** 역할도 조금 시작한 상태다.

## Limit of v1
- policy action is still advisory, not auto-executed
- no automatic corpus move/promote yet
- no regression enforcement hook yet
- no multi-step policy chaining yet
