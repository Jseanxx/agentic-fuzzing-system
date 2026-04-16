# Checklist — Hermes Watch R20 recovery downstream automation v0.1

- [x] recovery queue consume 이후 retry lane을 bridge launch/verify까지 자동 연결하는 함수 추가
- [x] downstream launch/verify 상태를 apply candidate manifest에 기록
- [x] `--run-harness-apply-recovery-downstream-automation` CLI 추가
- [x] TDD로 downstream retry automation 테스트 추가 후 실패 확인
- [x] TDD로 main CLI downstream automation 테스트 추가 후 실패 확인
- [x] 구현 후 관련 타깃 테스트 통과 확인
- [x] `tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests` 회귀 확인
- [x] `tests/test_hermes_watch.py` 회귀 확인
- [x] 전체 `tests` 회귀 확인
- [x] `py_compile` 검증 확인

## 검증 명령
- `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_run_harness_apply_recovery_downstream_automation_launches_and_verifies_retry tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_main_run_harness_apply_recovery_downstream_automation_emits_artifacts -q`
- `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests -q`
- `python -m pytest tests/test_hermes_watch.py -q`
- `python -m pytest tests -q`
- `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/harness_skeleton.py scripts/hermes_watch_support/__init__.py tests/test_hermes_watch.py`

## 검증 결과
- targeted downstream tests: `2 passed`
- targeted class: `36 passed`
- `tests/test_hermes_watch.py`: `187 passed`
- `tests`: `206 passed`
- `py_compile`: OK
