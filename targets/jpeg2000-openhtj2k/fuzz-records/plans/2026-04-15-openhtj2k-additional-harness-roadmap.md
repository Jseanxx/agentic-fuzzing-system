# OpenHTJ2K Additional Harness Implementation Roadmap

Date: 2026-04-15
Repo: `/home/hermes/work/fuzzing-jpeg2000`

## Scope
This roadmap links the two new harnesses:
- `fuzz/parse_memory_harness.cpp`
- `fuzz/cleanup_memory_harness.cpp`

and defines the order they should be implemented in practice.

---

## Recommended order

### Step 1 — Implement `parse_memory_harness.cpp` first
Reason:
- shallower than cleanup harness
- easier to wire into CMake/build
- likely to produce quick parser-side signal
- good first TDD exercise

### Step 2 — Validate parser-focused seed subset
Reason:
- prevents mixing parser-noise with full decode corpus too early
- helps establish whether parser harness is actually distinct in value

### Step 3 — Implement `cleanup_memory_harness.cpp`
Reason:
- more stateful and subtle
- better done after parser harness wiring pattern is already proven

### Step 4 — Compare all three harnesses
Harness set:
- `decode_memory_harness.cpp`
- `parse_memory_harness.cpp`
- `cleanup_memory_harness.cpp`

Compare on:
- distinct crash count
- crash class quality
- parser-side vs lifecycle-side balance
- duplicate fixation

---

## Immediate implementation file list

- `fuzz/parse_memory_harness.cpp` (new)
- `fuzz/cleanup_memory_harness.cpp` (new)
- `CMakeLists.txt` (modify)
- `scripts/build-libfuzzer.sh` (modify)
- optional smoke tests or harness CLI tests under `tests/`

---

## Minimum build target names

- `open_htj2k_parse_memory_harness`
- `open_htj2k_parse_memory_fuzzer`
- `open_htj2k_cleanup_memory_harness`
- `open_htj2k_cleanup_memory_fuzzer`

---

## TDD rule reminder

For each harness:
1. write the failing build/CLI test expectation first
2. run and confirm failure
3. implement minimal harness
4. run targeted test
5. run full relevant test suite
6. only then compare fuzz behavior

---

## Practical next move

If implementation starts now, the best next concrete action is:
- first write the CMake/build integration failing test expectation for `parse_memory_harness.cpp`
- then add the minimal parser-focused harness skeleton

That is the fastest honest TDD path.
