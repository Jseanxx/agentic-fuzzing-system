# Hermes Watch — R20 retry and downstream budget/cooldown v0.1

- Date: 2026-04-16
- Scope: retry recursive chain과 reingested downstream chain에 최소 budget / cooldown을 도입

## 왜 이 단계가 필요한가
지금까지 recovery/control-plane은 꽤 많이 닫혔다.
- retry recursive chain
- hold/abort follow-up reingestion
- reingested downstream chaining

하지만 실행 연쇄가 길어질수록 다른 문제가 생긴다.
바로:
**너무 자주 다시 돌거나, 충분한 근거 없이 너무 오래 반복되면 오히려 artifact만 오염시키고 상태가 꼬일 수 있다는 점**이다.

이 단계는 그걸 막기 위한 최소 운영 지능을 추가한다.
즉 지금부터는 단순히 “더 자동화”가 아니라,
**언제 멈추고, 얼마나 쉬고, 몇 번까지만 더 시도할지**를 control-plane이 알게 만드는 단계다.

## 이번에 붙인 것
### 1. retry recursive chain cooldown
새 helper:
- `_cooldown_active(last_checked_at, cooldown_seconds=...)`

`run_harness_apply_retry_recursive_chaining(...)`는 이제 latest apply candidate manifest를 보고:
- `recovery_recursive_chain_checked_at`
- `recovery_recursive_chain_cooldown_seconds` (default 300)

를 확인한다.

최근 실행 직후면:
- `recursive_chain_status = cooldown-active`
- `cycle_count = 0`

으로 반환하고 실제 full-chain을 다시 돌리지 않는다.

즉 retry recursive chain은 이제
**짧은 시간 안에 바로 재호출돼도 다시 돌기 전에 한 번 멈춘다.**

### 2. reingested downstream chain budget
`run_harness_apply_reingested_downstream_chaining(...)`는 이제 original apply candidate manifest를 보고:
- `recovery_followup_chain_budget` (default 2)
- `recovery_followup_chain_attempt_count`
- `recovery_followup_chain_checked_at`
- `recovery_followup_chain_cooldown_seconds` (default 300)

를 확인한다.

#### budget 초과 시
- `downstream_chain_status = budget-exhausted`
- bridge/launch/apply를 더 진행하지 않음

#### cooldown active 시
- `downstream_chain_status = cooldown-active`
- 바로 재실행하지 않음

즉 reingested downstream rail도 이제
**검증된 follow-up이 있다고 무한히 downstream rail을 계속 타는 구조가 아니게 됐다.**

### 3. attempt count 기록
reingested downstream chain은 실제 downstream 실행을 시도하기 전에:
- `recovery_followup_chain_attempt_count += 1`

을 기록한다.

즉 이제 original apply candidate 기준으로도
**이 follow-up chain을 몇 번 실행하려 했는지**가 남는다.

### 4. CLI exit semantics 보정
CLI 성공 조건에도 이제 추가했다.
- retry recursive chain: `cooldown-active`
- reingested downstream chain: `budget-exhausted`, `cooldown-active`

즉 이 상태들은 실패가 아니라
**의도된 운영 guard 상태**로 취급된다.

## 이번 TDD에서 실제 검증한 것
### 1. retry recursive chain cooldown
manifest에 `recovery_recursive_chain_checked_at = now`를 넣고 실행했을 때,
- 실제 full-chain을 호출하지 않고
- `recursive_chain_status = cooldown-active`
로 멈추는지 확인했다.

### 2. reingested downstream chain budget
manifest에 `recovery_followup_chain_attempt_count = 2`를 넣고 실행했을 때,
- launch를 부르지 않고
- `downstream_chain_status = budget-exhausted`
로 멈추는지 확인했다.

## 의미
이번 단계 이후 control-plane은
단순히 다음 rail을 찾는 수준을 넘어,
**너무 빨리 다시 도는 것과 너무 많이 도는 것을 최소한으로 억제**한다.

이건 사용자 질문에 대한 직접적인 답이기도 하다.
“그냥 쭉 한꺼번에 자동 진행”은 가능은 하지만,
control-plane maturity가 따라오지 않으면:
- 중복 실행
- stale evidence 소비
- endless retry
- lineage 오염

이 생기기 쉽다.

그래서 지금처럼 작은 운영 guard를 하나씩 넣는 방식이
오히려 장기적으로 덜 꼬이고 덜 부서진다.

## 아직 일부러 안 한 것
이번 v0.1에서도 아직 안 한 것:
- failure class별 budget 차등화
- candidate risk / semantic safety 수준에 따른 cooldown 차등화
- reverse-linked follow-up failure를 routing decision에 직접 반영
- reingested rail까지 포함한 full recursive recovery orchestration

즉 지금은 baseline budget/cooldown이고,
운영 지능은 아직 더 깊어질 여지가 크다.

## 냉정한 평가
좋아진 점:
- retry/downstream rail이 덜 성급해졌다
- 상태 오염과 무의미한 재실행 위험이 줄었다
- guard 상태가 artifact에 남아 운영면에서 읽기 쉬워졌다
- “한꺼번에 계속 돌리면 안 되나?”에 대한 최소한의 기술적 안전장치가 생겼다

여전히 부족한 점:
- budget/cooldown이 아직 고정값 중심이다
- target/candidate/failure-class별 차등화가 없다
- reverse-linked failure를 아직 next routing에 직접 먹이지 않는다
- fully self-running recovery ecosystem으로 가기엔 아직 운영 지능이 얕다

## 다음 단계
가장 자연스러운 다음 단계는:
- reverse-linked follow-up failure를 recovery routing에 직접 반영
- failure class / candidate risk 기반 adaptive budget-cooldown
- reingested rail까지 포함한 bounded recursive recovery loop 확장

즉 이제는 단순 loop closure보다,
**운영 판단을 더 똑똑하게 만드는 단계**가 자연스럽다.
