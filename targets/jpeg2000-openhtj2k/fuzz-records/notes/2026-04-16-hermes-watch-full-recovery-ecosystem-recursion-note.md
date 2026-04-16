# Note — full recovery ecosystem recursion v0.1

- Date: 2026-04-16 06:39:41 KST
- Scope: `scripts/hermes_watch.py`, `tests/test_hermes_watch.py`

## 이번 단계에서 한 일
- `run_harness_apply_recovery_ecosystem_recursion(repo_root, max_rounds=4)`를 추가했다.
- retry recursive lane과 reingested downstream lane을 한 함수에서 라운드 단위로 오케스트레이션하도록 묶었다.
- reverse-linked follow-up escalation / queued follow-up / reingested follow-up 상태가 보이면 lane priority를 `downstream -> retry`로 바꾸도록 했다.
- 각 라운드마다 아래 lineage를 original apply candidate manifest에 기록하도록 했다.
  - `recovery_ecosystem_status`
  - `recovery_ecosystem_stop_reason`
  - `recovery_ecosystem_round_count`
  - `recovery_ecosystem_last_lane`
  - `recovery_ecosystem_lane_sequence`
  - `recovery_ecosystem_checked_at`

## 왜 의미가 있나
기존에는 retry recursive chain과 reingested downstream chain이 각각은 존재했지만,
둘을 같은 bounded recursion 관점에서 읽는 상위 orchestration은 비어 있었다.
이번 단계로 최소한 다음이 가능해졌다.

1. reverse-linked follow-up escalation이 남아 있으면 재시도 lane을 무조건 먼저 보는 대신 downstream/reingestion rail을 우선 본다.
2. retry lane이 `hold`/`abort`로 멈춘 뒤에도 다음 라운드에서 downstream lane으로 넘어가 closure를 계속 시도할 수 있다.
3. "왜 멈췄는지"를 `no-eligible-lane`, `retry-lane-*`, `downstream-lane-*`, `ecosystem-round-budget-exhausted` 같은 stop reason taxonomy로 남긴다.

## 아직 얕은 점
- 아직 CLI entrypoint는 붙이지 않았다. 현재는 Python 함수 레벨 orchestration이다.
- retry/downstream lane 사이의 budget/cooldown을 하나의 unified policy object로 승격한 것은 아니다.
- follow-up verification이 아직 안 끝난 상태에서는 `no-eligible-lane`으로 멈추므로, 완전 자율적인 장시간 재호출 스케줄링까지 닫힌 것은 아니다.

## 검증
- RED
  - 새 테스트 3개 추가 후 `AttributeError`로 실패 확인
- GREEN / regression
  - `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_run_harness_apply_recovery_ecosystem_recursion_prefers_downstream_lane_after_followup_escalation tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_run_harness_apply_recovery_ecosystem_recursion_crosses_from_retry_into_downstream_lane tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_run_harness_apply_recovery_ecosystem_recursion_stops_at_round_budget -q`
  - `python -m py_compile scripts/hermes_watch.py tests/test_hermes_watch.py`
  - `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests -q`
  - `python -m pytest tests/test_hermes_watch.py -q`
  - `python -m pytest tests -q`

## 냉정한 평가
이건 "full autonomy 완성"이 아니라,
기존에 흩어져 있던 retry recursion과 reingested rail을 같은 bounded ecosystem으로 읽기 시작한 v0.1이다.
그래도 이제 control-plane은 개별 rail들의 존재를 넘어,
rail 간 전환과 정지 이유를 하나의 artifact-first lineage로 남길 수 있게 됐다.
