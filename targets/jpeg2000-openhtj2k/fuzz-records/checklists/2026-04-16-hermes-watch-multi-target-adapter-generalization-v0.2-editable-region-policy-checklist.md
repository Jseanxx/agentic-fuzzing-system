# Checklist — multi-target adapter generalization v0.2 editable-region policy seam slice

- [x] editable-region safety 하드코딩 지점 점검 (`harness-skeletons`, `LLVMFuzzerTestOneInput`)
- [x] adapter policy field 추가 방향 확정 (`editable_harness_relpath`, `fuzz_entrypoint_names`)
- [x] 관련 failing test 추가 및 RED 확인
- [x] profile summary → target adapter → apply safety 계층으로 policy seam 연결
- [x] custom editable harness dir / custom entrypoint guarded-apply regression 통과
- [x] `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/target_adapter.py scripts/hermes_watch_support/profile_summary.py tests/test_hermes_watch.py`
- [x] `python -m pytest tests/test_hermes_watch.py::HermesWatchTargetAdapterTests tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests -q`
- [x] `python -m pytest tests/test_hermes_watch.py -q`
- [x] `python -m pytest tests -q`
