# Hermes Watch — R20 patch-candidate result verification / ingestion v0.1

- Date: 2026-04-15
- Scope: child LLM이 만든 patch-candidate artifact의 session/artifact/shape/quality를 검증하고 apply candidate manifest에 다시 반영

## 왜 이 단계가 필요한가
이전 단계에서 system은:
- guarded apply candidate를 만들고
- delegate request를 bridge/launch로 소비해서
- child LLM patch-candidate 작업을 실제로 시작할 수 있었다.

하지만 아직 빠져 있던 것은:
**그 결과 artifact가 실제로 쓸 만한지 검증해서 control-plane 안으로 다시 ingest하는 단계**였다.

즉 launch는 가능했지만,
그 결과를 다음 단계가 믿고 읽을 수 있는 상태는 아니었다.

## 이번에 붙인 것
### 1. apply candidate verification
새 함수:
- `verify_harness_apply_candidate_result(repo_root, probe_runner=...)`

이 함수는 latest succeeded apply candidate를 읽고:
- delegate session visibility
- delegate artifact 존재
- expected sections 존재 여부
- quality sections 내용 존재 여부
를 검사한다.

검증 로직은 기존 delegate verification 패턴을 재사용한다.

### 2. manifest ingestion
verification 결과는 apply candidate manifest에 다시 기록된다.
주요 필드:
- `verification_status`
- `verification_summary`
- `delegate_session_verified`
- `delegate_artifact_verified`
- `delegate_artifact_shape_verified`
- `delegate_artifact_quality_verified`
- `verified_at`

즉 이제 apply candidate artifact는 단순 launch 결과를 넘어서,
**검증된 patch-candidate 결과 상태**를 담는다.

### 3. CLI 추가
- `--verify-harness-apply-candidate`

이제 bridge launch 이후에 patch-candidate artifact를 별도 단계로 검증할 수 있다.

## 의미
이번 단계로 loop는 다음처럼 더 또렷해졌다.

- guarded apply candidate
- delegate request
- bridge launch
- patch-candidate artifact 생성
- patch-candidate verification / ingestion

즉 이제 system은 child LLM 결과를:
- 세션이 실제 있었는지
- artifact가 실제 있는지
- 최소한의 구조/품질을 만족하는지
를 기준으로 판정할 수 있다.

이건 다음 단계의 guarded patch apply로 가기 전에 꼭 필요한 관문이다.

## 아직 일부러 안 한 것
이번 단계에서도 일부러 하지 않은 것:
- verified patch-candidate를 source에 적용
- build/smoke rerun
- patch apply 실패 시 rollback
- verification 결과를 registry weighting에 직접 반영

즉 지금은 result ingestion까지만 왔다.
다음은 제한적 apply와 closure rerun이다.

## 냉정한 평가
좋아진 점:
- child LLM 결과를 이제 control-plane이 다시 평가할 수 있다
- apply candidate manifest가 launch 상태뿐 아니라 verification 상태까지 담는다
- 다음 단계의 guarded patch apply로 넘어갈 기반이 생겼다

여전히 부족한 점:
- verified라고 해서 실제로 source에 적용한 것은 아니다
- patch semantics가 target에 맞는지까지는 아직 보장하지 않는다
- rerun/rollback이 없어서 아직 진짜 폐루프는 아니다

## 다음 단계
가장 자연스러운 다음 단계는:
- verified patch-candidate artifact를
- 아주 제한된 범위에서 source에 적용하고
- build/smoke rerun으로 다시 closure를 만드는 것이다.

즉 다음은:
**R20 guarded patch apply + build/smoke rerun**
이 가장 자연스럽다.
