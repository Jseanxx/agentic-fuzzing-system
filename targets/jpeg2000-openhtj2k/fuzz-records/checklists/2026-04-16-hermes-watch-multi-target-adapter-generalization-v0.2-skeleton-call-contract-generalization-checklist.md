# 2026-04-16 — hermes_watch multi-target adapter generalization v0.2 skeleton call-contract generalization checklist

- [x] skeleton TODO wiring / target call shape / lifetime guidance의 남은 generic leakage를 점검했다
- [x] custom adapter의 call TODO / lifetime hint가 draft payload에 실제 반영돼야 한다는 failing test를 먼저 추가했다
- [x] written source artifact와 markdown에도 custom call contract가 실제 반영돼야 한다는 failing test를 먼저 추가했다
- [x] RED를 확인했다
- [x] target adapter에 `target_call_todo`, `resource_lifetime_hint` contract를 추가했다
- [x] profile summary / regression matrix가 새 contract를 보존하도록 확장했다
- [x] `_skeleton_call_contract(repo_root)` helper를 추가했다
- [x] `_render_skeleton_code(...)`가 adapter-driven call TODO / lifetime hint를 source comment에 반영하도록 확장했다
- [x] draft payload/markdown에 `skeleton_target_call_todo`, `skeleton_resource_lifetime_hint` metadata를 추가했다
- [x] `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/harness_skeleton.py scripts/hermes_watch_support/target_adapter.py scripts/hermes_watch_support/profile_summary.py tests/test_hermes_watch.py`로 문법 검증했다
- [x] `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests -q`로 집중 검증했다
- [x] `python -m pytest tests/test_hermes_watch.py -q`로 파일 단위 회귀 검증했다
- [x] `python -m pytest tests -q`로 전체 회귀 검증했다
- [x] note / current-status / progress-index를 갱신했다
- [x] 이번 단계의 구조적 의미와 한계를 냉정하게 기록했다
