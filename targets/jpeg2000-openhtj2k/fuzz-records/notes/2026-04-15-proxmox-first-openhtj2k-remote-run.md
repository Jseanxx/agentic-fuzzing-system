# Proxmox first remote OpenHTJ2K run

Date: 2026-04-15
Host: `proxmox-js`
Remote repo: `/home/js/work/fuzzing-jpeg2000`
Remote branch: `main`
Remote commit: `1d5b676`

## What was done

1. Proxmox environment checked
   - disk available: ~49G on `/`
   - memory available: ~8.5Gi
   - `git`, `clang`, `clang++`, `cmake`, `ninja`, `python3` all present
2. repo cloned to `/home/js/work/fuzzing-jpeg2000`
3. local working-tree-only files synced to remote
   - `scripts/hermes_watch.py`
   - `scripts/run-fuzz-mode.sh`
   - `source/core/coding/coding_units.cpp`
   - `tests/test_hermes_watch.py`
   - `fuzz/corpus/`
   - `fuzz-records/`
4. remote watcher tests passed
   - `python3 -m unittest tests/test_hermes_watch.py -v`
5. sanitizer build passed
   - `bash scripts/build-libfuzzer.sh`
6. smoke reproduced the known local UBSan issue
   - `block_decoding.cpp:86:23`
   - failing baseline seed lineage: `p0_12.j2k`

## First remote fuzzing result

### Coverage run #1
Run dir:
- `/home/js/work/fuzzing-jpeg2000/fuzz-artifacts/modes/coverage/20260415_000604_coverage`

New crash found almost immediately.

Fingerprint:
- `asan|coding_units.cpp:3076|SEGV /home/js/work/fuzzing-jpeg2000/source/core/coding/coding_units.cpp:3076:16 in j2k_tile::add_tile_part(SOT_marker&, j2c_src_memory&, j2k_main_header&)`

Artifact:
- `/home/js/work/fuzzing-jpeg2000/fuzz-artifacts/modes/coverage/20260415_000604_coverage/crashes/crash-2e9e3430ad22d4e8ddac4f9c02cad921fbcdcf15`

SHA1:
- `2e9e3430ad22d4e8ddac4f9c02cad921fbcdcf15`

Observed base unit:
- `1f3c4ac5be5709e2c1043dca593be5d134cee901`

Cold read:
- this is not the old smoke UBSan issue
- it is a distinct ASan write-side crash in tile-part handling
- good signal that remote coverage fuzzing is immediately reaching bug-relevant parser/decode paths

### Immediate triage action
- crash artifact copied into remote `triage/` and `known-bad/`
- toxic base seed `1f3c4ac5be5709e2c1043dca593be5d134cee901` quarantined out of remote coverage bucket
- crash artifact reproduced with `open_htj2k_decode_memory_harness`

Harness reproduction result:
- reproducible ASan SEGV at `coding_units.cpp:3076`

## Second remote fuzzing result

### Coverage run #2 (after quarantining the toxic coverage seed)
Run dir:
- `/home/js/work/fuzzing-jpeg2000/fuzz-artifacts/modes/coverage/20260415_000731_coverage`

A second distinct crash appeared quickly.

Fingerprint:
- `asan|j2kmarkers.cpp:52|heap-buffer-overflow /home/js/work/fuzzing-jpeg2000/source/core/codestream/j2kmarkers.cpp:52:17 in j2k_marker_io_base::get_byte()`

Artifact:
- `/home/js/work/fuzzing-jpeg2000/fuzz-artifacts/modes/coverage/20260415_000731_coverage/crashes/crash-51597f0f199a894f99d0f51e1c5b6267bb21b300`

SHA1:
- `51597f0f199a894f99d0f51e1c5b6267bb21b300`

Cold read:
- this is better than just rediscovering the first crash
- it suggests the coverage corpus is not singularly trapped on one toxic path
- parser-side marker handling is also fragile enough to produce immediate ASan findings

## What this means

The remote Proxmox expansion succeeded in the most important practical sense:

- remote build works
- remote smoke reproduces known local behavior
- remote coverage fuzzing finds real sanitizer crashes immediately
- at least two distinct ASan findings were observed quickly

That is enough to justify continued remote fuzzing.

## Important caution

This does **not** mean the harness is complete or that the overnight campaign is mature.
It means the current decode-memory harness is already strong enough to hit:

- tile-part handling faults
- codestream marker parsing faults
- concrete ASan-visible memory safety failures

## Recommended next human follow-up

1. deduplicate the two new crash artifacts locally as first-class findings
2. promote them into triage/regression handling explicitly
3. decide whether coverage corpus needs another quarantine pass
4. later, consider a parser-focused secondary harness if marker parsing keeps dominating
