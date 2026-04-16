# OpenHTJ2K Harness Improvement Plan

> Goal: OpenHTJ2K에서 방어 가치가 높은 memory-safety finding(UAF, invalid write, heap-buffer-overflow, double free, severe OOB)을 더 잘 드러내는 하네스 구조를 단계적으로 강화한다.

Date: 2026-04-15
Target repo: `/home/hermes/work/fuzzing-jpeg2000`
Current primary harness: `fuzz/decode_memory_harness.cpp`

---

## Current state

현재 주 하네스는 이미 다음 장점을 가진다.

- memory-buffer 기반 입력
- fresh decoder object 생성
- `parse()` + `invoke()` 경로 진입
- output plane 해제 수행
- smoke와 fuzz에서 실제 의미 있는 sanitizer finding을 생성함

이미 확인된 방향:
- `block_decoding.cpp:86` UBSan
- `coding_units.cpp:3076` ASan SEGV write 계열
- `j2kmarkers.cpp:52` ASan heap-buffer-overflow

즉, 하네스를 버릴 필요는 없고 **분화**시키는 게 맞다.

---

## Architecture

하네스는 하나만 더 세게 만드는 대신, 역할별 3개 체계로 가는 것이 좋다.

1. `decode_memory_harness.cpp` 유지
   - full decode / invoke / allocation-free lifecycle 담당
2. parser-focused harness 추가
   - marker / length / truncation / short codestream 경로 담당
3. cleanup-focused harness 추가
   - partially valid input 이후 exceptional cleanup path 담당

---

## Priority

### P0 — Keep and harden existing decode harness
**Why:** 이미 high-value crash를 잘 뽑고 있음.

Files:
- Keep: `fuzz/decode_memory_harness.cpp`
- Check/update build integration: `scripts/build-libfuzzer.sh`

Checklist:
- [ ] `DecodeOneInput()`에서 success/failure/exception 모두 cleanup 일관성 재점검
- [ ] output plane free 이전/이후 stale state 접근이 없는지 점검
- [ ] `parse()` 성공 후 `invoke()` 실패 경로에서도 메모리 해제가 완전한지 확인
- [ ] 가능하면 lightweight internal assertions는 추가하되 sanitizer signal을 가리지 않게 유지

Expected outcome:
- tile-part / object lifecycle / decode pipeline 계열 crash 유지

---

### P1 — Add parser-focused harness
**Why:** `j2kmarkers.cpp:52` 같은 parser-side memory bug를 더 빨리 찾기 위함.

Suggested file:
- Create: `fuzz/parse_memory_harness.cpp`

Target behavior:
- input -> decoder 생성
- 가능한 최소 parser entry 수행
- marker/segment length processing을 많이 타도록 유지
- full output decode까지는 꼭 안 가도 됨

Design notes:
- parser-only로 너무 shallow해지면 안 됨
- marker parsing 후 최소한의 downstream object interaction이 있으면 더 좋음
- malformed marker, short codestream, invalid segment length에 민감한 path를 우선

Checklist:
- [ ] marker parsing 함수 호출 경로를 파악
- [ ] decoder object lifetime을 유지하되 invoke-heavy cost는 줄임
- [ ] valid, near-valid, truncated seed에서 parser coverage 비교
- [ ] crash가 reject noise만 늘리는지 확인

Expected outcome:
- marker parser / codestream handling / short read / length misuse 계열 crash 증가

---

### P2 — Add cleanup-focused harness
**Why:** UAF, double free, invalid free는 성공 path보다 partial failure / rollback / exceptional cleanup에서 잘 나옴.

Suggested file:
- Create: `fuzz/cleanup_memory_harness.cpp`

Target behavior:
- 가능한 한 parse를 통과한 뒤
- decode 중간 또는 직후 실패하도록 유도되는 입력에서
- partial allocation/free/rollback 경로를 많이 타게 함

Design notes:
- truncate/near-valid input에 강한 하네스가 좋음
- early reject보다 partial success 후 failure가 중요
- multiple object/plane/component cleanup 경로가 살아 있어야 함

Checklist:
- [ ] near-valid truncated inputs로 cleanup path가 실제로 호출되는지 확인
- [ ] partial tile/component decode 이후 failure 경로가 존재하는지 확인
- [ ] 실패 후 output plane / internal state / temporary buffers가 안전하게 정리되는지 sanitizer로 검증

Expected outcome:
- UAF / invalid free / double free / stale pointer 계열 finding 가능성 상승

---

## Verification plan

### For each harness
- [ ] single-file smoke repro 가능
- [ ] libFuzzer build target 추가 가능
- [ ] sanitizer stack trace가 충분히 symbolized 됨
- [ ] crash artifact가 보존됨
- [ ] known-good seed로는 최소한 일부 path를 타고, toxic seed는 분리 가능

### Minimum success criteria
- [ ] 기존 decode harness보다 parser harness가 parser-side crash를 더 빨리 찾는지 비교
- [ ] cleanup harness가 partial-failure 계열 sanitizer finding을 실제로 만들 수 있는지 확인
- [ ] 3개 하네스의 역할이 서로 중복만 되는지 여부 점검

---

## Concrete next actions

1. `fuzz/decode_memory_harness.cpp` cleanup review
2. `fuzz/parse_memory_harness.cpp` 초안 작성
3. `fuzz/cleanup_memory_harness.cpp` 초안 작성
4. build script에 target 3개 반영
5. smoke/triage corpus를 하네스별로 매핑
6. Proxmox에서 짧은 비교 run 수행

---

## Bottom line

현재 하네스는 이미 유효하다.
다만 단일 하네스에 모든 목표를 실으려 하지 말고:

- full decode lifecycle
- parser/marker path
- exceptional cleanup path

로 **분화**하는 것이 OpenHTJ2K에서 가장 실전적이다.
