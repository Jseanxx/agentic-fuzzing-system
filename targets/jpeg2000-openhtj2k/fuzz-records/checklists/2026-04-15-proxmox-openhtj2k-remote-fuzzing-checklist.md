# Proxmox OpenHTJ2K remote fuzzing checklist

Date: 2026-04-15
Target host: `proxmox-js`
Remote user: `js`
Primary target: `OpenHTJ2K` decode path
Primary repository candidate: `https://github.com/Jseanxx/fuzzing-jpeg2000.git`

## Goal

Use the user's sleep time to run **careful remote fuzzing** on Proxmox without pretending the system is more mature than it is.

The remote goal is:
- clone the project
- build sanitizer-enabled fuzz target
- validate smoke behavior
- stage corpus buckets
- run a bounded first remote fuzz campaign
- preserve artifacts and logs for later triage

---

## Phase 0 — Safety and framing

- [x] Do not treat this as full autonomy
- [x] Prefer reproducible bounded runs first
- [x] Keep local WSL as the control/reference environment
- [ ] Decide whether first remote run is:
  - short triage reproduction
  - short coverage-growth probe
  - overnight bounded campaign

---

## Phase 1 — Remote environment readiness

- [x] SSH access works (`ssh proxmox-js`)
- [x] remote work root exists (`/home/js/work`)
- [x] `git` exists
- [x] `clang` / `clang++` exist
- [x] `cmake` exists
- [x] `ninja` exists
- [x] `python3` exists
- [x] CPU count checked (`7`)
- [ ] disk free space check
- [ ] memory availability check
- [ ] long-run output/log location check

---

## Phase 2 — Repository setup

- [x] clone `fuzzing-jpeg2000` into `/home/js/work/fuzzing-jpeg2000`
- [x] verify branch / commit
- [x] verify scripts exist:
  - `scripts/build-libfuzzer.sh`
  - `scripts/run-smoke.sh`
  - `scripts/run-fuzz-mode.sh` (synced from local working tree)
- [x] verify `fuzz/decode_memory_harness.cpp` exists remotely

---

## Phase 3 — Target and harness stance

## Primary remote target

Use the existing memory-buffer decoder harness first:
- file: `fuzz/decode_memory_harness.cpp`
- core path: `DecodeOneInput(data, size, verbose)`
- libFuzzer entry: `LLVMFuzzerTestOneInput`

## Why this is the right first remote target

- it already reaches a real decoder path
- it already produced sanitizer-visible failures locally
- it constructs a fresh decoder per input
- it frees output planes after decode
- it is a realistic crash/UAF candidate surface because it stresses:
  - parser behavior
  - tile/codeblock decode
  - output allocation/free lifecycle

## Expected bug classes to care about

- UBSan arithmetic/overflow issues
- ASan heap-buffer overflow / OOB reads-writes
- use-after-free if decoder output/object lifetime assumptions are wrong
- invalid frees / double frees
- leaks on exceptional decode paths
- timeout / pathological decompression paths

## Harness quality checks

- [ ] one input -> one fresh decoder object
- [ ] all allocated decode planes freed on both success and failure paths
- [ ] exception paths do not leak or reuse stale pointers
- [ ] no hidden global state dependence across iterations
- [ ] fuzz entry returns 0 and leaves sanitizer to report memory bugs

---

## Phase 4 — Seed and corpus strategy

## Start small, not broad

Use a curated seed set first:
- known-good baseline decodable seeds
- known-bad regression/triage seed (`p0_12.j2k` lineage)
- avoid throwing a giant mixed corpus at the first remote run

## Bucket plan

- `fuzz/corpus/coverage/`
  - clean-ish seeds for coverage growth
- `fuzz/corpus/regression/`
  - baseline failing or must-recheck seeds
- `fuzz/corpus/known-bad/`
  - crash artifacts / already known toxic seeds
- `fuzz/corpus/triage/`
  - immediate reproducer-oriented seeds

## Seed goals

- [ ] confirm clean seeds still decode
- [ ] confirm known-bad seed still reproduces expected sanitizer behavior
- [ ] keep coverage seeds separated from instant-crash seeds
- [ ] preserve all crash artifacts as separate files, not just hashes

---

## Phase 5 — Build and sanitizer stance

## First remote build policy

Prefer observability over speed.

Initial sanitizer stance:
- AddressSanitizer: on
- UndefinedBehaviorSanitizer: on
- leak detection: on for triage/regression
- leak detection: optionally relaxed later for coverage growth

## Initial build checklist

- [x] run `scripts/build-libfuzzer.sh`
- [x] confirm target binary exists
- [x] confirm compile flags still include sanitizer config
- [x] preserve build log under remote artifact directory

---

## Phase 6 — First remote validation run

## Recommended order

1. smoke
2. triage
3. bounded regression
4. bounded coverage

## Concrete first-pass idea

- smoke run to verify environment parity
- short triage run to verify known issue reproduction
- short bounded regression run
- only then run bounded coverage mode

## Validation checklist

- [x] smoke output captured
- [x] crash / sanitizer output captured
- [x] run directory created predictably
- [x] `FUZZING_REPORT.md` generated
- [x] `status.json` / `current_status.json` updated
- [x] crash artifact preserved if created

---

## Phase 7 — Sleep-time campaign design

## Conservative overnight plan

Use bounded runtime rather than infinite fuzzing on night one.

Suggested philosophy:
- first night: prove remote loop stability
- second night onward: longer campaigns

## Night-one goals

- [ ] no environment/config breakage
- [ ] at least one meaningful report written
- [ ] crash or regression reproduction confirmed if expected
- [ ] no silent failure where process dies without artifacts

---

## Phase 8 — Post-run triage requirements

- [ ] copy back or inspect remote artifacts
- [ ] compare remote findings with local WSL behavior
- [ ] decide whether bug is:
  - already known
  - remotely reproducible only
  - worth turning into dedicated regression seed
- [ ] update local notes/limitations/checklist after review

---

## Cold strategy note

The current best first remote approach is **not** “invent a brand-new complex harness before sleep.”

It is:
1. reuse the already working decode-memory harness
2. reuse known-good and known-bad seeds
3. verify remote reproducibility
4. only then iterate on deeper harness ideas

That is the highest signal-per-risk move right now.
