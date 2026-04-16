# Checklist — multi-target adapter generalization v0.1

- [x] OpenHTJ2K fallback-only target adapter selection 한계 확인
- [x] target profile에서 adapter spec을 summary로 끌어올릴 seam 추가
- [x] `get_target_adapter(...)`가 custom adapter spec을 실제 adapter로 해석하도록 구현
- [x] custom adapter unit test 추가 및 RED 확인
- [x] main smoke-success/final-summary E2E test 추가 및 RED 확인
- [x] 최소 구현으로 GREEN 달성
- [x] `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/profile_summary.py scripts/hermes_watch_support/target_adapter.py tests/test_hermes_watch.py`
- [x] `python -m pytest tests/test_hermes_watch.py::HermesWatchTargetAdapterTests -q`
- [x] `python -m pytest tests/test_hermes_watch.py -q`
- [x] `python -m pytest tests -q`
