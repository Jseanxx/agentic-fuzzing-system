# Hermes Watch — R20 rollback / failure recovery v0.1

- Date: 2026-04-15
- Scope: limited patch apply 실패 시 backup에서 원본 target file을 복구하고 rollback 상태를 artifact로 남김

## 왜 이 단계가 필요한가
이전 단계에서 system은:
- verified patch-candidate를 제한적으로 source에 적용하고
- build/smoke rerun 결과를 관찰할 수 있었다.

하지만 아직 큰 구멍이 있었다.
바로:
**실패 시 원본으로 돌아갈 수 있는 최소한의 recovery가 없었다는 점**이다.

자가발전형 하네스 수정 루프에서 이건 치명적이다.
왜냐하면 apply는 자동화되는데 복구가 안 되면,
점점 working harness를 망가뜨릴 수 있기 때문이다.

## 이번에 붙인 것
### 1. pre-apply backup
`apply_verified_harness_patch_candidate(...)`가 이제 patch를 넣기 전에:
- `fuzz-records/harness-apply-backups/`
  - `*-pre-apply.backup`
을 남긴다.

즉 first-pass라도 원본은 항상 보관된다.

### 2. build/smoke failure 시 rollback
apply 후:
- build 실패 또는
- smoke 실패
가 나오면

system은:
- target file을 원본 content로 복구
- `rollback_status = restored`
- `apply_status = rolled_back`
로 기록한다.

즉 이제 최소한의 원복 루프는 있다.

### 3. rollback metadata 기록
apply candidate/result artifact에:
- `rollback_status`
- `backup_path`
를 남긴다.

그래서 다음 단계가:
- 왜 되돌렸는지
- 어떤 파일 기준으로 복구했는지
를 추적할 수 있다.

## 의미
이번 단계로 loop는 다음처럼 더 현실적으로 변했다.

- verified patch-candidate
- limited apply
- build/smoke rerun
- failure 시 rollback
- rollback metadata 기록

즉 이제 control-plane은 단순히 수정→실패를 보는 게 아니라,
**실패한 수정에서 working state를 보존하는 방향으로 진화했다.**

이건 production-safe까지는 아니어도,
적어도 “망가지면 복구도 못 하는 자동화” 단계는 벗어났다는 의미가 있다.

## 아직 일부러 안 한 것
이번 단계에서도 일부러 하지 않은 것:
- multi-step retry / hold / abort policy
- patch semantic correctness deeper checks
- diff size/scope guardrail 고도화
- rerun 실패 후 next correction policy 자동 재생성

즉 지금 rollback은 단일-step restore까지만 있다.
다음은 recovery policy와 diff safety 강화다.

## 냉정한 평가
좋아진 점:
- 실패한 limited apply가 working file을 영구적으로 오염시키지 않게 됐다
- backup과 rollback metadata가 남아 lineage가 더 강해졌다
- 실제 자동 수정 실행 루프의 안전성이 한 단계 올라갔다

여전히 부족한 점:
- rollback 기준이 아직 build/smoke fail에 단순히 묶여 있다
- patch semantic safety가 여전히 얕다
- retry/hold/abort 같은 후속 정책은 아직 없다

## 다음 단계
가장 자연스러운 다음 단계는:
- patch 의미/범위(diff size/scope)를 더 엄격히 제한하고
- rollback 이후 retry / hold / abort를 나누는 multi-step recovery policy를 붙이는 것이다.

즉 다음은:
**R20 candidate semantics / diff safety**
또는
**R20 multi-step recovery policy**
가 가장 자연스럽다.
