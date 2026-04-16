# Hermes Watch — R20 recovery downstream automation v0.1

- Date: 2026-04-15
- Scope: rearmed retry를 bridge launch + verification까지 이어 붙여 recovery downstream을 더 닫음

## 왜 이 단계가 필요한가
이전 단계에서 system은 recovery queue를 실제로 소비할 수 있게 되었다.
즉:
- retry → bridge rearm
- hold → review parking
까지 연결됐다.

하지만 아직 한 걸음이 남아 있었다.
바로:
**retry가 다시 준비되기만 하고, 실제로 launch/verify까지 자동으로 이어지지 않았다는 점**이다.

이 상태는 꽤 좋아졌지만,
냉정하게 보면 아직 “rearmed work item을 사람이 다시 눌러줘야 하는” 반자동 상태였다.

## 이번에 붙인 것
### 1. recovery downstream automation 함수 추가
`run_harness_apply_recovery_downstream_automation(repo_root)`를 추가했다.

이 함수는:
1. recovery queue를 먼저 consume하고
2. retry인 경우 bridge가 rearmed 되면
3. 곧바로 bridge launch를 실행하고
4. launch 성공 시 verify까지 이어서 수행한다.

즉 이제 retry lane은:
- queue
- consume
- rearm
- launch
- verify
까지 한 번에 이어질 수 있다.

### 2. downstream status lineage
apply candidate manifest에 다음 downstream 상태를 기록한다.
- `recovery_downstream_status`
- `recovery_downstream_checked_at`
- 필요 시
  - `recovery_downstream_launch_status`
  - `recovery_downstream_verification_status`
  - `recovery_downstream_verification_summary`

즉 downstream automation도 artifact로 역추적 가능하다.

### 3. CLI 추가
새 CLI:
- `--run-harness-apply-recovery-downstream-automation`

이제 recovery queue 소비와 retry downstream action을 한 번에 실행할 수 있다.

## 의미
이번 단계 이후 retry rail은 다음처럼 닫힌다.

- recovery decision = retry
- recovery routing
- retry queue placement
- retry queue consumption
- bridge rearm
- bridge launch
- verify

즉 이제 system은 최소한 retry lane에 대해
**판단 → routing → consume → prepare → execute → verify**
까지 이어지기 시작했다.

이건 중요한 진전이다.
여기까지 오면 retry downstream은 더 이상 dead-end queue가 아니라,
실제로 다시 움직이는 rail이 된다.

## 아직 일부러 안 한 것
이번 v0.1에서도 아직 안 한 것:
- verify 이후 apply/recovery 재판단까지 한 번에 자동 연쇄 실행
- hold lane의 실제 review consumer / Discord hold channel 연결
- abort lane의 correction policy regeneration / deeper refiner route 자동 연결
- retry downstream의 retry budget / cooldown / launch backoff 고도화

즉 지금은 retry lane이 가장 많이 닫혔지만,
전체 recovery ecosystem이 완전 자동은 아니다.

## 냉정한 평가
좋아진 점:
- retry lane은 이제 실제로 다시 달린다
- control-plane이 단순 orchestration 기록을 넘어 재실행 rail을 갖기 시작했다
- launch/verify까지 이어지면서 self-revision loop의 실행감이 커졌다

여전히 부족한 점:
- verify 이후 다음 apply/recovery cycle까지는 아직 수동 연결이 남아 있다
- hold는 여전히 review parking만 있고 실제 review consumer는 없다
- abort도 terminal 기록은 되지만 더 깊은 corrective route는 없다
- retry lane에 쿨다운/예산/우선순위 같은 운영 지능은 아직 약하다

## 다음 단계
가장 자연스러운 다음 단계는:
- verify 이후 next-route / next-apply까지 재연결
- hold lane을 Discord hold channel / review registry consumer로 연결
- abort lane을 correction regeneration 또는 deeper route로 연결
- patch diff touched-region safety 강화

즉 다음은:
**R20 recovery full closed-loop chaining**
또는
**R20 patch diff scope / touched-region safety**
가 자연스럽다.
