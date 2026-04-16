# 2026-04-16 — secondary-conflict severity/actionability v0.1 checklist

- [x] 현재 secondary-conflict-aware routing 흐름 점검
- [x] failing test 먼저 추가
  - [x] reviewable deferred conflict는 `hold`로 가야 함
  - [x] severe build-side deferred conflict는 `abort`로 가야 함
  - [x] clean retry path는 severity/actionability를 `none`으로 남겨야 함
- [x] RED 확인
  - [x] status가 기존 단일 `override-from-secondary-conflict`로 남음
  - [x] severe conflict가 아직 `abort`로 안 감
  - [x] severity/actionability 필드 없음
- [x] secondary conflict severity/actionability helper 확장
- [x] routing 필드 확장
  - [x] `routing_secondary_conflict_severity`
  - [x] `routing_secondary_conflict_actionability`
- [x] hold/abort status 분리
  - [x] `override-from-secondary-conflict-hold`
  - [x] `override-from-secondary-conflict-abort`
- [x] route manifest / apply candidate manifest / apply result payload 반영
- [x] GREEN 확인
  - [x] `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_route_harness_apply_recovery_secondary_conflict_overrides_retry_to_hold_for_reviewable_tension tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_route_harness_apply_recovery_secondary_conflict_overrides_retry_to_abort_for_severe_build_tension tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_route_harness_apply_recovery_marks_no_secondary_conflict_when_retry_path_is_clean -q` → 3 passed
- [x] syntax 검증
  - [x] `python -m py_compile scripts/hermes_watch.py tests/test_hermes_watch.py` → OK
- [x] targeted class regression 검증
  - [x] `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests -q` → 86 passed
- [x] file-level regression 검증
  - [x] `python -m pytest tests/test_hermes_watch.py -q` → 266 passed
- [x] full regression 검증
  - [x] `python -m pytest tests -q` → 285 passed
- [x] status / progress / note / checklist 갱신

## 냉정한 판정
- [x] 이번 단계는 정교한 severity engine이 아니라 hold 급 vs abort 급의 최소 분리다
- [x] secondary conflict routing이 조금 더 정책다워졌지만 아직 coarse heuristic이다
- [x] 다음은 finding-efficiency-facing intelligence나 confidence/budget linkage가 자연스럽다
