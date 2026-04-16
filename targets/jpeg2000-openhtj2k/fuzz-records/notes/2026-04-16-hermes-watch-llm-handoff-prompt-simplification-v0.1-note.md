# 2026-04-16 — LLM handoff prompt simplification v0.1 note

## 왜 바로 이 단계를 넣었나
`LLM evidence packet`과 `failure reason extraction v0.2`까지 들어간 시점에서,
다음 병목은 더 분명해졌다.

문제는 evidence packet이 생겼는데도
**실제 delegate handoff가 그 evidence를 중심으로 작동하지 않는 것**이었다.

즉 packet은 좋아졌는데,
LLM에게 넘기는 작업 계약은 아직 예전 generic prompt 톤에 더 가까웠다.

그래서 이번 단계는:
- 더 많은 구조를 추가하지 않고
- guarded apply delegate handoff가
- latest `llm_objective` / `failure_reason_codes` / evidence packet path를 먼저 보게 만드는
아주 작은 prompt simplification slice로 갔다.

## 이번에 바꾼 것
### 1. apply candidate가 evidence packet을 같이 들고 다니기 시작
`write_harness_apply_candidate(...)`가 delegate request를 만들기 전에
latest LLM evidence packet을 생성하고 payload에 주입한다.

추가된 payload/context:
- `llm_evidence_json_path`
- `llm_evidence_markdown_path`
- `llm_objective`
- `failure_reason_codes`

### 2. delegate request goal 단순화
기존:
- promoted correction policy 중심의 generic guarded patch candidate 요청

이제:
- **latest LLM evidence packet을 primary input으로 사용**하라고 명시

즉 correction policy보다 더 앞에
“왜 지금 수정해야 하는가 / 어디에 집중해야 하는가”를 놓기 시작했다.

### 3. bridge prompt도 같은 방향으로 정렬
`build_delegate_bridge_prompt(...)`가 이제:
- request context에 evidence packet 경로가 있으면 먼저 읽고
- `failure_reasons` / `llm_objective`를 우선하라고 적는다.

즉 delegate handoff가 generic bridge-only dispatch에서
**evidence-first dispatch**로 한 단계 이동했다.

## 의미
이건 거창한 변화는 아니다.
하지만 중요하다.

이제 system은 적어도:
1. evidence packet을 만들고
2. 그 packet을 delegate request에 묶고
3. bridge prompt도 그것을 먼저 읽으라고 지시한다.

즉 `evidence -> handoff` 연결이 처음으로 실제 코드 경로에 들어왔다.

## 냉정한 한계
- 아직 delegate 결과 verification/apply policy가 evidence packet 핵심 필드를 다시 lineage에 남기진 않는다.
- 아직 prompt body는 여전히 text-heavy하고 artifact path 중심이다.
- handoff가 evidence를 "읽으라"고는 하지만, 아직 output schema를 evidence-aware하게 강제하진 않는다.

한 줄 평가:
**이번 단계는 handoff를 evidence-first로 정렬하기 시작했지만, 아직 result schema까지 evidence-aware하게 재설계한 건 아니다.**

## 다음 단계
1. failure reason extraction v0.3
   - raw log/body-level signals
   - import-path 실행성 문제
2. delegate verification / apply policy가 evidence 핵심 필드를 다시 lineage에 남기게 연결
