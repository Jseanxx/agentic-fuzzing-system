# Review-First Harness/Target Assessment

- Updated: 2026-04-16 18:12:00 KST
- Context: fresh `hermes_watch` run after v2 real-loop checklist
- Trigger: `halt_and_review_harness` / `review-current-candidate`

---

## 한 줄 결론
**이번 실패는 새 하네스 수정부터 밀어야 하는 상황이 아니라, smoke baseline 계약과 현재 active target/profile이 어긋난 상태에서 known-bad seed가 반복적으로 smoke gate를 막고 있는 상황에 더 가깝다.**

---

## fresh 상태 요약
- latest outcome: `smoke-failed`
- latest artifact reason: `baseline-input-failed`
- latest objective: `smoke-enable-or-fix`
- suggested action: `halt_and_review_harness`
- suggested route: `review-current-candidate`
- raw smoke signal:
  - `runtime error`
  - `UndefinedBehaviorSanitizer`
- signal location:
  - `source/core/coding/block_decoding.cpp:86:23`

---

## 냉정한 판정
### primary bottleneck
- `harness-target`

### 왜 이렇게 봤나
1. 현재 profile/campaign의 primary binary는 `open_htj2k_deep_decode_focus_v3_harness` 쪽인데,
   smoke 실행은 여전히 `open_htj2k_decode_memory_harness` 쪽 계약에 더 묶여 있다.
2. baseline smoke seed에 `p0_12.j2k`가 계속 포함되어 있고,
   이 seed는 이미 regression/triage 성격으로 반복 기록되고 있다.
3. 즉 지금 루프는 “새로운 LLM-guided revision”보다도 먼저,
   **무엇을 clean smoke baseline으로 볼지** 정리되지 않은 상태다.

---

## 지금 review-first가 맞는 이유
- apply candidate / probe manifest가 아직 직접 이어진 상태가 아니다.
- 이 상황에서 patch/apply-first로 밀면,
  실제 병목(known-bad baseline + smoke contract mismatch)을 가린 채 수정만 늘어날 수 있다.
- 그래서 이번 단계의 올바른 해석은:
  - current candidate를 새로 고친다
  가 아니라
  - **현재 smoke contract / harness route / seed baseline을 review한다**
  쪽이다.

---

## 우선 점검할 파일
1. `scripts/run-smoke.sh`
   - smoke binary selection
   - baseline seed list
2. `fuzz-records/profiles/openhtj2k-target-profile-v1.yaml`
   - primary binary / mode
   - stable-valid seed definition
3. `fuzz/decode_memory_harness.cpp`
   - 기존 smoke harness contract
4. `fuzz/deep_decode_focus_v3_harness.cpp`
   - 현재 intended candidate contract
5. `source/core/coding/block_decoding.cpp`
   - current UB signal site

---

## 사용자 최종목표 기준 위험 신호
- smoke gate가 active campaign과 정렬되지 않으면,
  Discord에서 “돌려”를 쳐도 반복적으로 같은 triage/regression loop만 돌 수 있다.
- 즉 지금 제어면은 꽤 만들어졌지만,
  **clean smoke baseline / known-bad triage seed / active harness candidate** 이 세 축의 정렬이 아직 실제 자율 루프 품질을 제한한다.

---

## 다음 권고
1. smoke baseline 계약 점검
2. active target profile과 smoke binary/seed alignment 점검
3. 그 다음에만 harness revision / apply rail을 다시 태운다

## 운영 문장
**지금은 하네스를 더 똑똑하게 짜는 것보다, 시스템이 무엇을 “정상 smoke baseline”으로 간주하는지부터 다시 맞추는 게 우선이다.**
