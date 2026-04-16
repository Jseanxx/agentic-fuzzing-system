# Checklist — multi-target adapter generalization v0.2 command separation slice

- [x] probe/closure 계층의 build/smoke command leakage 지점 확인
- [x] custom adapter command를 요구하는 failing test 2개 추가 및 RED 확인
- [x] `harness_probe` 계층에 profile-driven adapter resolution 추가
- [x] `build_harness_probe_draft(...)`가 adapter build/smoke command를 우선 사용하도록 반영
- [x] `run_harness_skeleton_closure(...)`가 같은 adapter-driven probe command를 재사용하도록 검증
- [x] `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/harness_probe.py scripts/hermes_watch_support/harness_skeleton.py scripts/hermes_watch_support/profile_summary.py scripts/hermes_watch_support/target_adapter.py tests/test_hermes_watch.py`
- [x] `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessProbeTests tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests -q`
- [x] `python -m pytest tests/test_hermes_watch.py -q`
- [x] `python -m pytest tests -q`
