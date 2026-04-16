# Hermes Watch — R20 follow-up failure policy reverse linkage v0.1

- Date: 2026-04-16
- Scope: unverified / escalated follow-up 결과를 original apply candidate lineage에 다시 되먹이기

## 왜 이 단계가 필요한가
직전 단계까지는 verified follow-up이 다시 execution rail로 잘 들어가기 시작했다.
- verified hold/abort follow-up → reingestion
- reingested result → downstream chaining

하지만 실패한 follow-up 쪽은 여전히 약했다.
즉:
- follow-up verification이 실패하거나
- policy가 retry/escalate를 결정해도

그 사실이 original apply candidate manifest에 충분히 역반영되지 않았다.

이 단계는 그 비대칭을 줄인다.
성공한 follow-up뿐 아니라,
**실패한 follow-up policy 결과도 원래 apply candidate 쪽에서 보이게 만드는 단계**다.

## 이번에 붙인 것
### 1. verification failure policy의 reverse linkage 추가
`apply_verification_failure_policy(...)`가 이제 follow-up entry를 처리할 때,
아래 조건이면 original apply candidate manifest를 갱신한다.
- `recovery_followup_reason` 존재
- `apply_candidate_manifest_path` 존재
- 해당 manifest 파일 존재

즉 recovery follow-up에서 파생된 verification failure policy만
reverse linkage 대상이 된다.

### 2. original apply candidate에 남기는 정보
이제 original apply candidate manifest에는 다음이 기록된다.
- `recovery_followup_failure_policy_status`
- `recovery_followup_failure_policy_reason`
- `recovery_followup_failure_action_code`
- `recovery_followup_failure_summary`
- `recovery_followup_failure_artifact_path`
- `recovery_followup_failure_checked_at`
- `recovery_followup_failure_registry`
- `recovery_followup_failure_entry_key`

즉 원래 apply candidate를 보면,
**어떤 follow-up이 실패했고, policy가 retry인지 escalate인지, 왜 그렇게 판단했는지**를 바로 읽을 수 있다.

### 3. retry / escalate 양쪽 모두 역반영
이번 단계는 특정 한쪽만 다루지 않는다.
- follow-up failure policy가 `retry`면 그 retry decision과 reason을 기록
- follow-up failure policy가 `escalate`면 escalate decision과 reason을 기록

즉 reverse linkage는
**follow-up failure policy outcome 전체를 original apply candidate에 되먹이는 최소 기록층**이다.

### 4. 함수 반환에도 reverse linkage 결과 노출
`apply_verification_failure_policy(...)` return payload에:
- `reverse_linked_apply_candidate_manifest_path`

를 추가했다.

즉 CLI/상위 orchestration에서도
reverse linkage가 어느 manifest에 반영됐는지 읽을 수 있다.

## 의미
이번 단계 이후에는
- 성공한 follow-up은 downstream chaining으로 다시 rail에 들어가고
- 실패한 follow-up도 original apply candidate lineage에 되돌아간다.

즉 original apply candidate 기준으로 보면 이제:
- follow-up 생성
- follow-up 검증 성공/실패
- verified reingestion/chaining
- unverified retry/escalate reason

까지 한쪽에서 점점 보이게 된다.

이건 중요하다.
왜냐하면 semi-autonomous system에서는
**성공한 경로만이 아니라, 실패한 경로도 다음 판단의 입력이 되어야 하기 때문**이다.

## 아직 일부러 안 한 것
이번 v0.1에서도 아직 안 한 것:
- reverse-linked failure 결과를 recovery routing/budget에 직접 반영하는 것
- original apply candidate score/risk를 follow-up failure에 따라 자동 갱신하는 것
- repeated follow-up failure를 별도 terminal/hold lane으로 승격하는 것
- reverse linkage 결과를 retry recursive chain 쪽 의사결정에 직접 통합하는 것

즉 지금은
**실패 정보를 기록/역반영하는 단계**까지고,
그 실패를 다음 policy weighting에 깊게 먹이는 건 다음 단계다.

## 냉정한 평가
좋아진 점:
- 성공한 follow-up과 실패한 follow-up의 비대칭이 줄었다
- original apply candidate 기준 lineage가 더 완결적이 됐다
- retry/escalate reason이 apply candidate 쪽에서 바로 보인다
- 상위 orchestration이 reverse linkage 결과를 다시 활용할 발판이 생겼다

여전히 부족한 점:
- 아직 기록층이다
- reverse linkage가 scheduling/budget/risk weighting에 자동 연결되진 않는다
- failure class taxonomy는 여전히 얕다
- recursive recovery policy가 이 reverse linkage를 아직 적극 활용하지 않는다

## 다음 단계
가장 자연스러운 다음 단계는:
- retry / reingested downstream budget/cooldown 강화
- reverse-linked follow-up failure를 recovery routing에 직접 반영
- deeper semantic corrective intent analysis

즉 이제는 성공/실패 모두 apply candidate lineage에 보이기 시작했으므로,
다음은 **그 정보를 실제 운영 지능으로 바꾸는 단계**가 자연스럽다.
