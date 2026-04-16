# parse_memory_harness.cpp TDD Implementation Plan

> Goal: OpenHTJ2K에서 marker parsing / segment length / truncated codestream 계열의 memory-safety finding을 더 잘 드러내는 parser-focused harness를 TDD로 구현한다.

Date: 2026-04-15
Repo: `/home/hermes/work/fuzzing-jpeg2000`

**Primary files**
- Create: `fuzz/parse_memory_harness.cpp`
- Modify: `CMakeLists.txt`
- Modify: `scripts/build-libfuzzer.sh`
- Create/Modify: `tests/test_parse_memory_harness.py` 또는 기존 harness smoke/CLI 검증 체계에 맞는 테스트 파일

---

## Design intent

현재 `decode_memory_harness.cpp`는 full decode lifecycle 쪽에는 좋지만,
parser/marker 경로를 독립적으로 세게 때리는 데는 불필요하게 깊고 비용이 큰 측면이 있다.

`parse_memory_harness.cpp`의 목적은:
- parser-side code path를 더 일찍/더 자주 두드리고
- marker/segment length/truncation 계열 corruption을 더 잘 드러내며
- full decode 수행 없이도 memory-safety signal을 잡아내는 것이다.

즉 target bug class는 주로:
- heap-buffer-overflow
- out-of-bounds read/write in marker parsing
- malformed marker length handling
- short codestream / truncated read handling
- arithmetic issue that precedes parser corruption

---

## Proposed architecture

### Core shape
`DecodeOneInput`를 새로 만들기보다, parser-focused 함수로 분리한다.

Suggested core function name:
- `ParseOneInput(const uint8_t* data, size_t size, bool verbose)`

Suggested status enum:
- `kParsed`
- `kRejected`

### Intended flow
1. null/zero input reject
2. decoder object creation
3. parser-heavy entry execution
4. 가능한 최소 downstream parser interaction
5. exception/unknown exception handling
6. no persistent state left behind

### Important constraint
이 하네스는 parser-only reject machine이 되면 안 된다.
즉, 너무 이르게 끝나서 coverage가 shallow해지지 않도록:
- marker parsing이 충분히 진행된 뒤 실패하도록 설계된 시드와 같이 써야 한다.

---

## Code direction

### Suggested skeleton
```cpp
namespace {

enum class ParseStatus {
  kParsed,
  kRejected,
};

ParseStatus ParseOneInput(const uint8_t* data, size_t size, bool verbose) {
  if (data == nullptr || size == 0) {
    return ParseStatus::kRejected;
  }

  try {
    open_htj2k::openhtj2k_decoder decoder(data, size, /*reduce_NL=*/0, /*num_threads=*/1);
    decoder.parse();
    return ParseStatus::kParsed;
  } catch (const std::exception& exc) {
    if (verbose) {
      std::fprintf(stderr, "parser rejected input: %s\n", exc.what());
    }
    return ParseStatus::kRejected;
  } catch (...) {
    if (verbose) {
      std::fprintf(stderr, "parser rejected input: unknown exception\n");
    }
    return ParseStatus::kRejected;
  }
}

}  // namespace

extern "C" int LLVMFuzzerTestOneInput(const uint8_t* data, size_t size) {
  (void)ParseOneInput(data, size, /*verbose=*/false);
  return 0;
}
```

### Why minimal is OK first
TDD first pass에서는 parser-heavy path만 분리하는 최소 구현이 맞다.
필요 이상으로 invoke/decode를 다시 섞으면 decode harness와 역할이 흐려진다.

---

## TDD tasks

### Task 1: Add build target wiring test expectation
**Objective:** 새 harness target이 build graph에 들어가야 함을 먼저 고정

Files:
- Modify: `CMakeLists.txt`
- Modify: `scripts/build-libfuzzer.sh`
- Test: lightweight build-target assertion script or documentation-backed verification step

RED:
- `cmake --build ... --target open_htj2k_parse_memory_fuzzer` should fail initially

GREEN target names:
- `open_htj2k_parse_memory_harness`
- `open_htj2k_parse_memory_fuzzer`

### Task 2: Add CLI smoke behavior test
**Objective:** harness binary가 valid file을 받아 parser path를 탈 수 있는지 확인

Suggested CLI contract:
- usage similar to existing decode harness
- optional `--expect-ok`

RED example:
- valid seed로 실행 시 binary not found / target missing

GREEN example:
```bash
./build-fuzz-libfuzzer/bin/open_htj2k_parse_memory_harness --expect-ok conformance_data/p0_11.j2k
```

### Task 3: Add malformed input rejection smoke
**Objective:** malformed input에 대해 crash 없이 reject 또는 sanitizer signal이 나오는지 확인

RED:
- tiny malformed input fixture or generated file causes harness command mismatch / missing binary

GREEN:
- harness returns reject semantics or sanitizer reports genuine bug

### Task 4: Add bounded libFuzzer sanity run
**Objective:** parser-focused target이 실제 fuzz loop로 진입하는지 확인

Command:
```bash
./build-fuzz-libfuzzer/bin/open_htj2k_parse_memory_fuzzer fuzz/corpus/coverage -runs=100
```

Success:
- target starts
- corpus loads
- sanitizer signal surfaces if bug exists

---

## Build integration changes

### CMakeLists.txt
Pattern should mirror existing decode harness target section.

Need to add:
- `add_executable(open_htj2k_parse_memory_harness fuzz/parse_memory_harness.cpp)`
- include dirs
- link with `open_htj2k`
- `open_htj2k_parse_memory_fuzzer` target with `OPENHTJ2K_LIBFUZZER`
- libFuzzer sanitizer compile/link flags matching current decode harness style

### scripts/build-libfuzzer.sh
Add builds for:
- `open_htj2k_parse_memory_fuzzer`
- `open_htj2k_parse_memory_harness`

---

## Seed guidance for this harness

Best paired seeds:
- near-valid truncated codestreams
- malformed marker length seeds
- marker sequence corruption seeds
- short but structurally plausible parser inputs

Avoid using only:
- fully random garbage
- decode-heavy toxic seeds already known to crash deep lifecycle first

---

## Success criteria

- build target exists
- CLI harness works on valid inputs
- bounded fuzz run starts cleanly
- parser-side crash yield improves or parser-side bug isolation becomes easier
- role overlap with decode harness remains acceptable

---

## Bottom line

`parse_memory_harness.cpp` should be implemented as a **minimal, parser-focused sibling** of `decode_memory_harness.cpp`, not as a clone with minor wording changes.
Its job is to isolate parser/marker memory-safety findings and shorten time-to-parser-crash.
