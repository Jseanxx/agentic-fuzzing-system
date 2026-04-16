# R20 Patch-Level Autonomous Correction Focus

## Why this step now
R20 actual closure v0.1까지는 skeleton artifact가 실제 build/smoke evidence와 닫혔지만,
그 evidence를 보고 system이 source-adjacent correction draft를 만들지는 못했다.

이번 단계의 목적은:
- failed closure / revision focus를 읽고
- conservative patch suggestion을 만들고
- 사람이 검토하거나 다음 automation이 읽을 correction draft artifact를 남기는 것이다.

## Scope boundary
이번 단계는 draft-only correction이다.
- 실제 자동 patch apply는 아직 아님
- compile/fix/verify closed loop도 아직 아님
- lifecycle canonicalization도 아직 아님

즉, 이번 단계는 **autonomous correction substrate v0.1**로, “무엇을 고칠지”까지 system이 구조화하기 시작하는 구간이다.

## What was actually added
- revision focus(build-fix / smoke-fix / smoke-enable / confidence-raise)에 따라 conservative correction suggestion 생성기 추가
- skeleton draft 결과에 다음 metadata 추가
  - `correction_strategy`
  - `correction_suggestions`
- write path에서 correction draft artifact 생성
  - `*-correction-draft.json`
  - `*-correction-draft.md`
- skeleton manifest에 correction draft 경로 연결
- skeleton markdown에 `Patch Suggestions` section 추가

## Verification
- `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests -q` → 9 passed
- `python -m pytest tests/test_hermes_watch.py -q` → 160 passed
- `python -m pytest tests -q` → 179 passed
- `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/harness_skeleton.py tests/test_hermes_watch.py` → OK

## Cold take
이번 단계로 system은 드디어 단순한 revision focus를 넘어서,
**failed closure를 보고 source-adjacent correction draft를 남기는 단계**까지 들어왔다.

하지만 여전히:
- correction draft 소비/승격 규칙
- 실제 patch apply
- compile/fix/verify 완전 폐루프
는 다음 단계다.
