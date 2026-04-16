# R20 Actual Skeleton Closure Focus

## Why this step now
R20 revision intelligence v0.1은 skeleton layer가 build/smoke 결과를 구조화했지만, 그 입력은 아직 skeleton-specific execution closure보다 느슨했다.

이번 단계의 목적은:
- latest skeleton artifact에 대해 build/smoke probe를 실제로 돌리고
- 그 closure evidence를 다음 revision intelligence가 우선 읽도록 만들어
- skeleton revision loop를 더 실제적인 execution substrate로 끌어올리는 것이다.

## Scope boundary
이번 단계는 actual closure까지다.
- patch-level autonomous correction은 아직 아님
- lifecycle canonicalization도 아직 아님
- multi-target runtime generalization도 아직 아님

즉, 이번 단계는 **R20 actual closure v0.1**로, skeleton revision loop를 artifact-first advisory layer에서 skeleton-specific execution evidence layer로 밀어 올린다.

## What was actually added
- latest skeleton artifact 기준 build/smoke probe 실행 함수 `run_harness_skeleton_closure(...)` 추가
- `fuzz-records/harness-skeleton-probes/` 아래 closure manifest/markdown 생성
- skeleton revision intelligence가 latest closure evidence를 probe feedback보다 우선 사용하도록 확장
- `revision_signal_source`로 evidence 출처(`skeleton-closure` / `probe-feedback` / `heuristic`)를 기록
- CLI `--run-harness-skeleton-closure` 추가

## Verification
- `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests -q` → 9 passed
- `python -m pytest tests/test_hermes_watch.py -q` → 160 passed
- `python -m pytest tests -q` → 179 passed
- `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/harness_skeleton.py tests/test_hermes_watch.py` → OK

## Cold take
이번 단계는 의미가 크다.
- 이제 skeleton loop는 advisory-only draft 단계가 아니라
- latest skeleton artifact를 실제 build/smoke evidence와 닫는 실행 substrate를 갖게 됐다

하지만 여전히:
- patch-level autonomous correction
- lifecycle cleanup
- malformed nested registry/race hardening
은 다음 단계다.
