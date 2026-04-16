# 2026-04-16 — diff-aware evidence-to-patch validation v0.1 note

## 왜 이 단계를 바로 넣었나
직전 단계에서는
- Evidence Response
- Patch Summary
의 정합성을 보기 시작했다.

하지만 그건 아직 artifact 텍스트끼리의 정합성에 가까웠다.
실제로 apply 단계에서 만들어진 mutation shape와 summary가 맞는지는 거의 안 봤다.

그래서 이번 slice는
**실제 적용 결과가 comment-only인지 guard-only인지 보고, delegate patch summary가 그 shape와 맞는지** 보는
작은 safe slice로 갔다.

## 이번에 추가한 것
### 1. apply 단계에서 actual mutation shape 기록
`apply_verified_harness_patch_candidate(...)`가 이제:
- `original_content`
- `patched_content`
- `apply_candidate_scope`
를 보고 actual mutation shape를 기록한다.

현재는 작게:
- `comment-only`
- `guard-only`
- `no-change`
정도만 본다.

새 필드:
- `actual_mutation_shape`
- `delegate_diff_alignment_verified`

### 2. delegate patch summary와 mutation shape 정합성 검사
현재 heuristic은 단순하지만 실제 apply 결과를 본다.
- actual mutation shape가 `comment-only`인데 summary가 `size guard`류면 false
- actual mutation shape가 `guard-only`인데 summary가 `guard` / `size` / `input`류면 true

즉 이제는
말/요약만이 아니라 **실제 적용된 변경 종류와 summary가 맞는지**도 보기 시작했다.

### 3. apply/result lineage에 반영
이 필드는 result payload와 apply result artifact에도 다시 남는다.

즉 이제 artifact 상에서:
- input evidence
- delegate response
- patch summary
- actual mutation shape
- apply result lineage
를 같이 따라갈 수 있다.

## 냉정한 평가
좋아진 점:
- 이제 validation이 artifact 텍스트끼리만 노는 게 아니라 실제 apply 결과까지 보기 시작했다.
- comment-only인데 guard 얘기를 하는 식의 명백한 mismatch를 더 빨리 잡을 수 있다.
- evidence-aware → patch-intent-aware → mutation-shape-aware로 한 단계 더 갔다.

한계:
- 아직 semantic diff judge는 아니다.
- changed hunk line 수준 의미를 해석하는 건 아니다.
- 실제로 왜 그 변경이 objective에 맞는지는 아직 깊게 판정하지 못한다.

한 줄 평가:
**이번 단계는 summary와 실제 mutation shape 사이 mismatch를 보기 시작했지만, 아직 changed hunk meaning까지 해석하는 수준은 아니다.**

## 다음 단계
1. hunk-intent-aware diff validation v0.1
   - changed hunk line과 objective/summary 연결
2. failure reason extraction v0.5
   - noisy signal dedup
   - prioritization
   - body-to-summary reduction
