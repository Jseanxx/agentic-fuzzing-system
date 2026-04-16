# 2026-04-16 — evidence-aware output schema tightening v0.1 note

## 왜 이 단계를 바로 넣었나
v0.4까지 오면서 evidence packet 입력면은 꽤 넓어졌다.
하지만 delegate output 쪽은 여전히 약했다.

즉 system은:
- 어떤 evidence를 보고 delegate를 보냈는지
는 꽤 잘 남기는데,
- delegate artifact가 그 evidence에 실제로 답했는지
는 거의 형식적으로만 보고 있었다.

그래서 이번 slice는
**output schema가 `llm_objective` / `failure_reason_codes`에 직접 답하도록 최소 계약을 추가하는 단계**로 갔다.

## 이번에 추가한 것
### 1. delegate request contract 강화
guarded apply delegate request가 이제 artifact 안에
`## Evidence Response` section을 명시적으로 요구한다.

그 안에는 최소한 다음 line이 들어가야 한다.
- `llm_objective:`
- `failure_reason_codes:`

그리고 왜 이 patch candidate가 그 evidence에 대한 가장 작은 안전 대응인지 같이 적게 했다.

### 2. bridge arm 기본 expected/quality section 강화
bridge arm 단계가 apply candidate manifest에 기본적으로 다음 section을 기대하게 만들었다.
- `## Patch Summary`
- `## Evidence Response`
- `## Verification Steps`

즉 이제 Evidence Response는 optional 설명이 아니라
verification contract 일부가 됐다.

### 3. verification이 evidence response를 실제 파싱/검증
`verify_delegate_entry(...)`가 이제 delegate artifact에서
`## Evidence Response` section을 읽고 다음을 검증한다.
- `delegate_artifact_evidence_response_verified`
- `delegate_reported_llm_objective`
- `delegate_reported_failure_reason_codes`

즉 artifact가 단순히 섹션 제목만 갖고 있는지 보는 게 아니라,
실제로 manifest의 `llm_objective` / `failure_reason_codes`에 맞는 응답을 적었는지 보기 시작했다.

### 4. apply/result artifact도 이 필드를 계속 유지
verification 뿐 아니라 apply/result artifact에도 위 필드를 다시 남기게 했다.

즉 이제는:
- input evidence
- delegate response
- verification/apply/result lineage
가 artifact 상에서 한 번 더 이어진다.

## 냉정한 평가
좋아진 점:
- delegate output이 evidence를 무시한 generic patch memo로 끝날 가능성을 조금 줄였다.
- 이제 최소한 output이 “무슨 objective / 무슨 failure reason에 답한다”고 명시해야 한다.
- verification/apply/result artifact만 봐도 output contract 충족 여부를 더 직접 읽을 수 있다.

한계:
- 아직 semantic judge는 아니다.
- objective와 reason code를 적었다고 해서 patch가 실제로 그 evidence에 맞는 건 아니다.
- 지금 단계는 evidence-aware quality enforcement라기보다 **evidence-aware form enforcement + 기본 정합성 검사**에 가깝다.

한 줄 평가:
**이번 단계는 output이 evidence에 직접 답하도록 형식을 조였지만, 아직 patch 내용의 실질적 타당성을 판정하는 수준은 아니다.**

## 다음 단계
1. evidence-faithful patch validation v0.1
   - reported objective/reason과 patch summary/intent의 실제 정합성 검사
2. failure reason extraction v0.5
   - noisy signal dedup
   - prioritization
   - body-to-summary reduction
