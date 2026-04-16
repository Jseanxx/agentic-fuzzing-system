# Regression Auto-Trigger v1 — 2026-04-14

## What was added
policy execution can now automatically create a regression trigger record for selected outcomes.

## Current trigger policy
Regression auto-trigger is currently enabled for:
- `build-failed`
- `smoke-failed`

It is currently NOT auto-triggered for:
- duplicate crash
- generic crash
- leak
- no-progress

## What it does in v1
This version does **not** immediately launch a full regression run.
Instead, it safely records an auto-trigger request so the workflow becomes machine-readable and auditable.

## Registry
- path: `fuzz-artifacts/automation/regression_triggers.json`

Stored fields:
- `trigger_reason`
- `run_dir`
- `report_path`
- `command`
- `status`

## Current command template
```bash
bash scripts/run-fuzz-mode.sh regression
```

## Verified behavior
- a real `smoke-failed` run automatically produced:
  - `regression_candidates.json`
  - `regression_triggers.json`
  - `policy_execution_updated: ['policy_log', 'regression_candidates', 'regression_trigger']`

## Meaning
이제 시스템은 특정 실패를 보면
단순히 "나중에 regression 해봐" 수준이 아니라,
**regression을 해야 한다는 사실을 구조화된 형태로 자동 등록**한다.

## Limits of v1
- 실제 regression run을 즉시 실행하지는 않는다
- trigger queue만 만든다
- trigger dedup/priority scheduling은 아직 단순하다
- SSH/remote target 연동은 아직 없다
