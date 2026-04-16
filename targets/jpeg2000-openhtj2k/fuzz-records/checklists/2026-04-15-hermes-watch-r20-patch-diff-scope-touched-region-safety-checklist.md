# Checklist — Hermes Watch R20 patch diff scope / touched-region safety v0.1

- [x] generated harness 내부 touched-region 판정을 위한 entrypoint region helper 추가
- [x] guard-only patch가 fuzzer entrypoint 밖을 건드리면 차단
- [x] comment-only patch가 append-only Hermes comment 외의 편집을 하면 차단
- [x] guard-only patch line whitelist 추가
- [x] multi-hunk diff baseline 차단 추가
- [x] diff safety metadata에 hunk/touched-region 상태 확장
- [x] blocked return payload에 diff safety reason/touched-region metadata 노출
- [x] TDD로 guard-only touched-region 차단 테스트 추가 후 실패 확인
- [x] TDD로 comment-only whitelist 차단 테스트 추가 후 실패 확인
- [x] targeted tests 통과 확인
- [x] `tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests` 회귀 확인
- [x] `tests/test_hermes_watch.py` 회귀 확인
- [x] 전체 `tests` 회귀 확인
- [x] `py_compile` 검증 확인

## 검증 명령
- `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_apply_verified_harness_patch_candidate_blocks_guard_only_touch_outside_fuzzer_entrypoint tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_apply_verified_harness_patch_candidate_blocks_comment_only_non_whitelisted_edit -q`
- `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests -q`
- `python -m pytest tests/test_hermes_watch.py -q`
- `python -m pytest tests -q`
- `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/harness_skeleton.py scripts/hermes_watch_support/__init__.py tests/test_hermes_watch.py`

## 검증 결과
- targeted diff safety tests: `2 passed`
- targeted class: `45 passed`
- `tests/test_hermes_watch.py`: `197 passed`
- `tests`: `216 passed`
- `py_compile`: OK
