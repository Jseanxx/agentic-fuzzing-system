# 2026-04-16 — secondary-conflict-aware routing v0.1 checklist

- [x] 현재 recovery routing / reverse-link override 흐름 점검
- [x] failing test 먼저 추가
  - [x] secondary conflict가 `present`인 retry routing은 `hold`로 override되어야 함
  - [x] clean retry path는 secondary conflict routing metadata를 `none`으로 남겨야 함
- [x] RED 확인
  - [x] retry가 그대로 유지되어 override 실패
  - [x] `routing_secondary_conflict_status` 필드 없음
- [x] secondary conflict routing helper 추가
- [x] `route_harness_apply_recovery(...)`에 secondary conflict 소비 로직 연결
- [x] routing lineage 확장
  - [x] `routing_secondary_conflict_status`
  - [x] `routing_secondary_conflict_count`
  - [x] `routing_secondary_conflict_reasons`
  - [x] `routing_secondary_conflict_deferred_reason_codes`
- [x] route manifest / apply candidate manifest / apply result payload 반영
- [x] GREEN 확인
  - [x] `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_route_harness_apply_recovery_secondary_conflict_overrides_retry_to_hold tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_route_harness_apply_recovery_marks_no_secondary_conflict_when_retry_path_is_clean -q` → 2 passed
- [x] syntax 검증
  - [x] `python -m py_compile scripts/hermes_watch.py tests/test_hermes_watch.py` → OK
- [x] targeted class regression 검증
  - [x] `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests -q` → 85 passed
- [x] file-level regression 검증
  - [x] `python -m pytest tests/test_hermes_watch.py -q` → 263 passed
- [x] full regression 검증
  - [x] `python -m pytest tests -q` → 282 passed
- [x] status / progress / note / checklist 갱신

## 냉정한 판정
- [x] 이번 단계는 secondary conflict를 이해한 게 아니라 retry action에 보수적으로 반영하기 시작한 단계다
- [x] visibility-only 상태를 넘어 routing override까지 갔지만 아직 severity/actionability 분해는 없다
- [x] 다음은 failure reason extraction v0.8 또는 secondary-conflict severity/actionability 분리가 자연스럽다
