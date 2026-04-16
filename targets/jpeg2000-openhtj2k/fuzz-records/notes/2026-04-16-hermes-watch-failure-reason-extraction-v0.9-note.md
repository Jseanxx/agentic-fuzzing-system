# 2026-04-16 — failure reason extraction v0.9 note

## 왜 이 단계를 바로 넣었나
v0.8까지는 packet이
- top failure reason ordering
- explanation
- causal chain
- multi-reason narrative
를 더 잘 보여주게 진화했다.

그리고 직전 단계에서
- finding efficiency summary
- finding efficiency recommendation
까지 붙었다.

문제는 그 다음이었다.
여전히 operator/LLM이 packet을 읽고 나서
**그래서 다음에 어떤 종류의 수정/행동으로 가야 하는지**를 또 머리로 한 번 더 해석해야 했다.

그래서 이번 slice는
**reason narrative + finding recommendation을 next harness fix direction / action code / candidate route까지 더 직접 연결하는 단계**로 갔다.

## 이번에 추가한 것
### 1. objective → routing linkage fields
새 packet 필드:
- `suggested_action_code`
- `suggested_candidate_route`
- `objective_routing_linkage_summary`

즉 이제는 packet이
- `llm_objective`
- top reason narrative
- finding efficiency recommendation
을 가지고
**다음 행동을 한 단계 더 직접 추천**한다.

### 2. 현재 v0.9의 보수 linkage
현재는 작은 rule-based linkage다.
예:
- `deeper-stage-reach` + weak finding efficiency
  - `shift_weight_to_deeper_harness`
  - `promote-next-depth`
- `build-fix`
  - `halt_and_review_harness`
  - `review-current-candidate`
- `stage-reach-or-new-signal` + corpus bloat
  - `minimize_and_reseed`
  - `reseed-before-retry`

즉 지금은 아직 학습된 policy는 아니지만,
**LLM이 다음 action class를 덜 헤매게 만드는 얇은 연결층**이 생겼다.

### 3. markdown 상단 linkage 노출
markdown 상단에도 이제
- `suggested_action_code`
- `suggested_candidate_route`
- `objective_routing_linkage_summary`
가 같이 나온다.

즉 packet을 열자마자
- 왜 이런 reason이 떴는지
- 지금 finding quality가 어떤지
- 그래서 다음에 어떤 action/route 쪽으로 가야 하는지
를 한 화면에서 읽기 시작했다.

## 냉정한 평가
좋아진 점:
- 이제 packet이 단순 설명서가 아니라 얇은 next-action guide 역할도 하기 시작했다.
- LLM이 다음 수정 방향을 덜 헤맨다.
- 사용자가 원한 LLM-heavy / low-code 루프에 더 맞다.

한계:
- 여전히 rule-based linkage다.
- repair success probability를 학습해서 고르는 건 아니다.
- objective/routing 연결이 semantic planner 수준은 아니다.
- confidence/budget linkage는 아직 없다.

한 줄 평가:
**v0.9는 더 똑똑하게 추론한 게 아니라, packet이 “왜 + 그래서 다음엔 뭐”를 한 번에 더 직접 말하게 만든 단계다.**

## 다음 단계
1. usable v1 cutline review
   - 지금까지 만든 LLM-heavy / low-code 루프를 기준으로 어디서 멈출지 명확히 자르기
2. secondary-conflict confidence/budget linkage v0.1
   - severity/actionability를 retry budget, cooldown, reroute confidence와 더 직접 연결
3. 실사용 루프 점검
   - 실제 퍼징→정보추출→LLM 수정→재실행 흐름에서 과잉 slice 없이 바로 써먹을 수 있는지 검토
