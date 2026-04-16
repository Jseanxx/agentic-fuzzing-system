# OpenHTJ2K deep decode v3 status

## What changed from v2
- Added `fuzz/deep_decode_focus_v3_harness.cpp`
- v3 intentionally removes the explicit metadata getter probes that were amplifying shallow header/null-deref crashes in v2
- v3 keeps repeated `decoder.init()` / `decoder.parse()` lifecycle pressure, but only performs a deep decode stage on the first pass
- Primary deep stage is selected deterministically from input size so the pristine valid seeds do not require header-byte mutation to choose a decode path
- Current baseline split:
  - `p0_11.j2k` → line-based decode
  - `ds0_ht_12_b11.j2k` → full decode

## v3 seed corpus
- Directory: `fuzz/corpus-afl/deep-decode-v3/`
- Current curated seeds:
  - `p0_11.j2k`
  - `ds0_ht_12_b11.j2k`
  - `ds0_ht_12_b11.tailcut-focus.j2k`
  - `p0_11.latebodyflip.j2k`
- Philosophy:
  - keep 2 stable valid baselines
  - keep 1 tailcut decode-focused seed
  - keep 1 late-body mutation that preserves the early header

## Local verification
- `python3 -m unittest tests/test_deep_decode_v3_harness.py -v` → OK
- full harness suite (19 tests) → OK
- `bash scripts/build-libfuzzer.sh` → OK
- smoke:
  - `open_htj2k_deep_decode_focus_v3_harness --expect-ok fuzz/corpus-afl/deep-decode-v3/p0_11.j2k` → OK
  - `open_htj2k_deep_decode_focus_v3_harness --expect-ok fuzz/corpus-afl/deep-decode-v3/ds0_ht_12_b11.j2k` → OK
- short libFuzzer sanity found a more interesting write-flavor crash:
  - `coding_units.cpp:3076`
  - `j2k_tile::add_tile_part(...)`
  - ASan SEGV on WRITE access

## Remote verification (js@proxmox)
- `tests/test_deep_decode_v3_harness.py` → OK
- `bash scripts/build-aflpp.sh` → OK
- remote valid-seed smoke → OK for both stable seeds
- 30s AFL++ smoke on v3:
  - `saved_crashes`: 20
  - `saved_hangs`: 1
  - `bitmap_cvg`: 11.15%
  - `stability`: 100.00%

## Current overnight run
- run root: `/home/js/work/fuzzing-jpeg2000-runs/deep-decode-v3-20260415_072003`
- mode: `deep-decode-v3`
- watcher cron: `openhtj2k-deep-decode-v3-watch-r2`

## Cold assessment
- v3 is not perfect; OpenHTJ2K still exposes shallow `get_max_safe_reduce_NL()`-adjacent crashes inside decode entrypoints.
- But v3 is a real improvement over v2 because it no longer *adds* extra shallow metadata-getter probes in the harness itself.
- More importantly, v3 already reproduced a deeper, higher-value signal locally:
  - `j2k_tile::add_tile_part(...)` write-flavor SEGV
- So the practical outcome is good: v3 is stable enough for overnight use and more aligned with decode/tile/block bug hunting than v2.
