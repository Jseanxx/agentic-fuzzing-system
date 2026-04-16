# Hermes Watch Smoke/Profile Alignment v0.1

- Updated: 2026-04-16 18:26:43 KST
- Project: `fuzzing-jpeg2000`
- Scope: **current target profile의 active campaign과 watcher의 실제 smoke/fuzz 계약이 어긋나던 문제를 최소 정렬**

---

## 왜 이 단계가 필요했나
직전 fresh run에서 드러난 핵심 문제는:
- profile의 primary binary는 `open_htj2k_deep_decode_focus_v3_harness`
- 그런데 watcher의 default smoke는 `open_htj2k_decode_memory_harness`
- 기본 smoke seed 목록에는 이미 regression/triage 성격으로 반복된 `p0_12.j2k`가 들어 있었다

즉, LLM revision loop를 더 밀기 전에
**무엇을 정상 smoke baseline으로 간주할지부터 현재 campaign과 맞춰야 했다.**

---

## 이번에 바꾼 것
### 1. `run-smoke.sh` 정렬
- 첫 번째 인자를 단순 build dir뿐 아니라 **직접 harness binary path**로도 받을 수 있게 했다.
- 기본 smoke seed 목록에서 `p0_12.j2k`를 제거했다.
- 기본 smoke seed는 profile의 `stable-valid` 예시에 맞춰:
  - `ds0_ht_12_b11.j2k`
  - `p0_11.j2k`
  만 사용하게 했다.

### 2. target profile에 runtime adapter 계약 추가
`fuzz-records/profiles/openhtj2k-target-profile-v1.yaml`에 `target.adapter`를 추가해,
watcher가 실제로:
- build: `scripts/build-libfuzzer.sh`
- smoke: `build-fuzz-libfuzzer/bin/open_htj2k_deep_decode_focus_v3_harness`
- fuzz: `open_htj2k_deep_decode_focus_v3_fuzzer` + `fuzz/corpus-afl/deep-decode-v3`
를 사용하도록 정렬하기 시작했다.

즉 이제 watcher의 runtime command 계약이
**current profile의 active deep-decode-v3 campaign과 더 가깝게 맞는다.**

---

## 실제 효과
이 정렬 이후 fresh run에서는 더 이상 이전처럼 smoke baseline에서 `p0_12.j2k`가 즉시 막지 않았다.
대신 실제 loop가:
- deep-decode-v3 smoke를 통과하고
- deep-decode-v3 fuzzer 경로로 들어가
- `coding_units.cpp:3076` / `j2k_tile::add_tile_part` 쪽 crash를 잡았다.

즉 이번 단계의 가치는:
- crash를 없앤 것이 아니라
- **루프가 현재 intended harness/corpus 경로로 실제 진입하게 만든 것**이다.

---

## 냉정한 평가
좋아진 점:
- smoke baseline 계약이 active campaign과 더 정렬됐다.
- known-bad regression seed가 기본 smoke gate를 반복 오염시키는 문제를 줄였다.
- LLM/evidence loop가 이제 smoke-failed 반복 대신 실제 crash evidence를 다시 받기 시작했다.

한계:
- 아직 완전한 remote/proxmox orchestration은 아니다.
- fuzz command도 여전히 local libFuzzer substrate를 사용한다.
- profile의 `current_campaign`은 AFL++ 중심인데 runtime adapter는 local watcher compatibility 때문에 libFuzzer 쪽 계약을 우선 쓴다.
- 즉 이 단계는 **runtime alignment v0.1**이지 최종 remote-autonomous loop 완성은 아니다.

---

## 한 줄 결론
**이번 단계는 LLM이 더 똑똑해진 게 아니라, watcher가 지금 의도한 deep-decode-v3 smoke/fuzz 경로로 실제 들어가게 만든 smoke/profile contract 정렬 단계다.**
