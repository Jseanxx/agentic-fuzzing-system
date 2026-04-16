# Checklist — Hermes Watch R20 hold/abort follow-up auto-reingestion v0.1

- [x] verified hold review follow-up를 correction-policy loop로 재주입하는 runner 추가
- [x] verified abort corrective regeneration follow-up를 apply-candidate loop로 재주입하는 runner 추가
- [x] follow-up registry entry에 reingestion lineage 기록 추가
- [x] original apply candidate manifest에 follow-up reingestion lineage 기록 추가
- [x] `--run-harness-apply-recovery-followup-auto-reingestion` CLI 추가
- [x] TDD로 hold review reingestion 테스트 추가 후 실패 확인
- [x] TDD로 abort regeneration reingestion 테스트 추가 후 실패 확인
- [x] TDD로 main CLI reingestion 테스트 추가 후 실패 확인
- [x] targeted reingestion tests 통과 확인
- [x] `tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests` 회귀 확인
- [x] `tests/test_hermes_watch.py` 회귀 확인
- [x] 전체 `tests` 회귀 확인
- [x] `py_compile` 검증 확인

## 검증 명령
- `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_run_harness_apply_recovery_followup_auto_reingestion_rehydrates_hold_review_into_correction_policy tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_run_harness_apply_recovery_followup_auto_reingestion_rehydrates_abort_regeneration_into_apply_candidate tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_main_run_harness_apply_recovery_followup_auto_reingestion_emits_artifacts -q`
- `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests -q`
- `python -m pytest tests/test_hermes_watch.py -q`
- `python -m pytest tests -q`
- `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/harness_skeleton.py scripts/hermes_watch_support/__init__.py tests/test_hermes_watch.py`

## 검증 결과
- targeted follow-up reingestion tests: `3 passed`
- targeted class: `48 passed`
- `tests/test_hermes_watch.py`: `200 passed`
- `tests`: `219 passed`
- `py_compile`: OK
