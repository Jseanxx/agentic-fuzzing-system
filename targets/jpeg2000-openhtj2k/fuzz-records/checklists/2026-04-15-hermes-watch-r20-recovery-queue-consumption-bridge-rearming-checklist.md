# Checklist — Hermes Watch R20 recovery queue consumption / bridge rearming v0.1

- [x] recovery queue consumer 함수 추가
- [x] retry queue 소비 시 apply bridge 재arming 추가
- [x] hold queue 소비 시 review parking metadata 추가
- [x] abort/resolved baseline consumer 상태 반영 추가
- [x] `--consume-harness-apply-recovery-queue` CLI 추가
- [x] TDD로 retry queue consumer 테스트 추가 후 실패 확인
- [x] TDD로 hold queue consumer 테스트 추가 후 실패 확인
- [x] TDD로 main CLI consumer 테스트 추가 후 실패 확인
- [x] 구현 후 관련 타깃 테스트 통과 확인
- [x] `tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests` 회귀 확인
- [x] `tests/test_hermes_watch.py` 회귀 확인
- [x] 전체 `tests` 회귀 확인
- [x] `py_compile` 검증 확인

## 검증 명령
- `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_consume_harness_apply_retry_queue_rearms_bridge tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_consume_harness_apply_hold_queue_marks_review_lane tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_main_consume_harness_apply_recovery_queue_emits_artifacts -q`
- `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests -q`
- `python -m pytest tests/test_hermes_watch.py -q`
- `python -m pytest tests -q`
- `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/harness_skeleton.py scripts/hermes_watch_support/__init__.py tests/test_hermes_watch.py`

## 검증 결과
- targeted consumer tests: `3 passed`
- targeted class: `34 passed`
- `tests/test_hermes_watch.py`: `185 passed`
- `tests`: `204 passed`
- `py_compile`: OK
