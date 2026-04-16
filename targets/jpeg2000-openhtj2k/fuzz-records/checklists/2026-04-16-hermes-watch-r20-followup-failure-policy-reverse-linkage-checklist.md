# Checklist — Hermes Watch R20 follow-up failure policy reverse linkage v0.1

- [x] follow-up verification failure policy가 original apply candidate manifest를 역갱신하도록 연결
- [x] retry decision reverse linkage 기록 추가
- [x] escalate decision reverse linkage 기록 추가
- [x] reverse linkage artifact path를 function return payload에 노출
- [x] TDD로 follow-up retry reverse linkage 테스트 추가 후 실패 확인
- [x] TDD로 follow-up escalation reverse linkage 테스트 추가 후 실패 확인
- [x] targeted reverse linkage tests 통과 확인
- [x] `tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests` 회귀 확인
- [x] `tests/test_hermes_watch.py` 회귀 확인
- [x] 전체 `tests` 회귀 확인
- [x] `py_compile` 검증 확인

## 검증 명령
- `python -m pytest tests/test_hermes_watch.py::HermesWatchRefinerRetryEscalationTests::test_apply_verification_failure_policy_records_reverse_linkage_for_followup_retry tests/test_hermes_watch.py::HermesWatchRefinerRetryEscalationTests::test_apply_verification_failure_policy_records_reverse_linkage_for_followup_escalation -q`
- `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests -q`
- `python -m pytest tests/test_hermes_watch.py -q`
- `python -m pytest tests -q`
- `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/harness_skeleton.py scripts/hermes_watch_support/__init__.py tests/test_hermes_watch.py`

## 검증 결과
- targeted reverse linkage tests: `2 passed`
- targeted class: `51 passed`
- `tests/test_hermes_watch.py`: `205 passed`
- `tests`: `224 passed`
- `py_compile`: OK
