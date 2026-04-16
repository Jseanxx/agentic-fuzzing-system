# Hermes Watch — R20 correction-consumption / apply policy v0.1

- Date: 2026-04-15
- Scope: harness skeleton correction draft를 latest closure evidence와 대조해 승격/보류 policy artifact로 남기는 단계

## 왜 이 단계가 필요한가
이전 단계까지는 system이 failed closure를 보고 correction draft를 만들 수는 있었지만,
그 draft를 **지금 소비해도 되는지**는 판단하지 못했다.

그 결과:
- 성공한 closure에도 예전 correction suggestion이 계속 매달릴 수 있었고
- 실패 evidence가 없는 suggestion도 실제 수정 후보처럼 보일 수 있었고
- 다음 단계의 guarded apply 후보를 어디서부터 시작해야 할지 기준이 약했다.

이번 단계의 목적은
**correction draft를 closure-backed policy decision으로 한 번 더 좁히는 것**이다.

## 이번에 붙인 것
### 1. correction consumption policy payload
`scripts/hermes_watch_support/harness_skeleton.py`에 다음 흐름을 추가했다.

- latest correction draft 로드
- latest skeleton closure evidence 로드
- 둘을 합쳐 `decision`, `disposition`, `apply_policy` 결정

핵심 판정은 보수적으로 잡았다.

- build failed / smoke failed
  - `decision = promote-reviewable-correction`
  - `disposition = promoted`
  - `apply_policy = comment-only`
- build passed + smoke passed
  - `decision = hold-no-change`
  - `disposition = deferred`
  - `apply_policy = none`
- smoke skipped / closure missing
  - hold 쪽으로 남김

즉 지금은 **실패 evidence가 있는 correction만 reviewable 상태로 승격**한다.

### 2. 새 artifact 계층
새 디렉터리:
- `fuzz-records/harness-correction-policies/`

생성 파일:
- `*-harness-correction-policy.json`
- `*-harness-correction-policy.md`

이 artifact는 다음을 canonical하게 남긴다.
- source correction draft path
- source closure manifest path
- decision / disposition / apply policy
- 실제 선택된 suggestion 목록

### 3. CLI 추가
- `--decide-harness-correction-policy`

이제 skeleton draft/closure 이후에
correction consumption policy artifact를 별도 경로로 뽑을 수 있다.

## 의미
이번 변경으로 loop는 다음처럼 한 단계 더 또렷해졌다.

- skeleton draft
- closure evidence
- correction draft
- correction consumption policy

즉 이제 system은
**“무엇을 고칠지” 뿐 아니라 “그 제안을 지금 소비해도 되는지”**도 artifact로 남긴다.

이건 실제 patch apply 전 단계에서 매우 중요하다.
왜냐하면 자가발전형 시스템은 제안 생성보다
**제안 승격 기준**이 더 중요하기 때문이다.

## 아직 일부러 안 한 것
이번 단계에서도 일부러 하지 않은 것:
- 실제 코드 patch auto-apply
- compile/fix/verify closed loop
- 성공 revision 승격분을 소스에 바로 반영
- correction policy 결과를 registry weight에 직접 반영

즉 이 단계는 apply가 아니라
**guarded consumption substrate**다.

## 냉정한 평가
좋아진 점:
- correction artifact가 더 이상 advisory-only로 떠다니지 않는다
- closure evidence가 있는 실패 suggestion만 승격된다
- 다음 단계의 guarded apply 후보를 만들 기준점이 생겼다

여전히 부족한 점:
- `comment-only` 수준 정책이라 실제 수정은 아직 사람/다음 단계가 해야 한다
- closure와 correction draft의 lineage는 있지만, patch diff artifact는 아직 없다
- compile/fix/verify 폐루프는 여전히 미완이다

## 다음 단계
가장 자연스러운 다음 단계는:
- promoted correction policy만 대상으로
- 아주 보수적인 comment/TODO 수준 patch candidate를 생성하고
- 그 결과를 다시 build/smoke verification으로 되먹이는 것

즉 다음은
**R20 guarded apply candidate generation**
이 가장 자연스럽다.
