# 2026-04-16 — secondary-reason conflict surfacing v0.1 note

## 왜 이 단계를 바로 넣었나
직전 단계들에서 시스템은
- top failure reason ordering
- primary reason 기반 hunk prioritization
- body-to-reason explanation
까지 얻었다.

문제는 그 다음이었다.
지금 구조는 primary reason을 더 잘 보지만,
그에 밀린 secondary reason이
- 그냥 무시된 건지
- 실제로 충돌 중인지
- 나중에 따로 봐야 하는지
artifact에서 잘 드러나지 않았다.

그래서 이번 slice는
**primary reason에 맞춰 aligned 판정을 하더라도, deferred secondary reason과의 tension을 artifact에 명시적으로 남기는 단계**로 갔다.

## 이번에 추가한 것
### 1. deferred secondary conflict surfacing
`_validate_failure_reason_hunk_alignment(...)`가 이제
primary reason 이후의 mapped top reasons도 다시 본다.

현재 규칙:
- primary/top reason은 hunk alignment 판정을 주도
- 그 뒤의 mapped secondary reason이 현재 hunk intent와 충돌하면
  - aligned 여부와 별개로
  - deferred secondary conflict로 기록

즉 이제는
primary reason 기준으로 pass하더라도,
**뒤에 밀린 secondary reason tension이 사라지지 않고 artifact에 남는다.**

### 2. 새 lineage 필드
추가 필드:
- `failure_reason_hunk_secondary_conflict_status`
- `failure_reason_hunk_secondary_conflict_count`
- `failure_reason_hunk_secondary_conflict_reasons`
- `failure_reason_hunk_deferred_reason_codes`

예:
- primary smoke reason은 guard-only와 일치 → aligned
- deferred `build-blocker`는 guard-only와 충돌 → secondary conflict present

### 3. apply/result lineage 반영
위 필드를
- apply result payload
- apply result artifact
- apply candidate manifest lineage
에 남긴다.

즉 이제 artifact만 봐도
- primary reason은 뭐였는지
- 왜 aligned/unverified였는지
- secondary reason tension이 있었는지
를 같이 볼 수 있다.

## 냉정한 평가
좋아진 점:
- primary reason만 보고 “문제 없음”처럼 보이던 케이스에서 deferred tension을 숨기지 않게 됐다.
- multi-reason conflict를 해결하지는 못하지만, 적어도 덮어버리지는 않게 됐다.
- 후속 단계가 secondary reason을 별도 corrective path로 다루기 쉬워졌다.

한계:
- still heuristic.
- deferred reason tension을 기록만 하지, 자동 분기/weighted merge는 하지 않는다.
- tension severity, urgency, actionability를 정교하게 계산하지 않는다.
- semantic trade-off analyzer는 아니다.

한 줄 평가:
**이번 단계는 multi-reason conflict를 푼 게 아니라, primary reason에 가려지던 secondary tension을 artifact에 보이게 만든 단계다.**

## 다음 단계
1. failure reason extraction v0.7
   - template explanation을 넘어 간단한 causal chain 압축 시도
2. secondary-conflict-aware routing v0.1
   - deferred tension이 일정 조건을 넘으면 downstream action/risk에 반영
3. finding-efficiency-facing intelligence 강화
   - novelty / coverage delta / crash quality를 repair loop와 더 직접 연결
