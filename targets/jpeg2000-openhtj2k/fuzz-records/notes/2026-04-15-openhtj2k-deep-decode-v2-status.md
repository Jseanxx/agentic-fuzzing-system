# OpenHTJ2K deep decode lifecycle v2 status

## Goal
Shift from parser-heavy overnight coverage toward deeper decode/lifecycle paths that are more likely to expose higher-value memory-safety bugs in tile/block/line-based decode and repeated decoder reinit paths.

## New harness
- `fuzz/deep_decode_lifecycle_harness.cpp`
- Targets:
  - `open_htj2k_deep_decode_lifecycle_harness`
  - `open_htj2k_deep_decode_lifecycle_fuzzer`

## Harness shape
- Reuses one decoder object across multiple `init()` / `parse()` cycles
- Captures decoder metadata getters after parse
- Runs one deep decode stage selected from:
  - `invoke()`
  - `invoke_line_based()`
  - `invoke_line_based_stream()`
- Re-inits on a second, closely related variant to stress lifecycle / cleanup / reparse behavior
- Keeps optional probes for:
  - `invoke_line_based_predecoded()`
  - `invoke_line_based_stream_reuse()`
  but gates them to small inputs because they were unstable / too slow on the baseline corpus

## AFL++ v2 seed corpus
- Directory: `fuzz/corpus-afl/deep-decode-v2/`
- Curated keepers:
  - `p0_11.j2k`
  - `ds0_ht_12_b11.j2k`
  - `ds0_ht_12_b11.tailcut-deep.j2k`
- Removed from v2 corpus because they crashed or degraded too early during smoke:
  - `*.bodyflip-deep.j2k`
  - `p0_11.tailcut-deep.j2k`

## Local verification
- `python3 -m unittest tests/test_deep_decode_v2_harness.py -v` → OK
- `bash scripts/build-libfuzzer.sh` → OK
- `open_htj2k_deep_decode_lifecycle_harness --expect-ok` on:
  - `fuzz/corpus/valid/p0_11.j2k` → OK
  - `fuzz/corpus/valid/ds0_ht_12_b11.j2k` → OK
- Short libFuzzer sanity on `fuzz/corpus-afl/deep-decode-v2/` found a deeper-path crash at:
  - `decoder.cpp:237`
  - `COD_marker::get_dwt_levels()`
  - null deref / SEGV via metadata getter path

## Remote smoke (js@proxmox)
- `tests/test_deep_decode_v2_harness.py` → OK
- `bash scripts/build-aflpp.sh` → OK
- 30s AFL++ smoke on `deep-decode-v2`:
  - `saved_crashes`: 19
  - `saved_hangs`: 1
  - `bitmap_cvg`: 12.54%
  - `stability`: 100.00%

## Cold assessment
- Better than v1 for deeper decode/lifecycle reach.
- Not a perfect “most dangerous bug finder” yet.
- Strong improvement because it leaves the parser-only zone and repeatedly touches decode state + reinit lifecycle.
- Still conservative about very unstable probes (`predecoded`, `reuse`) to avoid overnight runs getting stuck on the baseline corpus.
