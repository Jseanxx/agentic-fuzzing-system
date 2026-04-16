# Checklist — Hermes Watch R20 reverse-linked follow-up failure routing integration v0.1

- [x] reverse-linked follow-up escalation을 읽는 routing helper 추가
- [x] escalated hold follow-up이 retry routing을 hold로 override하도록 연결
- [x] escalated corrective follow-up이 retry routing을 abort로 override하도록 연결
- [x] recovery route entry에 risk / reverse linkage metadata 기록 추가
- [x] apply candidate manifest와 apply result에 recovery route risk metadata 반영
- [x] TDD로 hold-side reverse linkage routing override 테스트 추가 후 실패 확인
- [x] TDD로 abort-side reverse linkage routing override 테스트 추가 후 실패 확인
- [x] targeted routing integration tests 통과 확인
- [x] `tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests` 회귀 확인
- [x] `tests/test_hermes_watch.py` 회귀 확인
- [x] 전체 `tests` 회귀 확인
- [x] `py_compile` 검증 확인

## 검증 명령
- `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_route_harness_apply_recovery_escalated_hold_followup_overrides_retry_routing tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_route_harness_apply_recovery_escalated_abort_followup_overrides_retry_routing -q`
- `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests -q`
- `python -m pytest tests/test_hermes_watch.py -q`
- `python -m pytest tests -q`
- `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/harness_skeleton.py scripts/hermes_watch_support/__init__.py tests/test_hermes_watch.py`

## 검증 결과
- targeted routing integration tests: `2 passed`
- targeted class: `55 passed`
- `tests/test_hermes_watch.py`: `209 passed`
- `tests`: `228 passed`
- `py_compile`: OK
