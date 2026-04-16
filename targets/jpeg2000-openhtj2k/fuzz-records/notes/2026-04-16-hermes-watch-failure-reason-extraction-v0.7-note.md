# 2026-04-16 — failure reason extraction v0.7 note

## 왜 이 단계를 바로 넣었나
v0.6에서 reason explanation은 생겼다.
하지만 아직 explanation은
- 어떤 summary key를 썼는지
- 어느 plane을 봤는지
정도의 template 설명에 가까웠다.

즉 여전히
**그래서 어떤 관측이 어떤 reason으로 이어졌는지**를 한 줄 causal chain처럼 읽기엔 부족했다.

그래서 이번 slice는
**top reason explanation을 causal-chain 형태로 더 압축해서 보여주는 단계**로 갔다.

## 이번에 추가한 것
### 1. per-reason causal chain 추가
`failure_reasons` 각 entry가 이제
- `explanation`
뿐 아니라
- `causal_chain`
도 가진다.

현재 causal chain은 작은 규칙 기반이다.
형태 예:
- `current_status => build-failed => build_log_signal_summary=runtime error, UndefinedBehaviorSanitizer => build-blocker`
- `smoke_log => smoke_log_signal_summary=AddressSanitizer => smoke-log-memory-safety-signal`

즉 이제는 reason이 어떤 source/evidence/signal summary를 따라 올라왔는지를
**짧은 화살표 체인으로 읽을 수 있다.**

### 2. top failure reason chain 노출
새 packet 필드:
- `top_failure_reason_chains`

형태:
- `[{code, causal_chain}, ...]`

즉 top reason 3개는 이제
- code
- explanation
- causal chain
의 세 층으로 읽을 수 있다.

### 3. markdown 상단 강화
LLM evidence markdown 상단도 이제
- `top_failure_reason_chains`
를 같이 남긴다.

그래서 packet 상단에서 바로
- 어떤 reason이 올라왔는지
- 왜 올라왔는지
- 어떤 causal chain으로 이어졌는지
를 한 번에 읽기 시작했다.

## 냉정한 평가
좋아진 점:
- explanation보다 한 단계 더 구조화된 causal reading이 가능해졌다.
- operator/LLM이 signal summary와 reason 사이 연결을 더 빠르게 훑을 수 있다.
- 단순 label reduction에서 evidence-to-reason chain 압축 쪽으로 한 칸 더 갔다.

한계:
- 여전히 template chain이다.
- semantic root-cause graph는 아니다.
- secondary/deferred reason tension을 causal chain 안에서 풀진 못한다.
- 실제 수정 효율 판단까지 연결되진 않는다.

한 줄 평가:
**v0.7은 causal diagnosis를 한 게 아니라, reason explanation을 더 chain-like하게 압축해 읽기 쉽게 만든 단계다.**

## 다음 단계
1. secondary-conflict-aware routing v0.1
   - deferred secondary tension이 일정 조건을 넘으면 downstream action/risk에 반영
2. failure reason extraction v0.8
   - causal chain을 multi-reason narrative 수준으로 압축 시도
3. finding-efficiency-facing intelligence 강화
   - novelty / coverage delta / crash quality를 repair loop와 더 직접 연결
