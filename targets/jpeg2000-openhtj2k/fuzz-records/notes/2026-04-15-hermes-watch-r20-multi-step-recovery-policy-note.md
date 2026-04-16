# Hermes Watch — R20 multi-step recovery policy v0.1

- Date: 2026-04-15
- Scope: guarded apply 이후 결과를 `retry / hold / abort / resolved`로 나누는 최소 recovery policy 추가

## 왜 이 단계가 필요한가
이전 단계까지 system은:
- pre-apply semantics / diff safety guardrail
- limited apply
- build/smoke rerun
- failure 시 rollback
까지 수행할 수 있었다.

하지만 아직 중요한 빈칸이 있었다.
바로:
**실패하거나 차단된 뒤 그 다음 액션을 구조적으로 구분하지 못했다는 점**이다.

이 상태에서는 artifact는 많이 남지만,
control-plane 입장에서는
- 그냥 한번 더 해볼 failure
- 당분간 보류해야 할 blocked apply
- 더 이상 같은 rail에서 반복하면 안 되는 repeated failure
를 같은 수준으로 다루게 된다.

## 이번에 붙인 것
### 1. recovery decision layer
`apply_verified_harness_patch_candidate(...)`가 이제 apply 결과를 바탕으로
다음 recovery decision을 계산한다.

현재 v0.1 규칙:
- `blocked` + pre-apply guardrail → `hold`
- `applied` 성공 → `resolved`
- `rolled_back` 첫 실패 → `retry`
- `rolled_back` 연속 실패 2회째 이상 → `abort`

즉 이제는 rollback 자체보다 한 단계 위에서
**“이 상태를 다음에 어떻게 소비해야 하는가”**를 artifact에 남긴다.

### 2. recovery streak / attempt metadata
manifest와 result artifact에 다음을 남긴다.
- `recovery_decision`
- `recovery_summary`
- `recovery_failure_streak`
- `recovery_attempt_count`
- `recovery_status`
- 필요 시 `recovery_last_build_status`, `recovery_last_smoke_status`

그래서 다음 단계는 단순 apply 결과뿐 아니라
해당 candidate가 지금
- 재시도 가능한지
- 보류해야 하는지
- 해당 rail에서 중단해야 하는지
를 바로 읽을 수 있다.

### 3. blocked / rolled_back / success 모두 lineage화
이번 단계는 실패한 경우만 다루는 게 아니다.
성공도 `resolved`, blocked도 `hold`로 명시한다.

이게 중요한 이유는,
recovery policy는 “실패 처리기”라기보다
**apply lifecycle state를 더 작은 상태 머신으로 바꾸는 층**이기 때문이다.

## 의미
이번 단계 이후 loop는 다음처럼 바뀌었다.

- verified patch-candidate
- semantics / diff safety guardrail
- limited apply
- build/smoke rerun
- rollback
- recovery decision (`retry / hold / abort / resolved`)

즉 이제는 단순히 원복하는 수준이 아니라,
**원복/차단 결과를 다음 orchestration action으로 번역하는 최소 policy layer**가 생겼다.

## 아직 일부러 안 한 것
이번 v0.1에서도 아직 안 한 것:
- build failure와 smoke failure를 더 세밀하게 다른 recovery class로 분리
- failure streak 외에 diff class / target risk / delegate quality를 함께 반영
- 자동 retry scheduler 재등록
- hold 항목을 별도 queue/channel로 승격
- abort 이후 자동 correction policy 재생성

즉 지금 정책은 유용하지만 아직 단순하다.

## 냉정한 평가
좋아진 점:
- apply 결과가 이제 다음 액션 의미를 가진다
- repeated failure를 같은 rail에서 무한 반복할 위험을 조금 줄였다
- blocked / rollback / success가 모두 상태 머신의 일부로 정리되기 시작했다

여전히 부족한 점:
- recovery policy가 여전히 coarse하다
- first failure는 거의 무조건 `retry`, second failure는 거의 무조건 `abort`라서 맥락 감도가 낮다
- build fail과 smoke fail, semantic block, delegate quality 문제를 충분히 세분화하진 못한다

## 다음 단계
가장 자연스러운 다음 단계는:
- `retry / hold / abort`를 실제 queue/registry 동작으로 연결
- touched-region / function / whitelist 기반 diff safety 강화
- smoke failure 유형을 build failure와 분리한 recovery policy 세분화

즉 다음은:
**R20 recovery policy consumption / routing**
또는
**R20 patch diff scope / touched-region safety**
가 자연스럽다.
