# Hermes Watch — adaptive retry / downstream budget-cooldown v0.1

- Date: 2026-04-16
- Scope: reverse-linked failure와 routing risk를 retry/downstream guard 값에 실제 반영

## 왜 이 단계가 필요한가
직전 단계에서 시스템은 reverse-linked follow-up failure를 읽고 next recovery routing을 더 보수적으로 바꿀 수 있게 됐다.
하지만 그 상태만으로는 아직 반쪽이었다.

왜냐하면 route가 `hold`나 `abort`로 바뀌지 않는 경우에도,
retry/downstream rail의 속도와 횟수는 여전히 고정값으로 움직였기 때문이다.

즉 시스템은 이제 위험을 **알긴 하지만**, 그 위험에 맞춰:
- 얼마나 오래 쉬어야 하는지
- 몇 번까지만 더 시도할지

를 아직 조절하지 못했다.

이번 단계는 그 빈칸을 채운다.
이제 reverse-linked failure / routing risk는 단순 route override 신호를 넘어서,
**retry cadence와 downstream budget 자체를 더 보수적으로 바꾸는 운영 입력**이 된다.

## 이번에 붙인 것
### 1. adaptive recursive retry cooldown
새 helper:
- `_adaptive_recursive_chain_cooldown(manifest)`

현재 정책:
- 기본 cooldown: `300s`
- `recovery_route_risk_level = high` → 최소 `900s`
- `recovery_route_risk_level = critical` 또는 `recovery_followup_failure_policy_reason = retry-budget-exhausted` → 최소 `1800s`

추가 lineage:
- `recovery_recursive_chain_cooldown_seconds`
- `recovery_recursive_chain_adaptive_reason`

즉 recursive retry rail은 이제
**최근에 critical-risk signal이 있었으면 훨씬 천천히 다시 돈다.**

### 2. adaptive downstream budget
새 helper:
- `_adaptive_downstream_chain_budget(manifest)`

현재 정책:
- 기본 budget: `2`
- `recovery_route_risk_level = high` → 최대 `1`
- `recovery_route_risk_level = critical` 또는 `retry-budget-exhausted` → 최대 `1`

추가 lineage:
- `recovery_followup_chain_budget`
- `recovery_followup_chain_adaptive_reason`

즉 downstream rail은 이제
**critical-risk 상태에서 같은 follow-up chain을 여러 번 밀어붙이지 않게 됐다.**

### 3. adaptive downstream cooldown
새 helper:
- `_adaptive_downstream_chain_cooldown(manifest)`

현재 정책은 recursive 쪽과 같은 risk tier를 사용한다.
즉 downstream rail도:
- high risk → 더 긴 cooldown
- critical risk / retry-budget-exhausted → 가장 긴 cooldown

으로 동작한다.

### 4. return payload에도 adaptive reason 노출
guard 반환 payload에 이제 필요 시:
- `adaptive_reason`

이 같이 들어간다.
즉 상위 orchestration도
**왜 이 rail이 더 길게 쉬거나 더 빨리 budget을 닫았는지** 바로 읽을 수 있다.

## 이번 TDD에서 실제 검증한 것
### 1. critical routing risk가 recursive retry cooldown을 1800초로 올리는지
manifest에:
- `recovery_route_risk_level = critical`
- `recovery_recursive_chain_checked_at = now`

를 넣고 실행했을 때:
- full-chain을 다시 호출하지 않고
- `recursive_chain_status = cooldown-active`
- `cooldown_seconds = 1800`
- `recovery_recursive_chain_adaptive_reason = critical-routing-risk`

가 남는지 확인했다.

### 2. critical routing risk가 downstream budget을 1로 낮추는지
manifest에:
- `recovery_route_risk_level = critical`
- `recovery_followup_chain_attempt_count = 1`

를 넣고 실행했을 때:
- launch를 호출하지 않고
- `downstream_chain_status = budget-exhausted`
- `downstream_budget = 1`
- `recovery_followup_chain_adaptive_reason = critical-routing-risk`

가 남는지 확인했다.

## 의미
이번 단계로 시스템은 이제:
- 실패를 기록하고
- route를 바꾸고
- 그 route risk에 따라 retry cadence와 attempt budget도 조절한다.

즉 control-plane은 한 단계 더 운영적으로 성숙해졌다.
이전까지는 “더 보수적인 route를 고르는 시스템”이었다면,
이제는 **더 보수적인 속도와 횟수로 움직이는 시스템**이 되기 시작했다.

## 아직 일부러 안 한 것
이번 v0.1에서도 아직 안 한 것:
- risk/failure class별 2단계 이상 정교한 budget tiering
- candidate quality / diff safety / semantic verifier를 합친 composite risk score
- rail별 서로 다른 adaptive curve
- downstream cooldown adaptive policy의 직접적인 회귀 테스트 보강
- reingested recursive recovery 전체에 동일 adaptive model 전파

즉 지금은 adaptive policy의 시작점이지,
아직 fully learned / deeply calibrated policy engine은 아니다.

## 냉정한 평가
좋아진 점:
- risk signal이 route뿐 아니라 cadence/budget에도 반영되기 시작했다
- critical-risk 상태에서 endless retry 성향을 더 잘 억제한다
- lineage가 계속 살아 있어 왜 guard가 더 보수적으로 바뀌었는지 읽기 쉽다

아직 부족한 점:
- 아직 coarse rule-based tiering이다
- high/critical 정도의 거친 구분에 머문다
- semantic safety나 finding quality objective와는 아직 분리돼 있다

## 다음으로 자연스러운 단계
다음은:
- **deeper semantic diff safety / corrective intent analysis**

이 가장 자연스럽다.
왜냐하면 이제 운영 guard는 많이 단단해졌고,
다음 약점은 실제 corrective apply가 얼마나 의미적으로 안전한지 더 깊게 보는 부분이기 때문이다.
