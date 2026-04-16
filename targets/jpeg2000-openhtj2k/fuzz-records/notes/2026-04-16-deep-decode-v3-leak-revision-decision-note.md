# Deep Decode V3 Leak Revision Decision Note

- Updated: 2026-04-16 18:39:00 KST
- Project: `fuzzing-jpeg2000`
- Scope: **toxic seed quarantine 이후 새 leak signal을 기준으로 다음 LLM revision 방향을 결정한 기록**

---

## 한 줄 결론
**지금 다음 단계는 deeper promotion이 아니라 triage-first다.**

즉:
- deep-decode-v3 방향 자체는 맞다
- 하지만 지금은 더 깊게 가는 것보다
- 새 leak이 진짜 decoder cleanup bug인지, harness/decoder lifecycle artifact인지 먼저 분리해야 한다

---

## 왜 그렇게 판단했나
### 1. 이번 leak은 실제 진전 신호다
좋은 점:
- 이전 startup-dominating SEGV를 유발하던 `p0_11.latebodyflip.j2k`를 quarantine한 뒤,
- active corpus 3개로 다시 시작했고,
- 이제 동일 startup crash 반복이 아니라 **새 LeakSanitizer signal**이 나왔다.

즉 이건:
- 같은 재현기만 반복하던 상태에서
- **실제 mutation-time signal**로 넘어왔다는 뜻이다.

### 2. 하지만 지금 suggested action은 약간 stale하다
packet은 아직:
- `shift_weight_to_deeper_harness`
- `promote-next-depth`
를 말하고 있다.

하지만 live state를 보면:
- 이미 deep-decode-v3 경로에 들어갔고
- deeper-path signal도 확보했다.

그래서 지금 immediate next step을
- 더 깊게 가자
로 두는 건 과하다.

### 3. 더 보수적인 다음 단계는 triage-first다
지금 가장 보수적인 해석은:
- 새 leak signal을 triage해서
  - 진짜 decode-path cleanup bug인지
  - harness/decoder lifecycle artifact인지
먼저 나눠보는 것이다.

이걸 안 하고 바로 deeper promotion이나 patching으로 가면,
실제 버그와 harness artifact를 섞어서 루프 품질을 떨어뜨릴 수 있다.

---

## 현재 leak의 의미
현재 stack에서 보이는 것:
- `j2k_tile::decode()`
- `decoder.invoke()`
- `deep_decode_focus_v3_harness.cpp`

이건 다음 두 경우 중 하나일 가능성이 높다:
1. malformed-but-deep input에서 `decode()` cleanup path 일부가 누락되는 실제 decoder-side leak
2. decoder reuse / lifecycle / single-tile reuse 성격 때문에 harness 쪽에서 leak처럼 보이는 artifact

중요한 점:
- base seed `p0_11.j2k`는 clean하다
- 변형 artifact에서 leak이 난다

즉 당장은
**seed triage + leak classification**이 next step이어야 한다.

---

## 다음 LLM revision decision
### 채택
- **triage-first**

### 지금 보류
- deeper-promotion
- harness-depth expansion
- broad seed-strategy rewrite
- premature patching

### 이유
- deeper stage reach는 이미 달성했다.
- 지금은 더 깊게 가는 것보다,
  **새 signal을 잃지 않고 분류하는 것**이 더 가치 있다.

---

## LLM-facing revision brief
### 바꿔야 할 것
- 이 leak을 triage 대상으로 잡는다.
- saved leak artifact와 clean parent seed를 비교 기준으로 삼는다.
- `j2k_tile::decode()` cleanup / lifetime 쪽을 우선 검토한다.

### 건드리지 말아야 할 것
- deep-decode-v3 primary mode 자체
- stable-valid smoke contract
- active corpus를 또 크게 흔드는 broad seed rewrite
- 지금 당장 deeper promotion
- leak detection 끄기

---

## operator checklist
1. saved leak artifact 재현성 확인
2. parent seed(`p0_11.j2k`)는 clean한지 유지 확인
3. `j2k_tile::decode()` allocation/free 경로 검토
4. `decoder.invoke()` / decoder lifecycle / reuse 정책 검토
5. leak을 decoder bug vs harness artifact로 분류
6. 분류 전에는 patching 금지

---

## 냉정한 최종평
**지금은 더 깊게 가야 하는 단계가 아니라, 드디어 deeper path에서 잡힌 새 signal을 잃지 않게 triage로 굳혀야 하는 단계다.**
