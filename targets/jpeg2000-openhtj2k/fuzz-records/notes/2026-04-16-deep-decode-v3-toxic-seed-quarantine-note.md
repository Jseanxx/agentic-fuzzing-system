# Deep Decode V3 Toxic Seed Quarantine Note

- Updated: 2026-04-16 18:34:58 KST
- Project: `fuzzing-jpeg2000`
- Scope: **deep-decode-v3 corpus에서 startup-dominating toxic seed를 분리해 실제 mutation-time signal을 다시 보게 만든 단계**

---

## 왜 이 단계가 필요했나
smoke/profile alignment 이후 첫 fresh run은 의도한 deep-decode-v3 경로로 들어갔지만,
즉시 다음 문제가 드러났다:
- active corpus의 `p0_11.latebodyflip.j2k`가
- `coding_units.cpp:3076` / `j2k_tile::add_tile_part` crash를
- fuzzing mutation 전에 바로 재현했다.

즉 harness 방향은 맞았지만,
**active corpus가 이미 독성(reproducer-dominating) 상태라서 iteration quality를 가로막고 있었다.**

---

## 이번에 한 것
1. crash artifact SHA1와 active corpus seed SHA1를 대조했다.
   - `p0_11.latebodyflip.j2k`
   - `crash-5a7442f89cdfd35db10098c2966f3b3296ab8d76`
   - 둘이 동일함을 확인했다.
2. 이 seed를 active corpus에서 제거했다.
3. 대신 아래에 보존했다.
   - `fuzz/corpus/triage/p0_11.latebodyflip.j2k`
   - `fuzz/corpus/regression/p0_11.latebodyflip.j2k`
4. deep-decode-v3 corpus 3개 상태에서 watcher를 다시 실행했다.

---

## 실제 결과
재실행 후:
- 더 이상 startup에서 같은 SEGV가 즉시 반복되지 않았다.
- fuzzer가 3개 seed로 시작해 `cov: 42`, `ft: 121`, `corp: 3/672b` 상태까지 진행했다.
- mutation-time 실행 뒤 새로운 leak signal이 잡혔다.
  - `LeakSanitizer: 12312 byte(s) leaked in 1 allocation(s).`
  - stack:
    - `j2k_tile::decode()`
    - `decoder.invoke()`
    - `deep_decode_focus_v3_harness.cpp`

즉 이번 단계의 가치는:
- crash를 없앤 게 아니라
- **같은 startup reproducer가 active corpus를 지배하던 상태를 끊고, mutation-time signal을 다시 보게 만든 것**이다.

---

## 냉정한 평가
좋아진 점:
- active corpus가 덜 독성화됐다.
- loop가 같은 startup crash만 재생산하지 않고 다른 sanitizer signal을 다시 내기 시작했다.
- 최종목표인 LLM-driven 반복 루프 관점에서, 이제야 “같은 seed 재현기”가 아니라 “iteration 가능한 fuzz loop”에 조금 더 가까워졌다.

한계:
- 새 leak signal은 아직 triage 전이다.
- 현재 evidence packet은 여전히 `shift_weight_to_deeper_harness` 쪽으로 말하는데, 이건 지금 live state에 비해 약간 stale할 수 있다.
- 즉 다음 단계는 deeper harness promotion보다 **새 leak/crash family triage + corpus discipline 유지**가 더 우선일 수 있다.

---

## 한 줄 결론
**이번 단계는 하네스를 더 깊게 만든 게 아니라, deep-decode-v3 active corpus에서 toxic reproducer를 분리해 실제 mutation-time signal을 다시 보게 만든 quarantine 단계다.**
