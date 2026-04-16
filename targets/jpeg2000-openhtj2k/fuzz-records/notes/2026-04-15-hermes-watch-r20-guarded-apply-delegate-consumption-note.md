# Hermes Watch — R20 guarded apply delegate consumption v0.1

- Date: 2026-04-15
- Scope: guarded apply candidate의 delegate request를 실제 bridge/launch 흐름으로 소비해 child LLM patch-candidate 작업을 시작할 수 있게 함

## 왜 이 단계가 필요한가
이전 단계에서 system은:
- promoted correction policy를 guarded apply candidate로 만들고
- optional delegate request까지 생성할 수 있었다.

하지만 아직 빠져 있던 것은:
**그 request를 실제로 소비해서 child LLM 작업을 launch하는 경로**였다.

즉 artifact는 준비됐지만,
실행까지는 아직 닿지 못한 상태였다.

## 이번에 붙인 것
### 1. apply candidate bridge 준비
새 함수:
- `prepare_harness_apply_candidate_bridge(repo_root)`

이 함수는 latest guarded apply candidate를 읽고:
- delegate request 존재 여부 확인
- `harness-apply-bridge/` 아래에
  - bridge prompt
  - bridge shell script
를 생성한다.

생성된 정보는 apply candidate manifest에 다시 기록된다.

### 2. apply candidate bridge launch
새 함수:
- `launch_harness_apply_candidate_bridge(repo_root)`

이 함수는 latest armed apply candidate bridge를 실행하고:
- launch log 저장
- delegate session id
- delegate status
- delegate artifact path
- delegate summary
를 manifest에 반영한다.

즉 이제 apply candidate artifact는 단순 준비 상태가 아니라,
**실제로 child LLM patch-candidate 작업을 시작하고 그 결과 메타데이터를 받는 상태**까지 간다.

### 3. CLI 추가
- `--bridge-harness-apply-candidate`
- `--launch-harness-apply-candidate`

이제 guarded apply candidate 이후에 bridge 준비/launch를 별도 단계로 실행할 수 있다.

## 의미
이번 단계로 loop는 다음처럼 더 또렷해졌다.

- correction policy
- guarded apply candidate
- delegate request
- bridge prompt/script
- delegate launch metadata

즉 이제 system은:
- child LLM patch-candidate 작업을 실제로 시작하고
- 그 launch 결과/session/artifact 경로를 추적할 수 있다.

아직 patch 내용을 검증하진 않지만,
**실행 자체는 이제 control-plane 안으로 들어왔다.**

## 아직 일부러 안 한 것
이번 단계에서도 일부러 하지 않은 것:
- child LLM이 만든 patch-candidate artifact의 shape/quality 검증
- patch candidate 결과를 source에 apply
- build/smoke 재검증과 rollback
- patch candidate를 registry/weighting에 반영

즉 지금은 delegate consumption까지다.
다음은 결과 ingestion/verification이다.

## 냉정한 평가
좋아진 점:
- 이제 child LLM patch-candidate 작업을 실제로 launch할 수 있다
- apply candidate manifest가 bridge/session/artifact 메타데이터를 추적한다
- 기존 refiner bridge 패턴과 유사한 control-plane 연결이 생겼다

여전히 부족한 점:
- patch-candidate artifact가 실제로 유효한지 아직 검사하지 않는다
- delegate가 실패해도 다음 corrective policy로 되먹이는 루프는 없다
- source mutation은 여전히 막혀 있고, 그게 맞다

## 다음 단계
가장 자연스러운 다음 단계는:
- delegate가 만든 patch-candidate artifact의
  - shape
  - required sections
  - quality
를 검증하고,
- 그 결과를 apply candidate manifest에 반영하는 것이다.

즉 다음은:
**R20 patch-candidate result verification / ingestion**
이 가장 자연스럽다.
