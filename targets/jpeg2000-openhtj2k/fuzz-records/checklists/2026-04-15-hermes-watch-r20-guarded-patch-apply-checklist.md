# Checklist — Hermes Watch R20 guarded patch apply + build/smoke rerun v0.1

- [x] latest verified apply candidate를 제한적으로 적용하는 함수 추가
- [x] `comment-only` patch injection 추가
- [x] `guard-only` min-size guard injection 추가
- [x] build probe rerun 추가
- [x] smoke probe rerun 추가
- [x] `harness-apply-results/` result artifact 추가
- [x] apply result를 apply candidate manifest에 다시 기록
- [x] CLI `--apply-verified-harness-patch-candidate` 추가
- [x] TDD로 apply/rerun 테스트 추가 후 실패 확인
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
- targeted class: `24 passed`
- `tests/test_hermes_watch.py`: `175 passed`
- `tests`: `194 passed`
- `py_compile`: OK
