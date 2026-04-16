# Checklist — Hermes Watch R20 retry recursive chaining / termination guard v0.1

- [x] retry recursive chaining CLI 경로 연결
- [x] reroute decision이 `retry`가 아닐 때 종료 상태 반환 확인
- [x] `max_cycles` 도달 시 `max-cycles-reached` 종료 상태 반환 확인
- [x] recursive chain status/cycle count를 manifest에 기록
- [x] TDD로 resolved termination 테스트 확인
- [x] TDD로 max cycle termination 테스트 확인
- [x] TDD로 main CLI recursive chaining 테스트 확인
- [x] `tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests` 회귀 확인
- [x] `tests/test_hermes_watch.py` 회귀 확인
- [x] 전체 `tests` 회귀 확인
- [x] `py_compile` 검증 확인

## 검증 명령
- `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_run_harness_apply_recovery_recursive_chaining_stops_at_resolved tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_run_harness_apply_recovery_recursive_chaining_stops_at_max_cycles tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_main_run_harness_apply_retry_recursive_chaining_emits_artifacts -q`
- `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests -q`
- `python -m pytest tests/test_hermes_watch.py -q`
- `python -m pytest tests -q`
- `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/harness_skeleton.py scripts/hermes_watch_support/__init__.py tests/test_hermes_watch.py`

## 검증 결과
- targeted recursive chain tests: `3 passed`
- targeted class: `41 passed`
- `tests/test_hermes_watch.py`: `192 passed`
- `tests`: `211 passed`
- `py_compile`: OK
