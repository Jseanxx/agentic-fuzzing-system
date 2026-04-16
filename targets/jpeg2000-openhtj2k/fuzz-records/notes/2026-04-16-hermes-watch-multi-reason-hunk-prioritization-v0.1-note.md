# 2026-04-16 — multi-reason hunk prioritization v0.1 note

## 왜 이 단계를 바로 넣었나
직전 단계들까지 오면서 시스템은
- `failure_reason_codes`
- `top_failure_reason_codes`
- changed hunk intent
를 각각 갖게 됐다.

문제는 이 셋이 아직 apply 단계에서 완전히 같은 방향으로 소비되지 않는다는 점이었다.
즉 packet 쪽에서는 이미 reason prioritization이 있었는데,
hunk alignment 쪽은 여전히 `failure_reason_codes` 전체를 평평하게 읽고 있었다.

그래서 이번 slice는
**multi-reason conflict가 있을 때 apply 단계가 `top_failure_reason_codes`를 우선 reason basis로 쓰도록 맞추는**
작은 safe slice로 갔다.

## 이번에 추가한 것
### 1. priority-aware failure reason hunk alignment
`_validate_failure_reason_hunk_alignment(...)`가 이제
- `failure_reason_codes`
- `top_failure_reason_codes`
를 같이 받는다.

현재 규칙:
- `top_failure_reason_codes` 안에 mapped reason이 있으면
  - 그 첫 번째 reason을 **primary reason**으로 사용
- 없으면
  - 기존처럼 `failure_reason_codes` 흐름을 사용

즉 이제는 packet 쪽 우선순위와 apply 쪽 hunk alignment가 최소한 같은 spine을 보기 시작했다.

### 2. 새 lineage 필드
추가 필드:
- `failure_reason_hunk_primary_reason_code`
- `failure_reason_hunk_priority_basis`

가능 값 예:
- `top_failure_reason_codes`
- `failure_reason_codes`

alignment reason 문구도 이제 priority winner를 드러낸다.

예:
- `smoke-log-memory-safety-signal: priority winner matched hunk intent guard-only`
- `smoke-log-memory-safety-signal: priority winner expects guard-only hunk intent, got comment-only`

### 3. conflict 축소 방식
현재 v0.1은 multi-reason 전체를 semantic merge하지 않는다.
대신:
- packet이 이미 고른 상위 reason을 apply 단계가 우선 소비
- 나머지 reason은 뒤로 미룸

즉 이번 단계는
**multi-reason conflict를 해결했다기보다, 최소한 packet priority와 hunk validation priority가 서로 엇갈리지 않게 만든 단계**다.

## 냉정한 평가
좋아진 점:
- evidence packet의 top reason ordering과 hunk alignment가 같은 우선순위 축을 보기 시작했다.
- `build-blocker + smoke memory-safety`가 동시에 있어도 top reason이 smoke 쪽이면 guard-only hunk를 우선 합리화할 수 있다.
- 반대로 top reason이 guard 계열인데 comment-only patch를 내는 경우 더 직접적으로 priority mismatch로 잡힌다.

한계:
- 아직 primary reason 1개를 뽑는 수준이다.
- second/third reason과의 tension을 구조적으로 설명하진 못한다.
- weighted merge나 conditional policy는 아직 없다.
- 여전히 semantic efficacy judge는 아니다.

한 줄 평가:
**v0.1은 multi-reason conflict를 깊게 해결한 게 아니라, packet priority와 apply-side hunk alignment priority를 일치시키는 첫 정렬 단계다.**

## 다음 단계
1. failure reason extraction v0.6
   - signal label reduction을 넘어 body-to-reason explanation 품질 강화
2. secondary-reason conflict surfacing v0.1
   - primary reason과 충돌하는 deferred reason을 artifact에 더 직접 남기기
3. finding-efficiency-facing intelligence 강화
   - novelty / coverage delta / crash quality를 repair loop와 더 직접 연결
