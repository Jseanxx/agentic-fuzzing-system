# 2026-04-16 — secondary-conflict-aware routing v0.1 note

## 왜 이 단계를 바로 넣었나
직전 단계에서 시스템은
- deferred secondary reason tension을 artifact에 노출
- top reason causal chain을 더 읽기 쉽게 압축
까지는 했다.

문제는 그 다음이었다.
이 tension이 보이더라도 recovery routing은 여전히 거의 그대로였다.
즉:
- primary reason 기준으로 `retry`
- secondary conflict는 `present`
이어도
실제 downstream action은 그대로 retry queue로 다시 밀릴 수 있었다.

그래서 이번 slice는
**secondary conflict를 기록만 하지 않고, retry recovery routing을 더 보수적인 hold/risk 판단으로 실제 소비하기 시작하는 단계**로 갔다.

## 이번에 추가한 것
### 1. secondary-conflict-aware routing adjustment
`route_harness_apply_recovery(...)`가 이제
- `failure_reason_hunk_secondary_conflict_status`
- `failure_reason_hunk_secondary_conflict_count`
- `failure_reason_hunk_secondary_conflict_reasons`
- `failure_reason_hunk_deferred_reason_codes`
를 읽는다.

현재 보수 규칙:
- base decision이 `retry`
- secondary conflict status가 `present`
- conflict count가 1 이상

이면
- retry를 그대로 밀지 않고
- `hold`로 조정한다.

즉 지금은
**충돌이 드러난 retry를 공격적으로 반복하지 않고, 일단 hold/review 쪽으로 꺾는 매우 보수적인 routing**을 선택한다.

### 2. 새 routing lineage 필드
추가 필드:
- `routing_secondary_conflict_status`
- `routing_secondary_conflict_count`
- `routing_secondary_conflict_reasons`
- `routing_secondary_conflict_deferred_reason_codes`

상태 예:
- `override-from-secondary-conflict`
- `none`
- `not-applicable`

### 3. route artifact / manifest / result 반영
위 필드를 이제
- recovery routing entry
- recovery route manifest / markdown
- apply candidate manifest
- apply result payload
에 남긴다.

즉 이제는 routing artifact만 봐도
- reverse-linked escalation이 있었는지
- secondary conflict가 routing에 반영됐는지
- 어떤 deferred reason code가 보수 override를 유발했는지
를 같이 읽을 수 있다.

## 냉정한 평가
좋아진 점:
- secondary tension이 이제 관찰값에만 머물지 않고 실제 action selection에 반영되기 시작했다.
- conflict가 드러난 retry를 무작정 반복하지 않게 됐다.
- evidence → hunk alignment → conflict surfacing → routing override로 spine이 한 단계 더 이어졌다.

한계:
- 여전히 coarse policy다.
- conflict severity를 정교하게 계산하지 않는다.
- 지금은 사실상 `present => hold`에 가까운 보수 규칙이다.
- abort/review urgency/actionability를 세밀하게 나누지 않는다.
- weighted multi-reason resolver는 아니다.

한 줄 평가:
**이번 단계는 secondary conflict를 이해한 게 아니라, 드러난 conflict를 retry action에 최소한 보수적으로 반영하기 시작한 단계다.**

## 다음 단계
1. failure reason extraction v0.8
   - causal chain을 multi-reason narrative 수준으로 더 압축
2. secondary-conflict severity/actionability v0.1
   - 어떤 conflict는 hold, 어떤 conflict는 abort/review urgency로 볼지 더 세밀하게 분리
3. finding-efficiency-facing intelligence 강화
   - novelty / coverage delta / crash quality를 repair loop와 더 직접 연결
