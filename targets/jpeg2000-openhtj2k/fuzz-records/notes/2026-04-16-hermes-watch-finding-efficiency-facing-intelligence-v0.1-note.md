# 2026-04-16 — finding-efficiency-facing intelligence v0.1 note

## 왜 이 단계를 바로 넣었나
지금까지의 evidence packet은
- failure reason code
- explanation
- causal chain
- multi-reason narrative
를 더 잘 보여주게 진화했다.

하지만 여전히 부족한 게 있었다.
사용자가 원한 건 단순히 "왜 실패했나"뿐 아니라
**퍼징이 지금 실제로 좋은 finding을 만들고 있는가**를 LLM이 빨리 읽게 하는 것이었다.

즉:
- coverage가 늘고 있나
- corpus만 불어나고 gain은 없나
- crash novelty가 낮아졌나
- shallow crash만 반복되나
를 reason code 조합만으로 눈치채게 두는 건 비효율적이었다.

그래서 이번 slice는
**finding quality 저하 신호를 별도 summary/recommendation으로 packet 상단에 압축하는 단계**로 갔다.

## 이번에 추가한 것
### 1. finding efficiency summary
새 packet 필드:
- `finding_efficiency_summary`

현재 포함하는 값:
- `status`
- `summary`
- `coverage_delta`
- `corpus_growth`
- `unique_crash_fingerprints`
- `recent_window_size`
- `weak_signals`
- `recommendation`

즉 이제는 run history를 다시 계산하지 않아도,
**LLM이 finding quality가 약해지는 방향을 바로 읽기 쉬운 요약 객체**가 생겼다.

### 2. finding efficiency recommendation
새 packet 필드:
- `finding_efficiency_recommendation`

현재 v0.1 recommendation 예:
- `bias-llm-toward-novelty-and-stage-reach`
- `maintain-current-loop-and-collect-more-signal`

즉 이제는 단순 관측을 넘어서,
**LLM에게 지금 어떤 쪽으로 bias를 줘야 하는지 한 줄 recommendation**까지 함께 준다.

### 3. markdown `## Finding Efficiency` 블록
LLM evidence markdown에도 이제
- status
- summary
- coverage delta
- corpus growth
- unique crash fingerprints
- weak signals
- finding_efficiency_recommendation
을 따로 보여준다.

즉 packet 상단에서
failure reason 읽기와 별도로,
**퍼징 효율이 지금 왜 약한지**를 더 직접 읽기 시작했다.

## 냉정한 평가
좋아진 점:
- 이제 evidence packet이 단순 failure packet이 아니라 finding-quality packet 역할도 조금 하기 시작했다.
- coverage plateau / corpus low gain / shallow novelty 문제를 더 직접 보여준다.
- 사용자가 원한 LLM-heavy loop 방향에 더 맞다.

한계:
- 여전히 heuristic compression이다.
- novelty를 fingerprint count 수준으로만 거칠게 본다.
- crash quality / triage cost / coverage value를 정교하게 계산하지 않는다.
- repair efficacy와 닫힌 loop는 아니다.

한 줄 평가:
**이번 단계는 finding efficiency를 이해한 게 아니라, finding quality 저하 신호를 LLM이 바로 읽기 좋게 packet 상단에 압축하기 시작한 단계다.**

## 다음 단계
1. failure reason extraction v0.9
   - narrative를 objective/routing linkage까지 더 직접 이어 붙이기
2. secondary-conflict confidence/budget linkage v0.1
   - severity/actionability를 retry budget, cooldown, reroute confidence와 더 직접 연결
3. usable v1 cutline review
   - 지금까지 만든 LLM-heavy / low-code 루프를 기준으로 어디서 멈출지 명확히 자르기
