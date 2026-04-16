# Policy Action Auto-Execution v1 — 2026-04-14

## What changed
정책 액션이 이제 단순 추천만 하는 것이 아니라, 일부 안전한 작업은 자동으로 집행한다.

## Current auto-executed actions
### 1. policy action log
- path: `fuzz-artifacts/automation/policy_actions.json`
- every finalized run appends a structured policy-action record

### 2. known-bad registry
- path: `fuzz-artifacts/automation/known_bad.json`
- when action is `record-duplicate-crash`, the fingerprint is automatically tracked here

### 3. regression candidate registry
- path: `fuzz-artifacts/automation/regression_candidates.json`
- when action is `promote-seed-to-regression-and-triage`, a regression candidate entry is created

## New output field
- `policy_execution_updated`
  - shows which registries were updated automatically during the run

## Verified now
- duplicate triage crash automatically updated:
  - `policy_actions.json`
  - `known_bad.json`
- `current_status.json` includes:
  - `policy_execution_updated: ["policy_log", "known_bad"]`

## Why this matters
이제 시스템은
- 분류한다
- dedup 한다
- 정책 액션을 추천한다
- 그리고 일부 안전한 상태 갱신은 자동 수행한다

즉 완전 자율은 아니지만,
**반자동 운영 시스템에서 부분 자동 집행 시스템**으로 한 단계 더 올라왔다.

## Limits of auto-execution v1
- corpus 파일 이동/복사는 아직 자동 아님
- regression run 자체를 자동으로 다시 돌리지는 않음
- Discord 우선순위 조정 자동화 없음
- destructive action은 아직 없음 (의도적으로 보수적)
