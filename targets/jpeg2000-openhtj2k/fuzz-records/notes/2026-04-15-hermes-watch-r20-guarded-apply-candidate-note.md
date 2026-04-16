# Hermes Watch — R20 guarded apply candidate generation v0.1

- Date: 2026-04-15
- Scope: promoted correction policy를 실제 source auto-apply 전 단계인 guarded apply candidate artifact와 optional delegate request로 연결

## 왜 이 단계가 필요한가
이전 단계까지는 system이:
- failed closure를 correction draft로 정리하고
- correction policy로 승격/보류를 판정할 수 있었다.

하지만 아직 부족했던 것은:
**승격된 correction을 실제 LLM 수정 작업으로 안전하게 넘기는 중간 artifact**였다.

즉 바로 source를 고치기보다 먼저 필요했던 것은:
- 지금 수정 후보를 만들 자격이 있는지
- 어느 범위까지 허용할지
- child LLM에게 어떤 artifact를 읽게 할지
를 명시하는 guarded apply candidate였다.

## 이번에 붙인 것
### 1. guarded apply candidate artifact
새 함수:
- `write_harness_apply_candidate(repo_root)`

이 함수는 latest correction policy를 읽고:
- decision
- apply_candidate_scope
- selected suggestions
- delegate trigger 여부
를 담은 guarded apply candidate manifest/markdown을 만든다.

새 artifact 위치:
- `fuzz-records/harness-apply-candidates/`
  - `*-harness-apply-candidate.json`
  - `*-harness-apply-candidate.md`

### 2. optional delegate request generation
policy가 다음 조건을 만족할 때만:
- `decision == promote-reviewable-correction`
- `apply_policy == comment-only`
- selected suggestion 존재

system은 추가로:
- `*-harness-apply-candidate-delegate-request.json`
을 생성한다.

즉 이제 child LLM을 자동 트리거할 준비가 된 request artifact가 생긴다.

### 3. 보수적 scope 분류
현재는 아주 보수적으로 scope를 잡는다.
- `smoke-fix` → `guard-only`
- `build-fix` → `comment-only`
- 나머지 → `comment-only`

이건 일부러 공격적으로 가지 않았다.
처음 단계의 목적은 source auto-apply가 아니라
**reviewable patch candidate generation**이기 때문이다.

### 4. CLI 추가
- `--prepare-harness-apply-candidate`

이제 correction policy 이후에 guarded apply candidate artifact를 별도 단계로 뽑을 수 있다.

## 의미
이번 단계로 loop는 다음처럼 더 또렷해졌다.

- skeleton draft
- closure evidence
- correction draft
- correction policy
- guarded apply candidate
- optional delegate request

즉 이제 system은:
- 무엇을 고칠지
- 그 제안을 지금 소비해도 되는지
- 이제 child LLM에게 patch candidate 생성을 맡겨도 되는지
까지 artifact로 정리한다.

이건 full auto-apply 전에 꼭 필요한 단계다.
왜냐하면 자가발전형 시스템은 “바로 고치기”보다
**어떤 수정만 자동화할지 경계선을 명시하는 것**이 더 중요하기 때문이다.

## 아직 일부러 안 한 것
이번 단계에서도 일부러 하지 않은 것:
- source 파일 자동 수정
- delegate request의 bridge/launch 자동 소비
- patch diff artifact 수신/검증
- compile/fix/verify 완전 폐루프

즉 지금은 apply candidate generation까지만 왔다.
실제 소비는 다음 단계다.

## 냉정한 평가
좋아진 점:
- promoted correction policy를 실제 다음 자동화 단계로 넘길 중간 artifact가 생겼다
- child LLM에게 읽힐 입력 범위가 더 명확해졌다
- auto-apply 없이도 “자동 트리거 준비 상태”까지는 만들었다

여전히 부족한 점:
- delegate request는 생성되지만 아직 orchestration bridge에 연결되진 않았다
- source mutation guardrail은 아직 artifact 레벨 선언에 가깝다
- patch candidate 결과를 다시 closure로 되먹이는 루프는 아직 없다

## 다음 단계
가장 자연스러운 다음 단계는:
- generated delegate request를 실제 bridge/launch 경로에 연결하고
- child LLM이 patch candidate artifact를 생성하게 한 뒤
- 그 결과를 다시 build/smoke verification과 연결하는 것이다.

즉 다음은:
**R20 guarded apply delegate consumption**
이 가장 자연스럽다.
