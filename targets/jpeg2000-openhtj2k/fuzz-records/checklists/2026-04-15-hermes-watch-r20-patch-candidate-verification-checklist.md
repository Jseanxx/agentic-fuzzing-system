# Checklist — Hermes Watch R20 patch-candidate result verification / ingestion v0.1

- [x] latest succeeded apply candidate를 검증하는 함수 추가
- [x] delegate session visibility 검증 추가
- [x] delegate artifact existence 검증 추가
- [x] expected section shape 검증 추가
- [x] quality section body 검증 추가
- [x] verification 결과를 apply candidate manifest에 반영
- [x] CLI `--verify-harness-apply-candidate` 추가
- [x] TDD로 verification 테스트 추가 후 실패 확인
- [x] 구현 후 타깃 테스트 통과 확인
- [x] `tests/test_hermes_watch.py` 회귀 확인
- [x] 전체 `tests` 회귀 확인
- [x] `py_compile` 검증 확인

## 검증 명령
- `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests -q`
- `python -m pytest tests/test_hermes_watch.py -q`
- `python -m pytest tests -q`
- `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/harness_skeleton.py scripts/hermes_watch_support/__init__.py tests/test_hermes_watch.py`

## 검증 결과
- targeted class: `21 passed`
- `tests/test_hermes_watch.py`: `172 passed`
- `tests`: `191 passed`
- `py_compile`: OK
