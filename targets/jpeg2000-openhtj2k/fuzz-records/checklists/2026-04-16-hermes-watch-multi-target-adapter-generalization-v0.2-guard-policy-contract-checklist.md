# 2026-04-16 — hermes_watch multi-target adapter generalization v0.2 guard policy contract checklist

- [x] mutation generation seam 다음 leakage로 남아 있던 guard condition / early return 하드코딩 지점을 점검했다
- [x] adapter가 `guard_condition`, `guard_return_statement`를 실제 보존해야 한다는 failing test를 먼저 추가했다
- [x] `_inject_guarded_patch(...)`가 custom guard condition / return policy를 직접 반영해야 한다는 failing test를 먼저 추가했다
- [x] regression smoke matrix가 guard policy metadata를 기록해야 한다는 failing test를 추가했다
- [x] runtime profile이 guarded apply E2E path에서 custom guard policy를 실제 적용해야 한다는 failing test를 추가했다
- [x] RED를 확인했다
- [x] `TargetAdapter`와 summary/matrix helper를 새 policy field로 확장했다
- [x] `_build_guard_only_patch_plan(...)` / `_inject_guarded_patch(...)`에 custom guard policy 전달 경로를 추가했다
- [x] `_guard_only_line_allowed(...)` / `_diff_safety_guardrails(...)`가 custom guard policy를 whitelist에 반영하게 만들었다
- [x] 기존 monkeypatch lambda regression tests를 깨지 않도록 compatibility fallback을 유지했다
- [x] `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/target_adapter.py scripts/hermes_watch_support/profile_summary.py tests/test_hermes_watch.py`로 문법 검증했다
- [x] `python -m pytest tests/test_hermes_watch.py::HermesWatchTargetAdapterTests tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests -q`로 집중 검증했다
- [x] `python -m pytest tests/test_hermes_watch.py -q`로 파일 단위 회귀 검증했다
- [x] `python -m pytest tests -q`로 전체 회귀 검증했다
- [x] note / current-status / progress-index를 갱신했다
- [x] 이번 단계의 구조적 의미와 한계를 냉정하게 기록했다
