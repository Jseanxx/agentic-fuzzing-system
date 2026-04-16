# R20 Revision Intelligence Focus

## Why this step now
R19는 skeleton draft substrate를 만들었지만, build/smoke outcome을 revision layer가 충분히 구조화해서 소비하지 못한다.

R20의 첫 조각은 full autonomous fixing이 아니다.
대신:
- latest probe feedback를 skeleton layer가 읽고
- 다음 revision의 핵심 초점(build-fix / smoke-fix / confidence-raise)을 정리하며
- 사람과 future automation이 모두 읽기 쉬운 metadata로 남기는 것이다.

## Scope boundary
이번 단계는 advisory intelligence layer다.
- 실제 compile/fix/verify closed loop는 아직 아님
- patch synthesis도 아직 아님
- lifecycle rework도 아직 아님

즉, 이번 단계의 목적은 R19의 얕은 revision loop를 **evidence-aware revision loop v0.1**로 올리는 것이다.

## What was actually added
- latest probe feedback의 `build_probe_status` / `smoke_probe_status`를 skeleton layer가 읽도록 확장
- skeleton draft에 다음 metadata 추가
  - `revision_priority`
  - `next_revision_focus`
  - `revision_signals`
  - `revision_summary`
- revision loop가 focus(build-fix / smoke-fix / smoke-enable / confidence-raise)에 따라 더 구체적으로 달라지도록 확장
- markdown에 `Revision Intelligence` section 추가
- manifest에 revision intelligence metadata 저장

## Verification
- `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests -q` → 6 passed
- `python -m pytest tests/test_hermes_watch.py -q` → 157 passed
- `python -m pytest tests -q` → 176 passed
- `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/harness_skeleton.py tests/test_hermes_watch.py` → OK

## Cold take
이번 단계는 아직 advisory layer지만, 의미는 분명하다.
- R19가 단순 skeleton draft substrate였다면
- 지금은 build/smoke evidence를 읽고 다음 revision의 초점을 구조화하는 **evidence-aware revision loop v0.1**까지 올라왔다

하지만 여전히:
- actual skeleton compile execution closure
- patch-level autonomous correction
- lifecycle cleanup
은 다음 단계다.
