# 2026-04-16 — failure reason extraction v0.5 note

## 왜 이 단계를 바로 넣었나
v0.4까지 오면서 evidence packet은
- smoke/build/fuzz log
- harness probe
- apply result
본문 signal을 더 많이 읽게 됐다.

문제는 그 다음이었다.
- 같은 signal line이 반복되면 packet이 금방 noisy해졌다.
- reason code는 뽑히지만 정렬이 평평해서 상위 문제를 한눈에 보기 어려웠다.
- body signal은 line list로만 남아서 사람이든 LLM이든 빠르게 읽기 어려웠다.

그래서 이번 slice는
**signal pickup을 더 넓히는 대신, 이미 읽은 signal을 덜 시끄럽고 더 우선순위 있게 압축하는 쪽**으로 갔다.

## 이번에 추가한 것
### 1. raw signal line dedup
`_match_signal_lines(...)`가 이제
- 완전 동일 line 반복
- 같은 sanitizer class 반복
을 줄인다.

즉 같은 `AddressSanitizer` line이 여러 번 나와도 packet에는 중복이 덜 들어간다.

### 2. body-to-summary reduction
`raw_signal_summary`에 이제 plane별 summary가 생긴다.

추가 필드:
- `smoke_log_signal_summary`
- `build_log_signal_summary`
- `fuzz_log_signal_summary`
- `probe_signal_summary`
- `apply_signal_summary`
- `body_signal_priority`

예:
- `AddressSanitizer, runtime error`
- `AddressSanitizer`

즉 이제 packet은 raw line list만 주는 게 아니라,
**각 evidence plane에서 어떤 종류의 body signal이 핵심인지 한 줄로 먼저 압축**한다.

### 3. failure reason prioritization
failure reason을 이제 우선순위 순서로 다시 정렬한다.

이번 v0.5 기준 방향:
- build blocker / build log memory-safety signal
- smoke / probe / fuzz / apply scope mismatch
- stage reach / plateau / shallow recurrence
- no-crash-yet

추가 필드:
- `top_failure_reason_codes`

즉 이제는 `failure_reason_codes`와 markdown 상단이
**그냥 append된 순서가 아니라 더 operator-friendly한 상위 문제 순서**를 가지기 시작했다.

## 냉정한 평가
좋아진 점:
- packet이 덜 시끄러워졌다.
- repeated sanitizer body line이 evidence packet을 불필요하게 부풀리는 문제가 줄었다.
- raw body line을 다 읽기 전에 signal summary와 top reason codes로 먼저 상황을 잡을 수 있게 됐다.
- 다음 hunk/patch validation 단계들이 소비할 failure reason ordering도 조금 더 안정됐다.

한계:
- 여전히 heuristic 압축이다.
- signal summary는 root-cause summary가 아니라 label reduction에 가깝다.
- multi-reason conflict resolution은 아직 약하다.
- body signal priority도 현재는 coarse plane ordering이지 learned ranking이 아니다.

한 줄 평가:
**v0.5는 evidence packet을 더 똑똑하게 만든다기보다 덜 시끄럽고 더 우선순위 있게 정리하게 만든 단계다. 아직 diagnosis engine은 아니다.**

## 다음 단계
1. multi-reason hunk prioritization v0.1
   - 여러 failure reason이 동시에 있을 때 어떤 reason이 patch/hunk 방향을 주도해야 하는지 규칙화
2. failure reason extraction v0.6
   - signal label reduction을 넘어 body-to-reason explanation 품질 강화
3. finding-efficiency-facing intelligence 강화
   - novelty / coverage delta / crash quality를 repair loop와 더 직접 연결
