# 2026-04-16 — failure-reason-to-hunk mapping v0.1 note

## 왜 이 단계를 바로 넣었나
직전 단계에서
- added hunk line preview
- Patch Summary
정합성을 보기 시작했다.

하지만 아직은
**summary와 hunk preview가 서로 맞는가**만 보는 수준이었다.
그 changed hunk가 애초에 현재 `failure_reason_codes`에 맞는 방향인지까지는 못 봤다.

그래서 이번 slice는
**failure reason과 changed hunk intent를 직접 연결하는 최소 규칙**을 넣는 쪽으로 갔다.

## 이번에 추가한 것
### 1. changed hunk intent 분류 helper
added hunk preview를 아주 작게 분류한다.

현재 분류:
- `comment-only`
- `guard-only`
- `build-fix`
- `no-change`
- `unknown`

이건 semantic parser가 아니라 preview 기반 intent label이다.

### 2. failure reason -> expected hunk intent mapping
새 검증 필드:
- `failure_reason_hunk_alignment_verified`
- `failure_reason_hunk_alignment_summary`
- `failure_reason_hunk_alignment_reasons`
- `failure_reason_hunk_intent`

현재 최소 규칙:
- `smoke-log-memory-safety-signal`
- `smoke-invalid-or-harness-mismatch`
- `harness-probe-memory-safety-signal`
- `fuzz-log-memory-safety-signal`
  - `guard-only` hunk를 기대
- `build-blocker`
  - `build-fix` hunk를 기대

즉 이제는
summary와 hunk preview mismatch를 넘어서,
**현재 failure reason이 기대하는 수정 방향과 실제 changed hunk intent가 맞는지**까지 보기 시작했다.

### 3. apply/result lineage 반영
위 필드를
- apply result payload
- apply result artifact
- apply candidate manifest lineage
에 다시 남긴다.

그래서 artifact만 봐도 이제:
- 어떤 failure reason이 있었는지
- 실제 hunk intent가 무엇으로 분류됐는지
- 그 둘이 최소 규칙상 맞았는지
를 같이 볼 수 있다.

## 냉정한 평가
좋아진 점:
- validation이 summary/hunk pair를 넘어서 failure reason까지 연결되기 시작했다.
- smoke memory-safety signal인데 comment-only patch를 내는 식의 mismatch를 더 직접 잡을 수 있다.
- build-blocker인데 guard-only patch를 내는 경우도 이제 “방향이 다르다”는 걸 artifact로 남긴다.

한계:
- 여전히 preview 기반 intent 분류다.
- `build-fix`도 include/type/entrypoint/build-script를 세분화하지 않는다.
- 여러 failure reason이 섞인 경우 우선순위/혼합 판정은 아직 약하다.
- changed hunk가 실제로 failure를 줄였는지까지는 아직 못 본다.

한 줄 평가:
**이번 단계는 changed hunk가 summary와 맞는지를 넘어서 failure reason이 기대하는 수정 방향과 맞는지 보기 시작했지만, 아직 multi-reason prioritization이나 semantic efficacy judge는 아니다.**

## 다음 단계
1. failure reason extraction v0.5
   - noisy signal dedup
   - prioritization
   - body-to-summary reduction
2. multi-reason hunk prioritization v0.1
   - 여러 failure reason이 섞일 때 어떤 reason이 hunk intent를 주도해야 하는지 규칙화
3. finding-efficiency-facing intelligence 강화
   - novelty / stage delta / crash quality를 repair loop와 더 직접 연결
