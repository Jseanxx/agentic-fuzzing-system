# 2026-04-16 — secondary-conflict severity/actionability v0.1 note

## 왜 이 단계를 바로 넣었나
직전 단계에서 시스템은 secondary conflict를
- artifact에 남기고
- retry routing에서 실제로 소비해
- 보수적으로 hold로 꺾기 시작했다.

문제는 그 다음이었다.
지금까지는 conflict가 보이면 거의 다 같은 종류로 취급됐다.
즉:
- review만 하면 될 수준의 tension
- corrective regeneration이 더 맞는 수준의 tension
이 아직 분리되지 않았다.

그래서 이번 slice는
**deferred secondary conflict를 최소한 reviewable conflict와 corrective-regeneration 급 conflict로 나누는 단계**로 갔다.

## 이번에 추가한 것
### 1. secondary conflict severity / actionability
새 routing 필드:
- `routing_secondary_conflict_severity`
- `routing_secondary_conflict_actionability`

현재 보수 규칙:
- base decision이 `retry`
- secondary conflict가 `present`

이면 severity를 본다.

현재 severe로 보는 기준:
- deferred reason code가 build 계열 severe set에 속함
  - 예: `build-blocker`
  - `build-log-memory-safety-signal`
  - `harness-build-probe-failed`
  - `guarded-apply-blocked`
- 또는 conflict count가 2 이상

### 2. 실제 routing 분기 강화
현재 분기:
- reviewable conflict
  - `severity=medium`
  - `actionability=review`
  - `decision=hold`
  - `status=override-from-secondary-conflict-hold`
- severe conflict
  - `severity=high`
  - `actionability=corrective-regeneration`
  - `decision=abort`
  - `status=override-from-secondary-conflict-abort`

즉 이제는 secondary conflict가 있다고 해서 전부 같은 hold가 아니라,
**최소한 hold와 abort 사이를 한 번 더 나눠 보기 시작했다.**

### 3. route artifact / manifest / result 반영
위 필드를 이제
- recovery routing entry
- recovery route manifest / markdown
- apply candidate manifest
- apply result payload
- route return payload
에 남긴다.

즉 routing artifact만 봐도
- conflict가 있었는지
- severity가 어느 정도였는지
- 무엇을 해야 하는지(review vs corrective-regeneration)
- 그래서 실제로 hold/abort 중 어디로 갔는지
를 같이 읽는다.

## 냉정한 평가
좋아진 점:
- secondary conflict를 더 이상 단일 상태로만 보지 않는다.
- reviewable tension과 regenerate 쪽이 맞는 tension을 최소 분리했다.
- routing이 조금 더 정책다워졌다.

한계:
- 여전히 coarse heuristic이다.
- severity confidence를 수치화하지 않는다.
- build 계열 reason set 중심이라 coverage/finding-efficiency 계열 conflict는 아직 얕다.
- retry budget/cooldown/confidence와 직접 연결되진 않는다.

한 줄 평가:
**이번 단계는 secondary conflict를 정교하게 이해한 게 아니라, conflict를 최소한 hold 급과 abort 급으로 나누기 시작한 단계다.**

## 다음 단계
1. finding-efficiency-facing intelligence 강화
   - novelty / coverage delta / crash quality를 repair loop와 더 직접 연결
2. failure reason extraction v0.9
   - narrative를 objective/routing linkage까지 더 직접 이어 붙이기
3. secondary-conflict confidence/budget linkage v0.1
   - severity/actionability를 retry budget, cooldown, reroute confidence와 더 직접 연결
