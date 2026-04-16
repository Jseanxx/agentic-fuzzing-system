# Checklist — Hermes Watch R20 recovery policy consumption / routing v0.1

- [x] latest apply candidate/result의 recovery decision을 읽는 routing 함수 추가
- [x] `retry / hold / abort / resolved` → action code / registry / bridge channel 매핑 추가
- [x] `fuzz-artifacts/automation/` 아래 recovery queue/registry 기록 추가
- [x] `fuzz-records/harness-apply-recovery/` routing artifact(json/md) 추가
- [x] apply candidate/result manifest에 recovery route metadata 역반영
- [x] TDD로 retry routing 테스트 추가 후 실패 확인
- [x] TDD로 hold routing 테스트 추가 후 실패 확인
- [x] TDD로 main CLI routing 테스트 추가 후 실패 확인
- [x] 구현 후 관련 타깃 테스트 통과 확인
- [x] `tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests` 회귀 확인
- [x] `tests/test_hermes_watch.py` 회귀 확인
- [x] 전체 `tests` 회귀 확인
- [x] `py_compile` 검증 확인

## 검증 명령
- `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_route_harness_apply_recovery_requeues_retry_decision tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_route_harness_apply_recovery_routes_hold_without_bridge_channel tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_main_route_harness_apply_recovery_emits_artifacts -q`
- `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests -q`
- `python -m pytest tests/test_hermes_watch.py -q`
- `python -m pytest tests -q`
- `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/harness_skeleton.py scripts/hermes_watch_support/__init__.py tests/test_hermes_watch.py`

## 검증 결과
- targeted recovery routing tests: `3 passed`
- targeted class: `31 passed`
- `tests/test_hermes_watch.py`: `182 passed`
- `tests`: `201 passed`
- `py_compile`: OK
