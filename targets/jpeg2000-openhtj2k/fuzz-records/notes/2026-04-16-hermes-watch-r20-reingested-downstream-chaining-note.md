# Hermes Watch — R20 reingested downstream chaining v0.1

- Date: 2026-04-16
- Scope: reingested correction-policy / apply-candidate 결과를 다시 bridge/verify/apply/reroute 쪽으로 이어붙이기

## 왜 이 단계가 필요한가
직전 단계에서 hold/abort follow-up은 verified 되면 다시 loop 입력으로 돌아가기 시작했다.
- hold review verified → correction-policy
- abort regeneration verified → apply-candidate

하지만 아직 한 번 더 끊겨 있었다.
즉 재주입은 되지만,
**그 재주입된 결과가 다시 bridge/apply rail로 자동 흘러가지는 않았다.**

이 단계는 그 다음 고리를 메운다.

## 이번에 붙인 것
### 1. reingested downstream chaining runner 추가
새 함수:
- `run_harness_apply_reingested_downstream_chaining(repo_root)`

이 함수는 내부적으로:
1. `run_harness_apply_recovery_followup_auto_reingestion(...)`
2. 필요 시 `write_harness_apply_candidate(...)`
3. `_arm_harness_apply_bridge_from_manifest(...)`
4. `launch_harness_apply_candidate_bridge(...)`
5. `verify_harness_apply_candidate_result(...)`
6. `apply_verified_harness_patch_candidate(...)`
7. `route_harness_apply_recovery(...)`

를 순서대로 이어 붙인다.

즉 이제 verified follow-up은
**다시 input으로 들어가는 것에서 끝나지 않고, 가능하면 곧바로 apply rail로 더 내려간다.**

### 2. hold reingestion의 downstream chaining
hold review verified 결과는 먼저 correction-policy로 재주입된다.
그리고 이 단계에서:
- correction-policy 기반 새 apply-candidate 생성
- 그 apply-candidate를 bridge/apply rail로 연장

한다.

즉 hold도 이제 단순 review 결과 저장이 아니라,
**review → correction-policy → apply-candidate → bridge/apply**
쪽으로 더 가까워졌다.

### 3. abort reingestion의 downstream chaining
abort corrective regeneration verified 결과는 apply-candidate로 재주입된다.
그리고 이 단계에서:
- 그 apply-candidate를 바로 arm
- launch
- verify
- apply
- reroute

까지 가능하면 계속 이어간다.

즉 abort lane도 이제
**regeneration → apply-candidate → bridge/apply/reroute**
쪽으로 실제 연쇄를 갖는다.

### 4. original apply candidate 쪽 lineage 확장
original apply candidate manifest에는 이제:
- `recovery_followup_chain_status`
- `recovery_followup_chain_apply_candidate_manifest_path`
- `recovery_followup_chain_checked_at`
- 필요 시 `recovery_followup_chain_reroute_decision`
- 필요 시 `recovery_followup_chain_reroute_action_code`

가 남는다.

즉 원래 apply candidate를 기준으로 봐도,
**verified follow-up이 다시 어떤 새 apply candidate로 이어졌고, 그 다음 reroute가 무엇이었는지** 읽을 수 있다.

### 5. CLI 추가
새 CLI:
- `--run-harness-apply-reingested-downstream-chaining`

즉 verified follow-up 재주입 + downstream chain을
한 번에 실행할 수 있다.

## 의미
이번 단계 이후 hold/abort rail은 이렇게 보인다.

### hold
- hold route
- review follow-up 생성
- review verified
- correction-policy reingestion
- apply-candidate 생성
- bridge / verify / apply / reroute 가능

### abort
- abort route
- corrective regeneration 생성
- regeneration verified
- apply-candidate reingestion
- bridge / verify / apply / reroute 가능

즉 이제 hold/abort는
단순히 retry rail의 보조 lane이 아니라,
**verified 되면 다시 apply/control-plane 실행 rail 쪽으로 복귀하는 lane**이 됐다.

## 아직 일부러 안 한 것
이번 v0.1에서도 아직 안 한 것:
- follow-up이 unverified/escalate 되었을 때 original apply candidate에 reverse linkage를 더 깊게 남기는 것
- reingested downstream chain을 recursive/budget-aware loop로 계속 반복하는 것
- correction-policy/apply-candidate 내용을 semantic하게 해석해 더 똑똑한 branching을 하는 것
- hold/abort 결과까지 포함한 full recursive recovery ecosystem

즉 지금은
**verified reingestion 이후 한 번 더 downstream rail로 이어주는 단계**까지다.

## 냉정한 평가
좋아진 점:
- reingestion이 이제 진짜 execution rail에 닿는다
- hold/abort rail이 점점 dead-end가 아니라 loop 일부로 보인다
- original apply candidate 기준 lineage가 길어졌다
- 기존 retry/full-chain 구성요소를 재활용해서 확장했다

여전히 부족한 점:
- recursive/budget-aware 후속 연쇄는 아직 없다
- follow-up failure reverse linkage는 아직 빈약하다
- semantic branching intelligence는 여전히 얕다
- 전체 recovery ecosystem이 fully self-running closed loop라고 부르기엔 아직 이르다

## 다음 단계
가장 자연스러운 다음 단계는:
- follow-up failure policy reverse linkage
- retry / reingested downstream budget/cooldown
- deeper semantic diff / corrective intent analysis

즉 이제는 verified follow-up 재주입 이후 실제 실행 rail까지 붙었으므로,
다음은 **실패한 follow-up의 역반영과 운영 지능 강화**가 핵심이다.
