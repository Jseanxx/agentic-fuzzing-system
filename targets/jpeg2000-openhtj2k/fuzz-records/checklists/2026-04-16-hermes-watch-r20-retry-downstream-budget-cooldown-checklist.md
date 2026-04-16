# Checklist — Hermes Watch R20 retry and downstream budget/cooldown v0.1

- [x] retry recursive chain에 cooldown guard 추가
- [x] reingested downstream chain에 budget guard 추가
- [x] reingested downstream chain에 cooldown guard 추가
- [x] downstream attempt count lineage 기록 추가
- [x] CLI 성공 조건에 `cooldown-active` / `budget-exhausted` guard 상태 반영
- [x] TDD로 retry recursive cooldown 테스트 추가 후 실패 확인
- [x] TDD로 downstream budget guard 테스트 추가 후 실패 확인
- [x] targeted guard tests 통과 확인
- [x] `tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests` 회귀 확인
- [x] `tests/test_hermes_watch.py` 회귀 확인
- [x] 전체 `tests` 회귀 확인
- [x] `py_compile` 검증 확인

## 검증 명령
- `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_run_harness_apply_retry_recursive_chaining_respects_cooldown_window tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_run_harness_apply_reingested_downstream_chaining_respects_budget_limit -q`
- `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests -q`
- `python -m pytest tests/test_hermes_watch.py -q`
- `python -m pytest tests -q`
- `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/harness_skeleton.py scripts/hermes_watch_support/__init__.py tests/test_hermes_watch.py`

## 검증 결과
- targeted budget/cooldown tests: `2 passed`
- targeted class: `53 passed`
- `tests/test_hermes_watch.py`: `207 passed`
- `tests`: `226 passed`
- `py_compile`: OK
