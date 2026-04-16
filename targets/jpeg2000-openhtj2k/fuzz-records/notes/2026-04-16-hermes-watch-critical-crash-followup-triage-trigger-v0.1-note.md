# Hermes Watch Critical Crash Follow-up Triage Trigger v0.1

- Date: 2026-04-16 20:18:07 KST
- Scope: `scripts/hermes_watch.py`, `tests/test_hermes_watch.py`

## 왜 이 단계가 필요했나
방금 시스템은 `continue_and_prioritize_triage` 같은 deep-stage critical crash policy를 계산할 수는 있었지만,
실제 후속 실행 trigger는 `fix-build-before-fuzzing`, `promote-seed-to-regression-and-triage` 두 경우에만 걸려 있었다.

즉 보고서에는 "triage 우선"이라고 쓰면서도,
실제 제어면은 그 crash를 triage mode 실행으로 넘기지 못했다.
이건 true north 기준으로 보면 `artifact -> trigger -> rerun` 고리가 policy 문자열에서 끊긴 상태였다.

## root cause
1. `should_trigger_regression(...)`가 crash follow-up action code를 인식하지 않았다.
2. follow-up trigger command가 항상 `run-fuzz-mode.sh regression`으로 고정되어 있었다.
3. trigger executor는 `current_mode == regression`만 special-case skip해서, triage command를 큐에 넣더라도 같은 mode 중복 실행을 막지 못했다.

## 이번에 바꾼 것
- `scripts/hermes_watch.py`
  - `continue_and_prioritize_triage`, `high_priority_alert`도 follow-up trigger 대상으로 포함
  - `followup_trigger_command(...)` 추가
    - deep critical crash follow-up은 `bash scripts/run-fuzz-mode.sh triage`
    - build/smoke regression 계열은 기존처럼 `... regression`
  - trigger priority에 deep crash triage lane 우선순위 반영
  - trigger executor가 command target mode를 읽어 `skipped-already-in-<mode>`로 일반화
- `tests/test_hermes_watch.py`
  - `continue_and_prioritize_triage`가 실제 trigger 대상임을 검증
  - triage command가 이미 triage mode일 때 중복 실행을 막는 regression test 추가
  - critical crash policy action이 triage trigger를 기록하고 auto-run까지 호출하는지 검증

## 의미
이 단계는 문구 수정이 아니다.
critical deep-stage crash를 잡았을 때,
이제 watcher가 실제로 triage follow-up rail을 자동으로 밟을 수 있게 만드는 제어면 복구다.

즉 `정책 판단`과 `후속 실행`이 다시 연결됐다.

## 검증
- RED
  - `pytest -q tests/test_hermes_watch.py -k 'continue_and_prioritize_triage or already_in_triage_mode_for_triage_command or critical_crash_triage_trigger'`
  - 초기 3개 실패 확인
- GREEN
  - 같은 명령 재실행: 3 passed
- 회귀
  - `pytest -q tests/test_hermes_watch.py`
  - `pytest -q`
- 동작 확인
  - temp sandbox에서 `apply_policy_action(...)` 호출 결과
    - `updated = [policy_log, regression_trigger, regression_auto_run]`
    - trigger command = `bash scripts/run-fuzz-mode.sh triage`
    - registry status = `completed`
- 현장 bounded rerun
  - `python scripts/hermes_watch.py --repo /home/hermes/work/fuzzing-jpeg2000 --max-total-time 5 --no-progress-seconds 30`
  - latest duplicate는 `record-duplicate-crash`라 새 triage trigger까지는 가지 않았지만,
    동일 family 재재현(`j2kmarkers.cpp:52`)과 duplicate classification은 유지됨

## 아직 남은 것
1. `high_priority_alert` path도 실제 live run artifact에서 밟히는지 확인 필요
2. triage run 결과가 LLM evidence/revision lane으로 얼마나 잘 닫히는지 추가 확인 필요
3. duplicate crash의 경우에도 triage replay/minimization이 필요하면 별도 follow-up rail을 둘지 판단 필요
