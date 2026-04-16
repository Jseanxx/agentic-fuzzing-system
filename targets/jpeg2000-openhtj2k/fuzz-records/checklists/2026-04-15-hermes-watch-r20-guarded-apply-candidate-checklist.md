# Checklist — Hermes Watch R20 guarded apply candidate generation v0.1

- [x] latest correction policy를 읽는 helper 추가
- [x] guarded apply candidate payload/markdown 렌더링 추가
- [x] `fuzz-records/harness-apply-candidates/` artifact 계층 추가
- [x] promoted correction policy일 때 optional delegate request JSON 생성
- [x] `smoke-fix -> guard-only`, `build-fix -> comment-only` scope 분류 추가
- [x] CLI `--prepare-harness-apply-candidate` 추가
- [x] TDD로 apply candidate 테스트 추가 후 실패 확인
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
- targeted class: `15 passed`
- `tests/test_hermes_watch.py`: `166 passed`
- `tests`: `185 passed`
- `py_compile`: OK
