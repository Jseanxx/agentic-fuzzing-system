# cleanup_memory_harness.cpp TDD Implementation Plan

> Goal: OpenHTJ2K에서 partial decode / exceptional cleanup / rollback / allocation-free lifecycle 계열의 memory-safety finding(UAF, invalid free, double free, stale pointer, invalid write)을 더 잘 드러내는 cleanup-focused harness를 TDD로 구현한다.

Date: 2026-04-15
Repo: `/home/hermes/work/fuzzing-jpeg2000`

**Primary files**
- Create: `fuzz/cleanup_memory_harness.cpp`
- Modify: `CMakeLists.txt`
- Modify: `scripts/build-libfuzzer.sh`
- Create/Modify: `tests/test_cleanup_memory_harness.py` 또는 기존 smoke/CLI 검증 체계와 맞는 테스트 파일

---

## Design intent

이 하네스는 정상 decode만 잘 타는 것이 목적이 아니다.
핵심은:
- partially valid input이 parser를 어느 정도 통과하고
- decode 중간 또는 직후 실패하고
- cleanup/rollback/free 경로가 많이 실행되게 만드는 것이다.

즉 target bug class는 주로:
- use-after-free
- invalid free / double free
- stale pointer use after exceptional path
- invalid write during cleanup-sensitive state transitions
- partially initialized object teardown bugs

---

## Proposed architecture

### Core function
Suggested function name:
- `CleanupStressOneInput(const uint8_t* data, size_t size, bool verbose)`

Suggested status enum:
- `kDecoded`
- `kRejected`
- `kPartialFailure`

### Intended behavior
1. create fresh decoder
2. parse
3. invoke deeper decode path
4. always attempt cleanup of any planes/buffers allocated so far
5. if exception occurs after partial progress, cleanup still runs deterministically
6. no pointer reuse beyond cleanup boundary

### Important design point
이 하네스는 단순히 decode harness 복사본이면 안 된다.
cleanup path를 더 잘 드러내기 위해:
- cleanup helper를 조금 더 명시적으로 분리하고
- partial allocation state를 더 잘 관찰할 수 있게 verbose path를 다듬는 것이 좋다.

---

## Code direction

### Suggested skeleton
```cpp
namespace {

enum class CleanupStatus {
  kDecoded,
  kRejected,
  kPartialFailure,
};

void FreePlanes(std::vector<int32_t*>& planes) {
  for (auto* plane : planes) {
    delete[] plane;
  }
  planes.clear();
}

CleanupStatus CleanupStressOneInput(const uint8_t* data, size_t size, bool verbose) {
  if (data == nullptr || size == 0) {
    return CleanupStatus::kRejected;
  }

  std::vector<int32_t*> planes;
  std::vector<uint32_t> widths;
  std::vector<uint32_t> heights;
  std::vector<uint8_t> depths;
  std::vector<bool> signeds;

  try {
    open_htj2k::openhtj2k_decoder decoder(data, size, 0, 1);
    decoder.parse();
    decoder.invoke(planes, widths, heights, depths, signeds);
    FreePlanes(planes);
    return CleanupStatus::kDecoded;
  } catch (const std::exception& exc) {
    FreePlanes(planes);
    if (verbose) {
      std::fprintf(stderr, "cleanup path exception: %s\n", exc.what());
    }
    return planes.empty() ? CleanupStatus::kRejected : CleanupStatus::kPartialFailure;
  } catch (...) {
    FreePlanes(planes);
    if (verbose) {
      std::fprintf(stderr, "cleanup path exception: unknown\n");
    }
    return CleanupStatus::kPartialFailure;
  }
}

}  // namespace
```

### Important note
위 skeleton은 방향만 보여준다.
실제 구현에서는 `planes.empty()`만으로 partial progress를 판단하는 건 부족할 수 있다.
필요하면:
- `parse_succeeded`
- `invoke_started`
- `invoke_completed`
같은 로컬 플래그를 추가해서 partial failure를 더 정확하게 라벨링한다.

---

## TDD tasks

### Task 1: Add target wiring first
**Objective:** cleanup harness target names를 build graph에 고정

Target names:
- `open_htj2k_cleanup_memory_harness`
- `open_htj2k_cleanup_memory_fuzzer`

RED:
- target missing build failure

GREEN:
- build targets exist and compile

### Task 2: Add valid input smoke
**Objective:** valid seed에서 cleanup harness가 정상 decode path를 탈 수 있는지 확인

Command:
```bash
./build-fuzz-libfuzzer/bin/open_htj2k_cleanup_memory_harness --expect-ok conformance_data/ds0_ht_12_b11.j2k
```

### Task 3: Add partial-failure behavioral smoke
**Objective:** near-valid truncated input에서 partial failure/cleanup path를 강제로 타게 함

Suggested behavior:
- binary should not hide sanitizer findings
- if no sanitizer issue, harness should still reject gracefully

### Task 4: Add bounded fuzz sanity run
**Objective:** target이 실제 fuzz loop로 돌고 cleanup-sensitive crashes를 surfacing 할 수 있는지 확인

Command:
```bash
./build-fuzz-libfuzzer/bin/open_htj2k_cleanup_memory_fuzzer fuzz/corpus/triage -runs=100
```

### Task 5: Compare against decode harness
**Objective:** cleanup harness가 decode harness 대비 partial failure / cleanup-sensitive signal을 더 빨리 드러내는지 판단

Compare:
- time-to-first-crash
- crash type class
- write/free/lifetime relevance
- duplicate ratio

---

## Build integration changes

### CMakeLists.txt
Mirror current decode harness target structure.
Need to add:
- executable for CLI harness
- executable for libFuzzer target
- include directories
- link against `open_htj2k`
- sanitizer compile/link options identical to current style

### scripts/build-libfuzzer.sh
Extend to build:
- `open_htj2k_cleanup_memory_fuzzer`
- `open_htj2k_cleanup_memory_harness`

---

## Seed guidance for this harness

Best paired seeds:
- near-valid truncated inputs
- deep-path seeds that fail late
- tile-part stressing seeds
- packet/codeblock corruption seeds
- known parser-passing but decode-failing samples

Avoid using only:
- trivial early reject garbage
- shallow parser-only malformed seeds

---

## Success criteria

- build targets compile cleanly
- valid input smoke passes
- near-valid failure inputs drive cleanup path
- sanitizer catches lifecycle-sensitive findings if present
- harness gives more cleanup-relevant signal than the general decode harness

---

## Bottom line

`cleanup_memory_harness.cpp` should be a **lifecycle-sensitive sibling** of the current decode harness.
It exists to make exceptional cleanup / partial allocation / rollback behavior first-class fuzz targets rather than incidental side effects.
