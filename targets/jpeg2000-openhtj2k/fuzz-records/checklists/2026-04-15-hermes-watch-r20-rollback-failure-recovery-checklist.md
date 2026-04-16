# Checklist — Hermes Watch R20 rollback / failure recovery v0.1

- [x] pre-apply backup artifact 추가
- [x] build failure 시 target file restore 추가
- [x] smoke failure 시 target file restore 추가
- [x] `rollback_status` 기록 추가
- [x] `backup_path` 기록 추가
- [x] rollback 결과를 apply candidate/result artifact에 반영
- [x] TDD로 rollback failure 테스트 추가 후 실패 확인
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
- targeted class: `25 passed`
- `tests/test_hermes_watch.py`: `176 passed`
- `tests`: `195 passed`
- `py_compile`: OK
