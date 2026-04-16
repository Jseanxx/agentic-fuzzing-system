# OpenHTJ2K deep decode v3 checklist

> Goal: use v2 crash feedback to push coverage away from shallow metadata/parser failures and toward higher-value decode/block/tile/lifecycle bugs for overnight AFL++.

## Feedback from v2
- Too many shallow crashes from metadata getters / header-derived null deref paths
- Valuable deeper findings exist in:
  - `ht_block_decoding.cpp`
  - `coding_units.cpp:create_subbands`
  - `coding_units.cpp:decode_line_based`
  - `idwt.cpp`
- Need a v3 harness that preserves deep decode pressure while suppressing easy shallow crashes

## v3 implementation checklist
- [ ] Define v3 harness objectives in code comments
- [ ] Create new harness file for decode-focused v3
- [ ] Bias v3 toward `invoke_line_based()` and full decode paths
- [ ] Only touch metadata after a deep decode stage succeeds, or remove shallow getter probes entirely
- [ ] Reuse decoder across `init()/parse()` cycles to preserve lifecycle pressure
- [ ] Add at least one alternate deep stage to vary decode behavior without regressing into parser-only paths
- [ ] Create curated `fuzz/corpus-afl/deep-decode-v3/`
- [ ] Keep only seeds that survive smoke and still reach deep decode
- [ ] Add failing tests for CMake/build/run/seed wiring
- [ ] Make tests pass
- [ ] Build libFuzzer and AFL++ targets locally
- [ ] Run local smoke on valid seeds
- [ ] Run short local sanity fuzz if possible
- [ ] Sync to `js@proxmox`
- [ ] Run remote smoke and short AFL++ validation
- [ ] Version the remote overnight run under `/home/js/work/fuzzing-jpeg2000-runs/`
- [ ] Start v3 overnight campaign in background
- [ ] Record v3 status and cold assessment in notes

## Cold success criteria
- Valid seeds pass smoke reliably
- v3 avoids being dominated by metadata-getter shallow crashes
- short AFL++ smoke shows decode/block/tile hotspots, not just parser/header crashes
- overnight run is actually live on `js`
