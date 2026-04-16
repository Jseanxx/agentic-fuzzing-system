# Checklist — Hermes Watch R20 reingested downstream chaining v0.1

- [x] verified hold review reingestion 뒤 apply-candidate 생성과 downstream chain runner 추가
- [x] verified abort regeneration reingestion 뒤 bridge/verify/apply/reroute chain runner 추가
- [x] original apply candidate manifest에 follow-up chain lineage 기록 추가
- [x] `--run-harness-apply-reingested-downstream-chaining` CLI 추가
- [x] TDD로 hold reingested chaining 테스트 추가 후 실패 확인
- [x] TDD로 abort reingested chaining 테스트 추가 후 실패 확인
- [x] TDD로 main CLI reingested chaining 테스트 추가 후 실패 확인
- [x] targeted chaining tests 통과 확인
- [x] `tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests` 회귀 확인
- [x] `tests/test_hermes_watch.py` 회귀 확인
- [x] 전체 `tests` 회귀 확인
- [x] `py_compile` 검증 확인

## 검증 명령
- `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_run_harness_apply_reingested_downstream_chaining_chains_hold_reingestion_into_apply_and_reroute tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_run_harness_apply_reingested_downstream_chaining_chains_abort_reingestion_into_apply_and_reroute tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_main_run_harness_apply_reingested_downstream_chaining_emits_artifacts -q`
- `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests -q`
- `python -m pytest tests/test_hermes_watch.py -q`
- `python -m pytest tests -q`
- `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/harness_skeleton.py scripts/hermes_watch_support/__init__.py tests/test_hermes_watch.py`

## 검증 결과
- targeted reingested chaining tests: `3 passed`
- targeted class: `51 passed`
- `tests/test_hermes_watch.py`: `203 passed`
- `tests`: `222 passed`
- `py_compile`: OK
