# 2026-04-16 — hunk-intent-aware diff validation v0.1 note

## 왜 이 단계를 바로 넣었나
직전 단계에서
- actual mutation shape
- Patch Summary
정합성을 보기 시작했다.

하지만 mutation shape는 여전히 coarse했다.
`comment-only` / `guard-only`까지만 보면, 실제 changed hunk line이 summary와 맞는지까지는 아직 멀었다.

그래서 이번 slice는
**실제 added hunk line preview를 남기고, Patch Summary가 그 changed line 의미와 맞는지** 보는
작은 safe slice로 갔다.

## 이번에 추가한 것
### 1. added hunk line preview 기록
apply 단계가 이제 실제 diff에서 added line 일부를 기록한다.

새 필드:
- `changed_hunk_added_lines_preview`

이걸 result payload와 apply result artifact에 남긴다.

### 2. hunk-intent alignment 검사
새 검증 필드:
- `delegate_hunk_intent_alignment_verified`

현재 heuristic:
- summary가 `comment` / `note`류면 added hunk preview에 Hermes comment line이 보여야 함
- summary가 `guard` / `size` / `input`류면 added hunk preview에 `if (size ...)` / `return ...`류가 보여야 함

즉 이제는
mutation shape 수준을 넘어서 **실제 추가된 line preview와 summary가 맞는지**도 보기 시작했다.

## 냉정한 평가
좋아진 점:
- validation이 한 단계 더 실제 diff line 쪽으로 내려왔다.
- comment-only vs guard-only 같은 큰 분류를 넘어서, 실제 추가된 줄이 summary와 맞는지 보기 시작했다.
- artifact만 봐도 “무슨 줄이 추가됐길래 이런 summary를 썼는지”를 조금 더 추적하기 쉬워졌다.

한계:
- 여전히 preview 기반이다.
- full hunk semantics, control-flow meaning, dataflow effect는 아직 안 본다.
- changed line이 실제 failure reason을 줄일 가능성이 큰지까지는 아직 못 본다.

한 줄 평가:
**이번 단계는 changed hunk preview와 summary mismatch를 보기 시작했지만, 아직 hunk 의미를 semantic하게 해석하는 수준은 아니다.**

## 다음 단계
1. failure-reason-to-hunk mapping v0.1
   - `failure_reason_codes`와 changed hunk line preview를 직접 연결
2. failure reason extraction v0.5
   - noisy signal dedup
   - prioritization
   - body-to-summary reduction
