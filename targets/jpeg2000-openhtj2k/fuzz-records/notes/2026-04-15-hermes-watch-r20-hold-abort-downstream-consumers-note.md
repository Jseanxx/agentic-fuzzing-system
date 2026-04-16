# Hermes Watch — R20 hold/abort downstream consumers v0.1

- Date: 2026-04-15
- Scope: hold review lane과 abort corrective route를 실제 refiner consumer로 연결

## 왜 이 단계가 필요한가
이전 단계까지 retry lane은 recursive chaining과 termination guard까지 붙으면서
상당히 닫힌 rail이 되었다.

반면 hold/abort는 여전히 얕았다.
- hold: `pending-review`를 manifest에 남기고 끝
- abort: `aborted`를 기록하고 끝

즉 recovery decision은 있었지만,
**hold/abort가 실제 다음 작업을 만드는 consumer는 아직 없었다.**

이 상태는 control-plane 관점에서 불균형하다.
retry는 스스로 다음 cycle로 들어가는데,
hold/abort는 단지 “멈췄다”는 표식만 남기기 때문이다.

## 이번에 붙인 것
### 1. hold lane → 실제 harness review consumer 연결
`run_harness_apply_recovery_downstream_automation(...)`가 hold를 소비하면,
이제 단순 `pending-review`만 남기지 않는다.

대신:
- `harness_review_queue.json`
- action code: `halt_and_review_harness`

로 follow-up refiner entry를 실제 enqueue한다.

즉 hold lane은 이제
**review parking**이 아니라
**기존 refiner review pipeline이 실제로 소비할 수 있는 queue 입력**이 된다.

### 2. abort lane → corrective regeneration consumer 연결
abort를 소비하면,
이제 단순 terminal status만 남기지 않는다.

대신:
- `harness_correction_regeneration_queue.json`
- action code: `regenerate_harness_correction`

로 corrective follow-up entry를 enqueue한다.

이 action은 새 refiner orchestration spec에 등록되어,
기존 refiner executor / orchestration / dispatch 흐름이 그대로 소비할 수 있다.

즉 abort lane은 이제
**막다른 terminal 기록**이 아니라
**더 안전한 correction regeneration route로 되먹이는 입력**이 된다.

### 3. follow-up lineage 기록 강화
apply candidate manifest에는 이제 다음이 남는다.
- `recovery_followup_status`
- `recovery_followup_action_code`
- `recovery_followup_registry`
- `recovery_followup_reason`
- `recovery_followup_entry_key`

즉 hold/abort가
- 어떤 후속 소비자로 연결됐는지
- 새 queue에 들어갔는지
- 이미 queue에 있었는지
를 artifact에서 추적할 수 있다.

### 4. corrective regeneration action을 refiner substrate에 편입
새 action:
- `regenerate_harness_correction`

추가 사항:
- `REFINER_QUEUE_REGISTRY_SPECS` 등록
- `REFINER_ORCHESTRATION_SPECS` 등록
- verification candidate scan 경로 등록

즉 abort corrective route는 일회성 임시 처리기가 아니라,
**기존 refiner control-plane 안에서 실행 가능한 정식 rail**이 되었다.

## 의미
이번 단계 이후 hold/abort는 이렇게 바뀐다.

### hold
- recovery queue consume
- review metadata 기록
- `harness_review_queue.json` enqueue
- 기존 harness review refiner pipeline이 후속 소비 가능

### abort
- recovery queue consume
- terminal metadata 기록
- `harness_correction_regeneration_queue.json` enqueue
- corrective regeneration refiner pipeline이 후속 소비 가능

즉 이제 recovery ecosystem은
**retry만 움직이고 hold/abort는 멈춰 있는 상태**에서,
**세 lane 모두가 실제 다음 작업을 만들 수 있는 구조**로 한 단계 더 균형을 갖는다.

## 아직 일부러 안 한 것
이번 v0.1에서도 아직 안 한 것:
- hold lane을 Discord hold channel로 직접 보내는 delivery
- abort corrective route 결과를 자동으로 새 correction policy/apply candidate로 재주입하는 chaining
- hold/abort follow-up의 priority/budget/cooldown 차등화
- patch diff touched-region/function 수준 safety 강화

즉 이번 단계는 hold/abort를 “죽은 lane”에서 꺼낸 것이지,
완전 자동 재생성 루프까지 닫은 것은 아니다.

## 냉정한 평가
좋아진 점:
- hold/abort도 이제 실제 후속 consumer를 가진다
- recovery ecosystem의 lane 불균형이 줄었다
- abort lane이 terminal-only 상태에서 corrective regeneration substrate로 진입했다
- 기존 refiner pipeline을 재사용해서 확장 비용을 낮췄다

여전히 부족한 점:
- abort corrective route는 queue 생성까지이며, 결과를 다시 apply loop로 자동 연결하지는 않는다
- hold lane은 still human/reviewer-facing 성격이 강하다
- semantic safety와 touched-region 검증은 여전히 orchestration 성숙도보다 뒤처져 있다
- retry budget/backoff/cooldown은 아직 단순하다

## 다음 단계
가장 자연스러운 다음 단계는:
- patch diff scope / touched-region safety 강화
- hold/abort follow-up 결과의 auto-reingestion 연결
- retry 운영 지능(cooldown/backoff/budget) 고도화

즉 이제는 control-plane lane 연결보다,
**실제 patch safety와 follow-up 결과 재주입 품질**을 끌어올리는 단계가 자연스럽다.
