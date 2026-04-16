# Checklist — Hermes Watch R20 hold/abort downstream consumers v0.1

- [x] hold downstream consumer가 `harness_review_queue.json`에 실제 follow-up entry를 enqueue
- [x] abort downstream consumer가 `harness_correction_regeneration_queue.json`에 corrective follow-up entry를 enqueue
- [x] 새 corrective action `regenerate_harness_correction`를 refiner registry/orchestration spec에 등록
- [x] hold/abort follow-up lineage를 apply candidate manifest에 기록
- [x] TDD로 hold downstream consumer 테스트 추가 후 실패 확인
- [x] TDD로 abort downstream consumer 테스트 추가 후 실패 확인
- [x] TDD로 corrective regeneration refiner executor 테스트 추가 후 실패 확인
- [x] targeted tests 통과 확인
- [x] `tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests` 회귀 확인
- [x] `tests/test_hermes_watch.py` 회귀 확인
- [x] 전체 `tests` 회귀 확인
- [x] `py_compile` 검증 확인

## 검증 명령
- `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_run_harness_apply_recovery_downstream_automation_enqueues_hold_review_consumer tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_run_harness_apply_recovery_downstream_automation_enqueues_abort_corrective_consumer tests/test_hermes_watch.py::HermesWatchRefinerExecutorTests::test_execute_next_refiner_action_processes_harness_correction_regeneration -q`
- `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests -q`
- `python -m pytest tests/test_hermes_watch.py -q`
- `python -m pytest tests -q`
- `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/harness_skeleton.py scripts/hermes_watch_support/__init__.py tests/test_hermes_watch.py`

## 검증 결과
- targeted downstream/follow-up tests: `3 passed`
- targeted class: `43 passed`
- `tests/test_hermes_watch.py`: `195 passed`
- `tests`: `214 passed`
- `py_compile`: OK
