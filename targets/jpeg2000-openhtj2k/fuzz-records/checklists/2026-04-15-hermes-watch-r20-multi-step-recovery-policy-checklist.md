# Checklist — Hermes Watch R20 multi-step recovery policy v0.1

- [x] apply result에서 `retry / hold / abort / resolved`를 계산하는 recovery policy 추가
- [x] blocked apply가 `hold`로 기록되도록 반영
- [x] first rollback failure가 `retry`로 기록되도록 반영
- [x] repeated rollback failure가 `abort`로 기록되도록 반영
- [x] `recovery_failure_streak`, `recovery_attempt_count`, `recovery_status` metadata 기록
- [x] TDD로 recovery decision 테스트 추가 후 실패 확인
- [x] 구현 후 관련 타깃 테스트 통과 확인
- [x] `tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests` 회귀 확인
- [x] `tests/test_hermes_watch.py` 회귀 확인
- [x] 전체 `tests` 회귀 확인
- [x] `py_compile` 검증 확인

## 검증 명령
- `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_apply_verified_harness_patch_candidate_rolls_back_on_build_failure tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_apply_verified_harness_patch_candidate_escalates_repeated_failures_to_abort tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_apply_verified_harness_patch_candidate_blocks_scope_semantics_mismatch -q`
- `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests -q`
- `python -m pytest tests/test_hermes_watch.py -q`
- `python -m pytest tests -q`
- `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/harness_skeleton.py scripts/hermes_watch_support/__init__.py tests/test_hermes_watch.py`

## 검증 결과
- targeted recovery tests: `3 passed`
- targeted class: `28 passed`
- `tests/test_hermes_watch.py`: `179 passed`
- `tests`: `198 passed`
- `py_compile`: OK
