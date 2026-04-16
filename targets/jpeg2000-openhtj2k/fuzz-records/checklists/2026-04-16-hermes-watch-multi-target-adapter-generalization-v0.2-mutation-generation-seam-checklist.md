# 2026-04-16 — hermes_watch multi-target adapter generalization v0.2 mutation generation seam checklist

- [x] mutation generation seam의 남은 하드코딩 지점을 점검했다
- [x] `_inject_guarded_patch(...)`가 custom fuzz entrypoint 이름을 직접 소비하는 failing test를 먼저 추가했다
- [x] custom C++ fuzz entrypoint signature 지원 failing test를 먼저 추가했다
- [x] runtime adapter profile이 실제 guarded apply path의 mutation generation에 반영되는 E2E failing test를 추가했다
- [x] RED를 확인했다
- [x] `_build_guard_only_patch_plan(...)` helper로 mutation planning seam을 분리했다
- [x] `_inject_guarded_patch(...)`에 `entrypoint_names` 전달 경로를 추가했다
- [x] `apply_verified_harness_patch_candidate(...)`가 runtime adapter의 `fuzz_entrypoint_names`를 실제 사용하도록 연결했다
- [x] 기존 monkeypatch 기반 guardrail regression tests가 깨지지 않도록 fallback 호환성을 유지했다
- [x] `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/target_adapter.py scripts/hermes_watch_support/profile_summary.py tests/test_hermes_watch.py`로 문법 검증했다
- [x] `python -m pytest tests/test_hermes_watch.py::HermesWatchTargetAdapterTests tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests -q`로 집중 검증했다
- [x] `python -m pytest tests/test_hermes_watch.py -q`로 파일 단위 회귀 검증했다
- [x] `python -m pytest tests -q`로 전체 회귀 검증했다
- [x] note / current-status / progress-index를 이번 단계에 맞게 갱신했다
- [x] 이번 단계의 구조적 의미와 한계를 냉정하게 기록했다
