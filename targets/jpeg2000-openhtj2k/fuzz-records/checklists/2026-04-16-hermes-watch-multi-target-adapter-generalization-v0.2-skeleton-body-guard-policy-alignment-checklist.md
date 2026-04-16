# 2026-04-16 — hermes_watch multi-target adapter generalization v0.2 skeleton body guard-policy alignment checklist

- [x] skeleton source body에 남아 있는 generic `hermes_prepare_input(...)` / `return 0;` leakage를 점검했다
- [x] custom adapter guard policy가 skeleton draft body에 실제 반영돼야 한다는 failing test를 먼저 추가했다
- [x] written source artifact도 custom guard policy를 실제 반영해야 한다는 failing test를 먼저 추가했다
- [x] RED를 확인했다
- [x] `_skeleton_guard_contract(repo_root)` helper를 추가했다
- [x] `_render_skeleton_code(...)`가 custom guard condition / return policy를 받도록 확장했다
- [x] C / C++ skeleton source draft에서 generic prepare helper를 제거하고 adapter-driven initial guard를 직접 배치했다
- [x] draft payload/markdown에 `skeleton_guard_condition`, `skeleton_guard_return_statement` metadata를 추가했다
- [x] `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/harness_skeleton.py scripts/hermes_watch_support/target_adapter.py scripts/hermes_watch_support/profile_summary.py tests/test_hermes_watch.py`로 문법 검증했다
- [x] `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests -q`로 집중 검증했다
- [x] `python -m pytest tests/test_hermes_watch.py -q`로 파일 단위 회귀 검증했다
- [x] `python -m pytest tests -q`로 전체 회귀 검증했다
- [x] note / current-status / progress-index를 갱신했다
- [x] 이번 단계의 구조적 의미와 한계를 냉정하게 기록했다
