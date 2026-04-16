# Checklist — Hermes Watch R20 candidate semantics / diff safety v0.1

- [x] apply candidate summary 기반 semantics guardrail 추가
- [x] out-of-scope mutation keyword 차단 추가
- [x] generated harness 디렉터리 밖 target file 차단 추가
- [x] scope별 changed line count 상한 추가
- [x] blocked apply를 result/manifest artifact로 기록
- [x] TDD로 semantics mismatch blocking 테스트 추가 후 실패 확인
- [x] TDD로 target path diff safety blocking 테스트 추가 후 실패 확인
- [x] 구현 후 관련 타깃 테스트 통과 확인
- [x] `tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests` 회귀 확인
- [x] `tests/test_hermes_watch.py` 회귀 확인
- [x] 전체 `tests` 회귀 확인
- [x] `py_compile` 검증 확인

## 검증 명령
- `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_apply_verified_harness_patch_candidate_blocks_scope_semantics_mismatch tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_apply_verified_harness_patch_candidate_blocks_target_outside_generated_harness_dir tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_apply_verified_harness_patch_candidate_guard_only_inserts_min_size_guard tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_apply_verified_harness_patch_candidate_rolls_back_on_build_failure -q`
- `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests -q`
- `python -m pytest tests/test_hermes_watch.py -q`
- `python -m pytest tests -q`
- `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/harness_skeleton.py scripts/hermes_watch_support/__init__.py tests/test_hermes_watch.py`

## 검증 결과
- targeted safety tests: `4 passed`
- targeted class: `27 passed`
- `tests/test_hermes_watch.py`: `178 passed`
- `tests`: `197 passed`
- `py_compile`: OK
