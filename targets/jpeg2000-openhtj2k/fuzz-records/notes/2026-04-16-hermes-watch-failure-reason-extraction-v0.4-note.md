# 2026-04-16 — failure reason extraction v0.4 note

## 왜 이 단계를 바로 넣었나
v0.3에서 smoke/build/fuzz raw log를 packet에 넣기 시작했지만,
실제로 reason code로 승격되는 건 smoke 쪽만 거의 살아 있었다.

또 packet은 여전히:
- latest `harness-probe` output 본문
- latest `harness-apply-result` semantics / verification summary 본문
을 거의 읽지 못했다.

그래서 이번 slice는
**evidence packet이 smoke-only에서 벗어나 build/fuzz/probe/apply body signal까지 같이 주워오게 만드는**
작은 safe slice로 갔다.

## 이번에 추가한 것
### 1. raw_signal_summary 확장
이제 `raw_signal_summary`가 다음까지 같이 요약한다.
- `build.log`
- `fuzz.log`
- latest `harness-probe`의 build/smoke probe output
- latest `harness-apply-result`의 `candidate_semantics_summary`, `verification_summary`, `candidate_semantics_reasons`

추가된 packet 필드:
- `build_log_signals`
- `fuzz_log_signals`
- `probe_signals`
- `probe_signal_count`
- `apply_signals`
- `apply_signal_count`

### 2. 새 reason code
이번에 승격된 것:
- `build-log-memory-safety-signal`
- `fuzz-log-memory-safety-signal`
- `harness-probe-memory-safety-signal`
- `apply-comment-scope-mismatch-signal`

의미:
- build/fuzz log 안의 sanitizer/runtime-error 류 단서를 이제 직접 reason으로 올린다.
- harness probe output에 이미 sanitizer signal이 있으면 그것도 pass/fail 비트가 아니라 body-level clue로 다룬다.
- guarded apply가 단순 blocked가 아니라 comment-only rail을 벗어났다는 본문 신호가 있으면 더 직접적인 reason으로 올린다.

### 3. markdown evidence도 body signal을 더 직접 노출
이제 packet markdown에서
- build/fuzz log signal line
- probe signal line
- apply signal line
을 같이 볼 수 있다.

즉 LLM handoff 전 사람이 packet markdown만 봐도
어디서 단서가 나왔는지 더 빨리 읽힌다.

## 실제 확인
실제 현재 repo에서 packet을 다시 생성해 보니,
아직 살아 있는 실데이터는 smoke log signal뿐이었다.

즉 v0.4가 들어갔다고 해서
현재 repo packet에 새 reason이 자동으로 더 붙은 건 아니다.

이건 구현 실패라기보다,
**실제 최신 artifact에 build/fuzz/probe/apply body signal이 아직 없어서 발화할 데이터가 없는 상태**에 가깝다.

## 냉정한 평가
좋아진 점:
- packet이 이제 snapshot/history/smoke log에만 의존하지 않는다.
- build/fuzz/probe/apply body도 같은 evidence plane으로 읽기 시작했다.
- apply blocked도 generic blocked reason에서 조금 더 구체적인 scope-mismatch reason으로 압축할 수 있게 됐다.

한계:
- 여전히 pattern matching 기반이다.
- body를 읽어도 “왜 그런지”를 semantic root-cause 수준으로 요약하진 못한다.
- noisy signal dedup / prioritization은 아직 약하다.

한 줄 평가:
**v0.4는 evidence packet을 body-signal 쪽으로 더 넓혔지만, 아직 diagnosis engine이라기보다 범위를 넓힌 signal collector다.**

## 다음 단계
1. evidence-aware output schema tightening
   - delegate output이 `llm_objective` / `failure_reason_codes`에 직접 답하도록 강제 강화
2. failure reason extraction v0.5
   - noisy signal dedup
   - prioritization
   - body-to-summary reduction
