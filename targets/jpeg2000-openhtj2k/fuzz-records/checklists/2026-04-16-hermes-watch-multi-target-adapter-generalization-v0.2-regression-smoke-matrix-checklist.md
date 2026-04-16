# Checklist — multi-target adapter generalization v0.2 regression smoke matrix slice

- [x] target adapter contract를 한 장으로 점검할 matrix 필요성 확인
- [x] matrix helper 관련 failing test 추가 및 RED 확인
- [x] adapter command/policy expectation matrix helper 추가
- [x] runtime default profile을 읽는 matrix writer helper 추가
- [x] matrix json/markdown artifact 생성 검증
- [x] `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/target_adapter.py tests/test_hermes_watch.py`
- [x] `python -m pytest tests/test_hermes_watch.py::HermesWatchTargetAdapterTests -q`
- [x] `python -m pytest tests/test_hermes_watch.py -q`
- [x] `python -m pytest tests -q`
