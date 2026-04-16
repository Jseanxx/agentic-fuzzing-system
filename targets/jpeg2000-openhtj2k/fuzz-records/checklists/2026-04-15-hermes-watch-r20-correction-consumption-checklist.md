# Checklist — Hermes Watch R20 correction-consumption / apply policy v0.1

- [x] latest correction draft를 읽는 helper 추가
- [x] latest skeleton closure evidence를 읽어 correction consumption payload 생성
- [x] `decision`, `disposition`, `apply_policy` 필드 도입
- [x] 실패 closure일 때 reviewable correction 승격 정책 추가
- [x] 성공 closure일 때 `hold-no-change` 정책 추가
- [x] `fuzz-records/harness-correction-policies/` artifact 계층 추가
- [x] markdown에 `Consumption Decision` section 추가
- [x] CLI `--decide-harness-correction-policy` 추가
- [x] TDD로 새 테스트 추가 후 실패 확인
- [x] 구현 후 타깃 테스트 통과 확인
- [x] 전체 `tests/test_hermes_watch.py` 회귀 확인
- [x] 전체 `tests` 회귀 확인
- [x] `py_compile` 검증 확인

## 검증 명령
- `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests -q`
- `python -m pytest tests/test_hermes_watch.py -q`
- `python -m pytest tests -q`
- `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/harness_skeleton.py scripts/hermes_watch_support/__init__.py tests/test_hermes_watch.py`

## 검증 결과
- targeted class: `12 passed`
- `tests/test_hermes_watch.py`: `163 passed`
- `tests`: `182 passed`
- `py_compile`: OK
