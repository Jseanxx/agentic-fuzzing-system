# Hermes Watch — R20 reverse-linked follow-up failure routing integration v0.1

- Date: 2026-04-16
- Scope: reverse-linked follow-up failure를 실제 recovery routing / risk 판단에 연결

## 왜 이 단계가 필요한가
직전 단계에서 시스템은 follow-up failure를 original apply candidate lineage에 다시 남길 수 있게 됐다.
하지만 그 시점까지는 아직 **기억만 하는 상태**였다.

즉 original apply candidate가:
- 어떤 follow-up에서
- 왜 실패했고
- retry가 아니라 escalate로 끝났는지

를 알고는 있어도, 다음 recovery routing은 여전히 예전처럼 `retry / hold / abort`만 기계적으로 읽을 수 있었다.

이번 단계는 그 비대칭을 줄인다.
이제 reverse-linked follow-up failure는 더 이상 passive lineage가 아니라,
**다음 recovery route를 덜 낙관적으로 바꾸는 risk signal**이 된다.

## 이번에 붙인 것
### 1. reverse-linked follow-up escalation → retry routing override
새 helper:
- `_reverse_linked_followup_routing_adjustment(manifest, base_decision)`

동작:
- base decision이 `retry`
- 그리고 original apply candidate manifest에 `recovery_followup_failure_policy_status = escalate`

가 있으면, follow-up failure 이유를 보고 routing을 더 보수적으로 조정한다.

### 2. hold lane escalation은 retry를 hold로 강등
다음 신호가 보이면:
- `recovery_followup_failure_policy_reason = delegate-quality-gap`
- `recovery_followup_failure_policy_reason = candidate-review-required`
- 또는 `recovery_followup_failure_action_code = halt_and_review_harness`

다음 recovery routing은 더 이상 retry가 아니라:
- `hold`

로 조정된다.

의미:
**review 성격의 follow-up이 escalate됐는데도 다시 retry rail로 밀어 넣는 낙관적 루프를 줄인다.**

### 3. corrective follow-up escalation은 retry를 abort로 강등
hold 성격이 아닌 escalate follow-up은 현재 v0.1에서 보수적으로:
- `abort`

로 조정한다.

대표 예:
- `recovery_followup_failure_policy_reason = retry-budget-exhausted`
- `recovery_followup_failure_action_code = regenerate_harness_correction`

의미:
**corrective regeneration 쪽 follow-up까지 escalation됐으면, 동일 rail을 또 retry로 태우기보다 일단 terminal 쪽으로 내리는 것이 더 안전하다.**

### 4. routing risk metadata 추가
이제 recovery route entry / original apply candidate / apply result 모두에 아래가 남는다.
- `routing_risk_level`
- `routing_reverse_linkage_status`
- `routing_reverse_linkage_reason`
- manifest/result 측 lineage:
  - `recovery_route_risk_level`
  - `recovery_route_reverse_linkage_status`
  - `recovery_route_reverse_linkage_reason`

즉 이제 routing 결과를 보면,
**왜 retry가 hold/abort로 더 보수적으로 바뀌었는지**를 artifact만 봐도 읽을 수 있다.

## 이번 TDD에서 실제 검증한 것
### 1. escalated hold follow-up이 retry routing을 hold로 바꾸는지
original apply candidate manifest에:
- `recovery_followup_failure_policy_status = escalate`
- `recovery_followup_failure_policy_reason = delegate-quality-gap`
- `recovery_followup_failure_action_code = halt_and_review_harness`

를 넣고 `route_harness_apply_recovery(...)`를 실행했을 때:
- 결과 decision이 `hold`
- `routing_risk_level = high`
- route registry entry에 reverse linkage reason이 남는지 확인했다.

### 2. escalated corrective follow-up이 retry routing을 abort로 바꾸는지
original apply candidate manifest에:
- `recovery_followup_failure_policy_status = escalate`
- `recovery_followup_failure_policy_reason = retry-budget-exhausted`
- `recovery_followup_failure_action_code = regenerate_harness_correction`

를 넣고 실행했을 때:
- 결과 decision이 `abort`
- `routing_risk_level = critical`
- abort queue registry에 reverse linkage reason이 남는지 확인했다.

## 의미
이번 단계로 reverse-linked failure는 단순 회고 메모가 아니라,
**다음 route를 더 보수적으로 만드는 정책 입력**이 됐다.

즉 recovery ecosystem은 이제:
- 성공한 follow-up은 downstream rail로 이어지고
- 실패한 follow-up은 next route를 더 조심스럽게 만들며
- 둘 다 original apply candidate 중심 lineage로 남는다.

이건 control-plane이 long-horizon으로 갈수록 중요하다.
실패 기억이 routing에 반영되지 않으면,
시스템은 같은 rail을 evidence 없이 계속 낙관적으로 재시도하게 된다.

## 아직 일부러 안 한 것
이번 v0.1에서도 아직 안 한 것:
- reverse-linked failure class별 세분화된 risk scoring
- candidate quality / semantic safety / diff scope를 합친 adaptive route policy
- cooldown/budget 값을 routing risk에 따라 자동 조정
- reingested recursive recovery 전체에 동일 risk model 전파

즉 이번 단계는 **routing integration의 시작점**이지,
아직 완성된 adaptive policy engine은 아니다.

## 냉정한 평가
좋아진 점:
- failure memory가 실제 routing behavior를 바꾸기 시작했다
- retry rail의 낙관 편향이 줄었다
- 왜 hold/abort로 더 보수적으로 갔는지 artifact에 남는다

아직 부족한 점:
- risk model이 아직 rule-based다
- route override 기준이 얕고 coarse하다
- adaptive cooldown/budget까지는 연결되지 않았다

## 다음으로 자연스러운 단계
다음은:
- **adaptive retry / downstream budget-cooldown v0.1**

이 가장 자연스럽다.
즉 이제 기록된 reverse-linked failure와 routing risk를 써서:
- cooldown을 더 길게 할지
- budget를 더 빨리 닫을지
- 어떤 rail은 더 보수적으로 제한할지

를 차등화하는 단계가 이어진다.
