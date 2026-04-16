# Checklist — Hermes Watch adaptive retry / downstream budget-cooldown v0.1

- [x] reverse-linked failure / routing risk 기반 adaptive recursive retry cooldown helper 추가
- [x] reverse-linked failure / routing risk 기반 adaptive downstream budget helper 추가
- [x] reverse-linked failure / routing risk 기반 adaptive downstream cooldown helper 추가
- [x] retry/downstream guard return payload에 adaptive reason 노출
- [x] TDD로 recursive retry adaptive cooldown 테스트 추가 후 실패 확인
- [x] TDD로 downstream adaptive budget 테스트 추가 후 실패 확인
- [x] targeted adaptive guard tests 통과 확인
- [x] `tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests` 회귀 확인
- [x] `tests/test_hermes_watch.py` 회귀 확인
- [x] 전체 `tests` 회귀 확인
- [x] `py_compile` 검증 확인

## 검증 명령
- `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_run_harness_apply_retry_recursive_chaining_adapts_cooldown_from_routing_risk tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_run_harness_apply_reingested_downstream_chaining_adapts_budget_from_routing_risk -q`
- `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests -q`
- `python -m pytest tests/test_hermes_watch.py -q`
- `python -m pytest tests -q`
- `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/harness_skeleton.py scripts/hermes_watch_support/__init__.py tests/test_hermes_watch.py`

## 검증 결과
- targeted adaptive guard tests: `2 passed`
- targeted class: `57 passed`
- `tests/test_hermes_watch.py`: `211 passed`
- `tests`: `230 passed`
- `py_compile`: OK
