# 2026-04-16 — hermes_watch multi-target adapter generalization v0.2 skeleton entrypoint de-hardcode checklist

- [x] harness skeleton source draft에 남아 있는 `LLVMFuzzerTestOneInput` 하드코딩 지점을 점검했다
- [x] custom adapter entrypoint 이름이 skeleton draft에 실제 반영돼야 한다는 failing test를 먼저 추가했다
- [x] custom adapter entrypoint 이름이 written source artifact에도 실제 반영돼야 한다는 failing test를 먼저 추가했다
- [x] RED를 확인했다
- [x] skeleton layer에서 runtime adapter를 resolve하는 helper를 추가했다
- [x] `_skeleton_entrypoint_name(repo_root)` helper를 추가했다
- [x] `_render_skeleton_code(...)`가 custom skeleton entrypoint 이름을 받도록 확장했다
- [x] `build_harness_skeleton_draft(...)` payload에 `skeleton_entrypoint_name` metadata를 추가했다
- [x] markdown/manifest가 새 metadata를 보여 주도록 갱신했다
- [x] `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/harness_skeleton.py scripts/hermes_watch_support/target_adapter.py scripts/hermes_watch_support/profile_summary.py tests/test_hermes_watch.py`로 문법 검증했다
- [x] `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests -q`로 집중 검증했다
- [x] `python -m pytest tests/test_hermes_watch.py -q`로 파일 단위 회귀 검증했다
- [x] `python -m pytest tests -q`로 전체 회귀 검증했다
- [x] note / current-status / progress-index를 갱신했다
- [x] 이번 단계의 구조적 의미와 한계를 냉정하게 기록했다
