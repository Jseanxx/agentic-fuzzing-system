# OpenHTJ2K Decoder Fuzzing Plan

## Goal

Build the first fuzzable decoder harness for OpenHTJ2K and make the workflow
easy to reproduce on a Proxmox Linux machine after a fresh `git clone`.

The security focus is memory-safety bugs in the decoder path:

- use-after-free
- heap-buffer-overflow
- out-of-bounds read/write
- other sanitizer-detectable undefined behavior

This is not an n8n, webhook, automation, or long-running orchestration project.
The first milestone is a single minimal decoder harness with useful debugging
signals.

## Scope For The First Harness

Included:

- memory-buffer input
- fresh decoder object per input
- `parse()` followed by full batch `invoke()`
- simple state setup and cleanup
- normal conformance sample smoke tests
- ASan/UBSan-ready Linux build path

Excluded for v1:

- RTP receiver path
- streaming reuse path
- long-lived decoder reuse
- multi-threaded decode path
- complicated output writing
- broad refactoring

## Entry Candidates Reviewed

1. `open_htj2k::openhtj2k_decoder(const uint8_t*, size_t, ...) -> parse() -> invoke()`
   - Direct memory input.
   - Covers JPH/JP2 wrapper detection and raw codestream input.
   - Reaches main header parsing, tile-part parsing, packet parsing, block
     decode, IDWT, and finalization.
   - Chosen for the first harness because state is the simplest.

2. `open_htj2k::openhtj2k_decoder::init(const uint8_t*, size_t, ...) -> parse() -> invoke_line_based()`
   - Direct memory input.
   - Good later target for line-based IDWT behavior.
   - More stateful than batch decode.

3. `open_htj2k::openhtj2k_decoder::init/constructor(...) -> parse() -> invoke_line_based_stream(callback)`
   - Direct memory input.
   - Useful later for streaming behavior.
   - Callback-driven and more complex for a first harness.

The reuse variant `invoke_line_based_stream_reuse()` is intentionally excluded
from v1 because it brings cache/reuse state and RTP-adjacent assumptions.

## Chosen Target

The selected target is:

```text
bytes -> openhtj2k_decoder(data, size, reduce=0, threads=1) -> parse() -> invoke()
```

Implementation file:

```text
fuzz/decode_memory_harness.cpp
```

The harness has a `DecodeOneInput(data, size)` shape and also exposes
`LLVMFuzzerTestOneInput`, so it can be converted into a libFuzzer target
without rewriting the decode logic.

## Current Build State

Implemented so far:

- `OPENHTJ2K_FUZZ_HARNESS=ON` CMake option.
- `OPENHTJ2K_FUZZ_SANITIZERS` CMake cache string.
- Linux-style sanitizer path for `address,undefined`.
- MSVC `address` sanitizer handling for local smoke-build checks.
- Linux/Proxmox helper scripts:
  - `scripts/build-linux-asan.sh`
  - `scripts/run-smoke.sh`

The current Proxmox-oriented sanitizer build is:

```bash
bash scripts/build-linux-asan.sh
bash scripts/run-smoke.sh
```

The build script intentionally uses:

```text
-DOPENHTJ2K_FUZZ_HARNESS=ON
-DOPENHTJ2K_FUZZ_SANITIZERS=address,undefined
-DCMAKE_DISABLE_FIND_PACKAGE_Threads=ON
-DENABLE_AVX2=OFF
```

Rationale:

- ASan/UBSan gives useful memory-safety diagnostics.
- Frame pointers and debug info make stack traces easier to send back to an LLM.
- Threading is disabled for the first version to keep failures easier to
  reproduce and reason about.
- AVX2 is disabled for the first Linux fuzz/debug build to reduce SIMD-specific
  noise while validating harness depth.

## Current Seed Strategy

Small valid seeds from `conformance_data`:

```text
conformance_data/ds0_ht_12_b11.j2k
conformance_data/p0_11.j2k
conformance_data/p0_12.j2k
```

Useful later seed families:

```text
conformance_data/ds0_ht_11_b10.j2k
conformance_data/ds0_ht_09_b11.j2k
conformance_data/p1_07.j2k
conformance_data/ds1_ht_06_b11.j2k
conformance_data/p1_06.j2k
conformance_data/ds0_ht_02_b11.j2k
```

Broken seeds should be handled carefully. A manually mutated seed already
triggered a Windows debug assertion/access violation during local testing.
Do not publish potentially vulnerability-revealing crash seeds until they have
been triaged.

## What The User Actually Needs

The user does not only want a harness that sometimes crashes. The user needs
debugging metrics that can be sent back to an LLM to decide how to improve the
harness.

If a crash occurs, collect:

- crashing input path
- exact command line
- sanitizer report
- stack trace
- exit code
- whether the crash is reproducible

If no crash occurs, collect:

- command line
- runtime
- exit code
- stderr
- accepted/rejected input counts
- libFuzzer `cov`, `ft`, and corpus growth once libFuzzer is added
- coverage report once coverage instrumentation is added

Important decoder reachability questions:

- Did execution reach `openhtj2k_decoder::parse()`?
- Did execution reach `openhtj2k_decoder::invoke()`?
- Did execution reach `j2k_main_header::read()`?
- Did execution reach `j2k_tile::add_tile_part()`?
- Did execution reach `j2k_tile::create_tile_buf()`?
- Did execution reach `j2k_tile::decode()`?
- Did execution reach `htj2k_decode()` or `j2k_decode()`?

These signals matter because a non-crashing run is only useful if we know
whether the harness is reaching deep decoder code or rejecting most inputs near
the header parser.

## Next Work

1. Push the current harness and scripts to:

```text
https://github.com/Jseanxx/fuzzing-jpeg2000.git
```

Recommended remote setup from the local OpenHTJ2K checkout:

```powershell
git remote add fuzzing https://github.com/Jseanxx/fuzzing-jpeg2000.git
git checkout -b harness/minimal-decoder
git push -u fuzzing harness/minimal-decoder
```

2. On Proxmox, clone and run the ASan smoke build:

```bash
git clone https://github.com/Jseanxx/fuzzing-jpeg2000.git
cd fuzzing-jpeg2000
bash scripts/build-linux-asan.sh
bash scripts/run-smoke.sh
```

3. Add the real libFuzzer target:

```text
open_htj2k_decode_memory_fuzzer
```

It should build with:

```text
-fsanitize=fuzzer,address,undefined
```

The existing `LLVMFuzzerTestOneInput` in `fuzz/decode_memory_harness.cpp`
should be reused.

4. Add a coverage/report workflow that produces an LLM-friendly summary:

```text
FUZZING_REPORT.md
```

Minimum report fields:

- build flags
- sanitizer settings
- seed corpus used
- run duration
- exec/s
- corpus size
- libFuzzer `cov` and `ft`
- accepted/rejected/crashed/timeout counts if available
- key decoder functions reached
- sanitizer reports and reproducer commands for crashes

5. Only after the first batch harness has useful metrics, consider a second
harness for `invoke_line_based()` or `invoke_line_based_stream()`.
