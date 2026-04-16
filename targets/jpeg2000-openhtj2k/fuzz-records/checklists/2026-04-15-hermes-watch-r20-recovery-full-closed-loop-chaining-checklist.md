# Checklist — Hermes Watch R20 recovery full closed-loop chaining v0.1

- [x] retry downstream verified 이후 apply + reroute를 잇는 full-chain 함수 추가
- [x] full-chain status를 apply candidate manifest에 기록
- [x] `--run-harness-apply-recovery-full-closed-loop-chaining` CLI 추가
- [x] TDD로 full closed-loop chaining 함수 테스트 추가 후 실패 확인
- [x] TDD로 main CLI full closed-loop chaining 테스트 추가 후 실패 확인
- [x] 구현 후 관련 타깃 테스트 통과 확인
- [x] `tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests` 회귀 확인
- [x] `tests/test_hermes_watch.py` 회귀 확인
- [x] 전체 `tests` 회귀 확인
- [x] `py_compile` 검증 확인

## 검증 명령
- `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_run_harness_apply_recovery_full_closed_loop_chaining_applies_and_reroutes_after_verified_retry tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_main_run_harness_apply_recovery_full_closed_loop_chaining_emits_artifacts -q`
- `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests -q`
- `python -m pytest tests/test_hermes_watch.py -q`
- `python -m pytest tests -q`
- `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/harness_skeleton.py scripts/hermes_watch_support/__init__.py tests/test_hermes_watch.py`

## 검증 결과
- targeted full-chain tests: `2 passed`
- targeted class: `38 passed`
- `tests/test_hermes_watch.py`: `189 passed`
- `tests`: `208 passed`
- `py_compile`: OK
