# 2026-04-16 — evidence-faithful patch validation v0.1 note

## 왜 이 단계를 바로 넣었나
직전 단계에서 delegate output이
- `llm_objective`
- `failure_reason_codes`
에 직접 답하도록 형식을 조였다.

하지만 그건 아직 “무슨 evidence에 답한다”고 적게 한 수준이었다.
즉 Patch Summary가 그 답과 실제로 맞물리는지는 거의 안 봤다.

그래서 이번 slice는
**Evidence Response와 Patch Summary가 서로 맞물리고 objective와도 정면 충돌하지 않는지** 보는
작은 safe slice로 갔다.

## 이번에 추가한 것
### 1. Patch Summary / Evidence Response 정합성 검사
`verify_delegate_entry(...)`가 이제 delegate artifact에서:
- `## Patch Summary`
- `## Evidence Response`
를 같이 읽는다.

그리고 최소한 다음을 본다.
- `response_summary`와 Patch Summary 사이에 token overlap이 있는가
- reported objective와 Patch Summary가 정면 충돌하지 않는가
  - 예: `deeper-stage-reach`인데 build script rewrite / persistent mode 제안

즉 이제는 output이 evidence에 답한다고 쓰기만 해서는 안 되고,
**Patch Summary 자체도 그 설명과 얼추 맞아야 한다.**

### 2. 새 lineage 필드
추가된 검증/결과 필드:
- `delegate_artifact_patch_alignment_verified`
- `delegate_reported_patch_summary`
- `delegate_reported_response_summary`

이 필드는 verification 결과뿐 아니라
apply/result artifact lineage에도 다시 남는다.

즉 이제는:
- input evidence
- delegate evidence response
- delegate patch summary
- verification/apply/result lineage
를 한 번 더 이어 볼 수 있다.

## 냉정한 평가
좋아진 점:
- 이제 output contract가 section 존재 여부를 넘어서, 최소한 patch intent까지 보기 시작했다.
- evidence-aware form enforcement에서 evidence-to-patch alignment check로 한 단계 갔다.
- objective와 정면 충돌하는 뻔한 엇나간 patch memo를 조금 더 빨리 걸러낼 수 있다.

한계:
- 여전히 heuristic이다.
- token overlap과 간단한 objective conflict rule만으로는 좋은 patch인지 판정할 수 없다.
- Patch Summary와 실제 code diff가 진짜 같은 의미인지는 아직 안 본다.

한 줄 평가:
**이번 단계는 “무슨 evidence에 답했는가”에서 한 걸음 더 나아가 “그 답과 patch summary가 얼추 맞는가”를 보기 시작했지만, 아직 diff-level semantic judge는 아니다.**

## 다음 단계
1. diff-aware evidence-to-patch validation v0.1
   - Patch Summary / Evidence Response와 실제 changed diff 또는 intended mutation shape 정합성 보기
2. failure reason extraction v0.5
   - noisy signal dedup
   - prioritization
   - body-to-summary reduction
