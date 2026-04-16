# Checklist — Hermes Watch R20 guarded apply delegate consumption v0.1

- [x] latest guarded apply candidate manifest 선택 helper 추가
- [x] apply candidate bridge prompt/script 생성 함수 추가
- [x] apply candidate bridge launch 함수 추가
- [x] delegate session/artifact metadata를 apply candidate manifest에 반영
- [x] CLI `--bridge-harness-apply-candidate` 추가
- [x] CLI `--launch-harness-apply-candidate` 추가
- [x] TDD로 bridge/launch 테스트 추가 후 실패 확인
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
- targeted class: `18 passed`
- `tests/test_hermes_watch.py`: `169 passed`
- `tests`: `188 passed`
- `py_compile`: OK
