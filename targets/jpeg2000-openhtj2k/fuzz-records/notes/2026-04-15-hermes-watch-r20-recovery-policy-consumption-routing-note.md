# Hermes Watch — R20 recovery policy consumption / routing v0.1

- Date: 2026-04-15
- Scope: recovery decision을 queue/registry artifact로 연결해 다음 orchestration 단계가 읽을 수 있게 함

## 왜 이 단계가 필요한가
이전 단계까지 system은 apply 결과를
- `hold`
- `retry`
- `abort`
- `resolved`
로 분기할 수 있었다.

하지만 그 decision은 아직 **기록되는 상태**에 가까웠다.
즉 control-plane은 이제 더 이상 "모르지는 않지만",
그 판단을 실제 후속 동작 rail에 싣지는 못하고 있었다.

이건 중요한 한계다.
왜냐하면 recovery decision이 artifact 안에만 남고,
queue/registry/bridge 쪽으로 소비되지 않으면
실제 orchestration은 여전히 사람이 해석해줘야 하기 때문이다.

## 이번에 붙인 것
### 1. recovery routing 함수 추가
`route_harness_apply_recovery(repo_root)`를 추가했다.

이 함수는 latest apply candidate/result를 읽고
`recovery_decision`을 다음 routing spec으로 바꾼다.

현재 v0.1 매핑:
- `retry` → `requeue-guarded-apply-candidate`
- `hold` → `hold-guarded-apply-candidate`
- `abort` → `abort-guarded-apply-candidate`
- `resolved` → `resolve-guarded-apply-candidate`

### 2. queue/registry 연결
routing decision은 `fuzz-artifacts/automation/` 아래 registry로 기록된다.

현재 registry:
- `harness_apply_retry_queue.json`
- `harness_apply_hold_queue.json`
- `harness_apply_abort_queue.json`
- `harness_apply_resolved.json`

즉 이제 recovery는 단순 상태가 아니라
**후속 동작이 읽을 수 있는 queue/registry artifact**가 된다.

### 3. routing artifact 추가
별도 lineage를 위해:
- `fuzz-records/harness-apply-recovery/`
  - `*-harness-apply-recovery.json`
  - `*-harness-apply-recovery.md`
를 생성한다.

그래서 다음 단계는
- 어떤 recovery decision이 내려졌는지
- 어떤 action code로 번역됐는지
- 어느 registry에 실렸는지
- bridge channel이 필요한지
를 명시적으로 읽을 수 있다.

### 4. apply candidate / result manifest 역반영
latest apply candidate/result manifest에도:
- `recovery_route_status`
- `recovery_route_action_code`
- `recovery_route_registry`
- `recovery_route_manifest_path`
- `recovery_route_plan_path`
- `recovery_route_bridge_channel`
를 기록한다.

즉 routing이 별도 artifact에만 존재하지 않고,
원래 lifecycle artifact에서도 역추적 가능하다.

## 의미
이번 단계로 closed loop는 한 단계 더 현실적으로 변했다.

- apply result
- recovery decision
- recovery routing
- queue/registry placement

즉 이제 control-plane은
**"이 candidate를 다시 시도할지, 붙잡아 둘지, 중단할지"를 상태로만 남기지 않고,
실제 orchestration rail의 입력으로 바꾸기 시작했다.**

이건 작아 보여도 중요하다.
자가발전형 시스템에서 상태 판단과 후속 action rail이 분리되어 있으면
사람이 중간에서 계속 해석자 역할을 해야 한다.
이번 단계는 그 해석 비용을 줄이는 방향으로 나아간 것이다.

## 아직 일부러 안 한 것
이번 v0.1에서도 아직 안 한 것:
- retry queue를 실제 bridge 재실행으로 자동 연결
- hold 항목을 별도 review lane / Discord hold channel로 자동 전달
- abort 항목을 correction policy 재생성이나 deeper refiner route로 자동 연결
- routing decision에 diff class / target risk / delegate quality 추가 반영

즉 지금은 **queue 연결까진 됐지만, queue 소비 자동화는 아직 없다.**

## 냉정한 평가
좋아진 점:
- recovery decision이 실제 후속 rail에 올라가기 시작했다
- apply lifecycle이 더 이상 단순 로그가 아니라 queueable state machine에 가까워졌다
- retry/hold/abort를 서로 다른 registry로 분리해 관측성이 좋아졌다

여전히 부족한 점:
- 아직 action code만 생겼지, 그 action을 실제로 수행하는 consumer는 없다
- retry가 정말 가치 있는 retry인지, hold가 정말 review 가치가 있는 hold인지 판단은 아직 거칠다
- resolved도 단지 기록될 뿐, success quality를 더 깊게 활용하지는 못한다

## 다음 단계
가장 자연스러운 다음 단계는:
- retry queue consumer / bridge 재arming
- hold lane을 별도 review 채널/registry로 소비
- abort를 correction policy 재생성 또는 deeper route로 연결
- diff touched-region safety 강화

즉 다음은:
**R20 recovery queue consumption / bridge rearming**
또는
**R20 patch diff scope / touched-region safety**
가 자연스럽다.
