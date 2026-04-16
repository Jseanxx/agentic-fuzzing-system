# Hermes Watch — R20 recovery queue consumption / bridge rearming v0.1

- Date: 2026-04-15
- Scope: recovery queue를 실제로 소비해 retry는 bridge rearm, hold는 review parking으로 연결

## 왜 이 단계가 필요한가
이전 단계에서 system은 recovery decision을
- `retry`
- `hold`
- `abort`
- `resolved`
로 route해서 registry/queue artifact에 올릴 수 있었다.

하지만 아직 가장 중요한 마지막 연결이 없었다.
바로:
**그 queue를 실제로 소비하는 consumer가 없었다는 점**이다.

즉 control-plane은 판단도 하고 routing도 했지만,
결국 사람이 다시 queue를 읽고 다음 action을 실행해줘야 했다.
이 상태는 “잘 정리된 반자동 시스템”이지,
진짜 자가수정 loop라고 보기엔 아직 한 끗 부족했다.

## 이번에 붙인 것
### 1. recovery queue consumer 추가
`consume_harness_apply_recovery_queue(repo_root)`를 추가했다.

현재 v0.1은 registry 우선순위를 다음처럼 소비한다.
- `harness_apply_retry_queue.json`
- `harness_apply_hold_queue.json`
- `harness_apply_abort_queue.json`
- `harness_apply_resolved.json`

즉 먼저 retry를 보고,
없으면 hold,
그 다음 abort,
마지막으로 resolved를 처리한다.

### 2. retry → bridge rearming
retry entry를 소비하면,
기존 apply candidate manifest의 `delegate_request_path`를 읽어
bridge prompt/script를 다시 생성하고
`bridge_status = armed`
상태로 되돌린다.

즉 이제 retry는 단순 상태가 아니라
**다시 launch 가능한 bridge work item**이 된다.

### 3. hold → review parking
hold entry를 소비하면,
apply candidate manifest에
- `recovery_review_status = pending-review`
- `recovery_review_lane = hold`
를 남긴다.

즉 hold는 그냥 방치되는 게 아니라
**review 대기 상태**로 명시된다.

### 4. abort / resolved baseline consumer
v0.1 기준으로:
- abort → `recovery_terminal_status = aborted`
- resolved → `recovery_resolution_status = resolved`
를 기록한다.

즉 retry/hold만 실제 동작을 조금 더 가지지만,
abort/resolved도 최소한 consumer를 갖게 되었다.

### 5. CLI consumer 추가
새 CLI:
- `--consume-harness-apply-recovery-queue`

이제 queue→consumer 경로를 명시적으로 실행할 수 있다.

## 의미
이번 단계 이후 loop는 다음처럼 바뀌었다.

- apply result
- recovery decision
- recovery routing
- recovery queue placement
- recovery queue consumption
- retry면 bridge rearm / hold면 review parking

이건 중요하다.
이제 system은
**판단 → routing → 최소 소비(action)**
까지 닫히기 시작했다.

즉 recovery queue가 더 이상 dead artifact가 아니라,
실제로 다음 phase를 준비하는 substrate가 된다.

## 아직 일부러 안 한 것
이번 v0.1에서도 아직 안 한 것:
- retry queue 소비 후 자동 launch까지 연속 실행
- hold lane을 Discord hold channel이나 별도 review queue로 자동 전달
- abort를 correction policy 재생성 / deeper refiner route로 자동 연결
- queue priority / retry budget / cool-down 같은 운영 규칙 고도화

즉 지금은 **consumer는 생겼지만, full autonomous downstream execution은 아직 아니다.**

## 냉정한 평가
좋아진 점:
- recovery queue가 실제로 소비되기 시작했다
- retry가 이제 단순 라벨이 아니라 다시 launch 가능한 armed bridge로 바뀐다
- hold도 방치가 아니라 review lane으로 명시된다

여전히 부족한 점:
- retry는 rearm까지만 되고 auto-launch는 아직 없다
- hold는 pending-review만 기록하지 실제 review consumer는 아직 없다
- abort/resolved는 여전히 기록 중심이라 action depth가 얕다
- queue 소비 우선순위도 아직 단순 고정 순서다

## 다음 단계
가장 자연스러운 다음 단계는:
- retry rearm 후 auto-launch / verify 재연결
- hold lane을 Discord hold 채널/리뷰 registry로 연결
- abort를 correction policy 재생성 또는 deeper refiner route로 연결
- patch diff touched-region safety 강화

즉 다음은:
**R20 recovery downstream automation**
또는
**R20 patch diff scope / touched-region safety**
가 자연스럽다.
