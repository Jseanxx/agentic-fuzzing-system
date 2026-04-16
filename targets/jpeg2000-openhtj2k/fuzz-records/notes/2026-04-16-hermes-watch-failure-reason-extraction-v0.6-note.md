# 2026-04-16 — failure reason extraction v0.6 note

## 왜 이 단계를 바로 넣었나
v0.5까지 오면서 evidence packet은
- 덜 noisy해졌고
- top reason ordering도 생겼다.

하지만 여전히 약한 건
**reason이 왜 지금 중요한지**를 한 줄 더 직접 설명하는 층이었다.

즉 packet은
- signal label summary
- top reason code
를 주지만,
그 reason이 body signal과 어떻게 연결되는지는 사람이 다시 추론해야 했다.

그래서 이번 slice는
**signal label reduction을 넘어서, reason이 어떤 body signal summary를 근거로 삼는지 설명 문자열을 같이 남기는 단계**로 갔다.

## 이번에 추가한 것
### 1. per-reason explanation 추가
`failure_reasons`의 각 reason entry가 이제
- `code`
- `summary`
- `source`
- `evidence`
뿐 아니라
- `explanation`
을 가진다.

현재 explanation은 작은 규칙 기반이다.
예:
- `build-log-memory-safety-signal`
  - `build_log_signal_summary`
  - `build_log`
- `smoke-log-memory-safety-signal`
  - `smoke_log_signal_summary`
  - `smoke_log`
- `harness-probe-memory-safety-signal`
  - `probe_signal_summary`
  - `probe`
- `apply-comment-scope-mismatch-signal`
  - `apply_signal_summary`
  - `apply`

즉 reason이 그냥 이름만 있는 게 아니라,
**어느 body plane의 어떤 summary를 근거로 잡았는지**를 더 직접 말하기 시작했다.

### 2. top failure reason explanation 노출
새 packet 필드:
- `top_failure_reason_explanations`

형태:
- `[{code, explanation}, ...]`

즉 이제 top failure reason 3개는
code만이 아니라 **짧은 근거 설명과 함께** 상단에 노출된다.

### 3. markdown 상단 설명 강화
LLM evidence markdown 상단도 이제
- `top_failure_reason_codes`
- `top_failure_reason_explanations`
를 함께 남긴다.

그래서 raw signal section을 내려가기 전에도
왜 이 reason이 앞에 왔는지 더 빨리 읽힌다.

## 냉정한 평가
좋아진 점:
- packet이 이제 code/summary 나열을 넘어서 reason-to-body linkage를 더 직접 설명한다.
- operator나 LLM이 top reason을 읽고 다시 raw signal section을 역추적하는 비용이 조금 줄었다.
- next-step selection에 필요한 “왜 이 reason이 올라왔는가” 설명력이 약간 좋아졌다.

한계:
- 아직 explanation은 template 기반이다.
- root-cause narrative나 causal chain을 생성하는 수준은 아니다.
- secondary/deferred reason tension을 설명하진 못한다.
- semantic diagnosis engine은 여전히 아니다.

한 줄 평가:
**v0.6은 failure reason을 더 잘 이해한다기보다, 이미 뽑은 reason이 어떤 body signal summary를 근거로 했는지 더 읽기 좋게 설명하는 단계다.**

## 다음 단계
1. secondary-reason conflict surfacing v0.1
   - primary reason에 밀린 deferred reason tension을 artifact에 더 직접 남기기
2. failure reason extraction v0.7
   - template explanation을 넘어 간단한 causal chain 압축 시도
3. finding-efficiency-facing intelligence 강화
   - novelty / coverage delta / crash quality를 repair loop와 더 직접 연결
