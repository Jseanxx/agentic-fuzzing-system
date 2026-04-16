# Checklist — comment-only / broader corrective intent analysis v0.1

- [x] `comment-only`에서 실제 코드 mutation 의도를 요구하는 summary 케이스 선정
- [x] failing test 2개로 RED 확인
- [x] `comment-only` semantic intent guardrail 최소 구현
- [x] blocked return payload에 semantics summary/reasons 노출
- [x] happy-path `comment-only` apply regression 확인
- [x] `python -m py_compile scripts/hermes_watch.py tests/test_hermes_watch.py`
- [x] `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests -q`
- [x] `python -m pytest tests/test_hermes_watch.py -q`
- [x] `python -m pytest tests -q`
