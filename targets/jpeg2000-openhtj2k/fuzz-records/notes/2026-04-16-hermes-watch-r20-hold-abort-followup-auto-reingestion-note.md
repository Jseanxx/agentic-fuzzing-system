# Hermes Watch — R20 hold/abort follow-up auto-reingestion v0.1

- Date: 2026-04-16
- Scope: verified hold/abort follow-up 결과를 다시 correction-policy / apply-candidate loop 입력으로 되먹이기

## 왜 이 단계가 필요한가
이전 단계까지는 hold/abort lane도 follow-up consumer를 갖게 됐다.
- hold → `halt_and_review_harness`
- abort → `regenerate_harness_correction`

하지만 아직 한 칸이 비어 있었다.
바로:
**그 follow-up이 실제로 끝나도, 그 결과가 다시 harness apply/control loop 입력으로 자동 들어오지 않는 점**이다.

즉 구조는 있었지만,
- review note가 검증돼도 correction-policy loop로 자동 복귀하지 않았고
- corrective regeneration이 검증돼도 apply-candidate loop로 자동 복귀하지 않았다.

이 단계는 그 끊긴 고리를 메우는 것이다.

## 이번에 붙인 것
### 1. follow-up auto-reingestion runner 추가
새 함수:
- `run_harness_apply_recovery_followup_auto_reingestion(repo_root)`

이 함수는 아래 registry를 본다.
- `harness_review_queue.json`
- `harness_correction_regeneration_queue.json`

조건:
- `recovery_followup_reason`이 있는 follow-up entry
- `verification_status == verified`
- 아직 `reingestion_status`가 없는 entry

즉 단순히 queue에 있는 것만이 아니라,
**검증까지 끝난 follow-up 결과만 재주입**한다.

### 2. hold review verified → correction-policy loop 재주입
`halt_and_review_harness` follow-up이 verified이면,
이제 자동으로:
- `write_harness_correction_policy(repo_root)`
를 호출한다.

즉 hold review 결과는 다시
**correction-policy layer 입력**으로 되돌아간다.

재주입 target:
- `correction-policy`

### 3. abort corrective regeneration verified → apply-candidate loop 재주입
`regenerate_harness_correction` follow-up이 verified이면,
이제 자동으로:
- `write_harness_apply_candidate(repo_root)`
를 호출한다.

즉 abort corrective follow-up은 다시
**guarded apply-candidate layer 입력**으로 되돌아간다.

재주입 target:
- `apply-candidate`

### 4. reingestion lineage 기록
follow-up registry entry에는 이제:
- `reingestion_status`
- `reingestion_target`
- `reingestion_artifact_path`
- `reingestion_checked_at`
- `reingestion_summary`

가 남는다.

그리고 원래 apply candidate manifest에도:
- `recovery_followup_reingestion_status`
- `recovery_followup_reingestion_target`
- `recovery_followup_reingestion_artifact_path`
- `recovery_followup_reingestion_action_code`
- `recovery_followup_reingestion_checked_at`
- `recovery_followup_verification_status`
- `recovery_followup_verification_summary`

가 남는다.

즉 이제는
**follow-up이 어떤 rail로 다시 흘러 들어갔는지**를 apply candidate 쪽에서 바로 추적할 수 있다.

### 5. CLI 추가
새 CLI:
- `--run-harness-apply-recovery-followup-auto-reingestion`

즉 hold/abort follow-up verified 결과를
명시적으로 한 번씩 재주입하는 runner가 생겼다.

## 의미
이번 단계 이후 흐름은 이렇게 된다.

### hold lane
- hold route
- review follow-up queue 생성
- review follow-up 실행/검증
- verified면 correction-policy loop로 재주입

### abort lane
- abort route
- corrective regeneration queue 생성
- regeneration follow-up 실행/검증
- verified면 apply-candidate loop로 재주입

즉 hold/abort는 이제
단순 follow-up 생성에서 끝나는 것이 아니라,
**verified follow-up 결과를 다시 harness control plane에 되먹이는 rail**이 되었다.

## 아직 일부러 안 한 것
이번 v0.1에서도 아직 안 한 것:
- unverified follow-up failure policy 결과를 apply candidate 쪽에 자동 역반영하는 것
- correction-policy/apply-candidate 이후 bridge launch까지 연쇄 자동 실행하는 것
- reingested 결과가 실제 build/smoke/apply success로 이어졌는지 end-to-end chaining
- follow-up artifact 내용을 semantic하게 읽어 patch intent를 재구성하는 것

즉 지금은
**verified follow-up 결과를 다음 loop 입력으로 다시 넣는 단계**까지고,
그 다음 실행 연쇄까지 full auto는 아니다.

## 냉정한 평가
좋아진 점:
- hold/abort rail이 이제 진짜 loop 일부처럼 보이기 시작했다
- review와 corrective regeneration이 dead-end artifact가 아니라 next input이 됐다
- apply candidate manifest 기준 lineage가 더 길고 명확해졌다
- 재주입이 verified 결과에만 걸려 있어 비교적 보수적이다

여전히 부족한 점:
- reingestion은 아직 1-hop이다
- follow-up failure policy의 역반영은 없다
- reingested artifact가 실제로 더 좋은 patch/apply 성공으로 이어지는지는 아직 별도 문제다
- follow-up 내용을 semantic하게 해석하지 않고, 현재는 검증 완료 사실 자체를 트리거로 쓴다

## 다음 단계
가장 자연스러운 다음 단계는:
- reingested correction-policy/apply-candidate 이후 bridge/apply까지 연쇄 자동화
- follow-up failure policy를 original apply candidate lineage로 역반영
- retry cooldown/backoff/budget 고도화

즉 이제는 hold/abort follow-up도 다시 loop 입력으로 돌아오므로,
다음은 **그 재주입 이후 실제 실행 연쇄를 얼마나 더 자동으로 닫을지**가 핵심이다.
