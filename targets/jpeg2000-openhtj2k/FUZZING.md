# Fuzzing Notes

This repository contains a minimal memory-buffer decoder harness for
OpenHTJ2K.  The first target is intentionally simple:

```text
bytes -> openhtj2k_decoder(data, size, reduce=0, threads=1) -> parse() -> invoke()
```

RTP, streaming reuse, and multi-threaded decode paths are out of scope for the
first harness.

## Linux / Proxmox ASan build

Install the usual C++ build tools, Clang, CMake, and Ninja, then run:

```bash
bash scripts/build-linux-asan.sh
bash scripts/run-smoke.sh
```

The build script enables:

```text
-DOPENHTJ2K_FUZZ_HARNESS=ON
-DOPENHTJ2K_FUZZ_SANITIZERS=address,undefined
-DCMAKE_DISABLE_FIND_PACKAGE_Threads=ON
-DENABLE_AVX2=OFF
```

The smoke script sets:

```text
ASAN_OPTIONS=abort_on_error=1:detect_leaks=1:strict_string_checks=1:check_initialization_order=1
UBSAN_OPTIONS=print_stacktrace=1:halt_on_error=1
```

If a mutated input does not crash, report the command line, exit code, stderr,
and whether the process printed `decoder accepted input` or `decoder rejected
input`.  If it does crash, keep the sanitizer report and the input that caused
the crash.

## Initial valid seeds

Use the smallest conformance codestreams first:

```text
conformance_data/ds0_ht_12_b11.j2k
conformance_data/p0_11.j2k
conformance_data/p0_12.j2k
```
