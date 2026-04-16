# 2026-04-16 — delegate verification / apply policy evidence-aware lineage v0.1 note

## 왜 이 단계를 바로 이었나
`LLM evidence packet`을 만들고,
`failure reason extraction`을 강화하고,
`handoff prompt`까지 evidence-first로 바꿨다.

그런데 아직 하나가 비어 있었다.

입력 쪽은 evidence-aware해졌는데,
**verification/apply/result lineage에는 그 evidence 핵심 필드가 다시 남지 않았다.**

즉,
- LLM에게는 이유를 주는데
- 이후 artifact를 보면 그 이유가 다시 사라지는 상태였다.

이번 단계는 그 끊긴 부분을 잇는 아주 작은 lineage slice다.

## 이번에 한 것
### 1. verification lineage에 evidence 핵심 필드 재주입
`verify_harness_apply_candidate_result(...)`가 이제 manifest에 이미 있던:
- `llm_objective`
- `failure_reason_codes`
- `raw_signal_summary`

를 verification 결과와 함께 다시 manifest/return payload에 유지한다.

### 2. apply lineage에도 같은 필드 유지
`apply_verified_harness_patch_candidate(...)`도
blocked / applied result payload와 manifest/result artifact에
같은 evidence lineage를 넣는다.

즉 이제:
- delegate request
- verification result
- apply result

모두가 최소한 같은 evidence spine을 공유하기 시작했다.

## 의미
이 변화는 겉으로는 작다.
하지만 control-plane 입장에서는 중요하다.

이전:
- evidence packet 생성
- handoff 때만 evidence 사용
- verification/apply 단계로 가면 evidence context가 약해짐

이제:
- evidence packet 생성
- handoff 사용
- verification/apply/result artifact에도 핵심 evidence가 남음

즉 **LLM input evidence -> result lineage**가 처음으로 조금 닫히기 시작했다.

## 냉정한 한계
- 아직 delegate output schema 자체가 evidence-aware하진 않다.
- 즉 output이 `llm_objective`에 잘 답했는지까지 강제하지는 않는다.
- 아직 probe/apply artifact 본문을 더 깊게 읽는 건 다음 단계다.

한 줄 평가:
**이번 단계는 evidence를 결과 lineage에 다시 남기기 시작했지만, 아직 output contract까지 evidence-aware하게 강제한 건 아니다.**

## 다음 단계
1. `failure reason extraction v0.4`
   - build/fuzz log signal
   - probe/apply artifact body signal
2. `evidence-aware output schema tightening`
   - delegate output이 `llm_objective` / 핵심 reason에 직접 답하도록 압박
