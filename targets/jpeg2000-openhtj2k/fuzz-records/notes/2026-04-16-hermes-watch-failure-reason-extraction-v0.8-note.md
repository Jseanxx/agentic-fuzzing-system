# 2026-04-16 — failure reason extraction v0.8 note

## 왜 이 단계를 바로 넣었나
v0.7에서 시스템은
- per-reason explanation
- per-reason causal chain
- top failure reason chain
까지는 만들었다.

하지만 아직 packet 상단을 읽을 때는
- code 목록
- explanation 목록
- chain 목록
을 사람이 다시 머리로 합쳐야 했다.

즉 여전히
**왜 이 reason들이 같이 보이고, 무엇이 primary이고, 무엇이 supporting/deferred인지**는 바로 읽히지 않았다.

그래서 이번 slice는
**top reason들을 multi-reason narrative로 한 번 더 압축하는 단계**로 갔다.

## 이번에 추가한 것
### 1. top failure reason narrative steps
새 packet 필드:
- `top_failure_reason_narrative_steps`

현재는 top 3 reason을 다음 역할로 나눈다.
- `primary`
- `supporting`
- `deferred`

각 step은:
- `role`
- `code`
- `narrative`
- `explanation`
- `causal_chain`
을 가진다.

즉 이제는 top reason 목록이 단순 병렬 리스트가 아니라,
**짧은 역할 기반 narrative step들**로 읽힌다.

### 2. packet-level multi-reason narrative
새 packet 필드:
- `top_failure_reason_narrative`

형태는 아직 간단한 stitching이다.
예:
- `primary build-blocker ...; supporting build-log-memory-safety-signal ...; deferred no-crash-yet ...`
- `primary stage-reach-blocked ...; supporting no-progress-stall ...; deferred no-crash-yet ...`

즉 이제는 operator/LLM이
**왜 이 reason들이 같이 보이는지**를 한 줄 narrative로 더 빨리 읽을 수 있다.

### 3. markdown 상단 노출
LLM evidence markdown 상단도 이제
- `top_failure_reason_narrative_steps`
- `top_failure_reason_narrative`
를 같이 남긴다.

그래서 packet을 열자마자
- top reason ordering
- causal chain
- multi-reason narrative
를 한 번에 훑기 시작했다.

## 냉정한 평가
좋아진 점:
- code / explanation / chain을 사람이 다시 조립해야 하던 부담이 줄었다.
- top 3 reason의 역할(primary/supporting/deferred)이 더 직접 읽힌다.
- evidence packet readability가 또 한 칸 올라갔다.

한계:
- 여전히 template stitching이다.
- semantic causal graph가 아니다.
- real trade-off solver는 아니다.
- objective/routing linkage까지 직접 압축하진 않는다.

한 줄 평가:
**v0.8은 multi-reason reasoning을 한 게 아니라, top reason들을 operator/LLM이 더 빨리 읽도록 narrative 형태로 압축한 단계다.**

## 다음 단계
1. secondary-conflict severity/actionability v0.1
   - 어떤 deferred conflict를 hold로만 볼지, abort/review urgency로 볼지 더 세밀하게 분리
2. finding-efficiency-facing intelligence 강화
   - novelty / coverage delta / crash quality를 repair loop와 더 직접 연결
3. failure reason extraction v0.9
   - narrative를 objective/routing linkage까지 더 직접 이어 붙이기
