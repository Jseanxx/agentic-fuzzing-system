# Follow-up Note: halt_and_review_harness

- run_dir: /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_201732_1d5b676
- report_path: /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_201732_1d5b676/FUZZING_REPORT.md
- target: open_htj2k_deep_decode_focus_v3_harness
- stage_hint: ht-block-decode
- operator_goal: verify harness determinism before any corpus or code changes

## What was verified

1. The suspicious artifact is stable and already normalized into known-bad coverage.
   - crash artifact sha1: b3c5e4eb4b2827051ee3179055e7151026e05c37
   - known-bad copy sha1: b3c5e4eb4b2827051ee3179055e7151026e05c37
   - result: exact byte-for-byte match

2. Reproduction is deterministic on the current build.
   - harness replay: 3/3 reproductions, exit status 1 each time
   - libFuzzer replay (`-runs=1`): 3/3 reproductions, exit status 134 each time
   - stable top frame and summary each time:
     - `j2k_marker_io_base::get_byte()`
     - `heap-buffer-overflow ... source/core/codestream/j2kmarkers.cpp:52:17`

3. This is a repeated crash family, not a one-off run artifact.
   - first seen run: `/home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_200858_1d5b676`
   - same crash fingerprint in both runs
   - earlier artifact differs in bytes/size, so the family is reproducible across distinct inputs

4. The fault fires during parse, before the harness reaches its explicit deep-stage dispatch.
   - crashing stack stops at `decoder.parse()` from `deep_decode_focus_v3_harness.cpp:143`
   - no evidence that `RunStage(...)` completed before abort
   - practical meaning: the reported `ht-block-decode` stage label should be treated as a signal-derived hint, not proof that the harness reached a later decode stage

5. Smoke coverage is weaker than full corpus validation.
   - run smoke log only exercised two conformance inputs and passed
   - current `fuzz/corpus-afl/deep-decode-v3` contents include several inputs that do not return `kDecoded` under `--expect-ok`
   - treat this as a harness stability warning, not as permission to delete seeds automatically

## Deterministic debugging checklist

1. Freeze the exact repro inputs before touching anything.
   - Keep the crash file in place.
   - Work from copies if you need to minimize or inspect.
   - Rollback: delete only your temporary copies.

2. Confirm the exact artifact identity.
   - Run:
     - `sha1sum fuzz-artifacts/runs/20260416_201732_1d5b676/crashes/crash-b3c5e4eb4b2827051ee3179055e7151026e05c37`
     - `sha1sum fuzz/corpus/known-bad/crash-b3c5e4eb4b2827051ee3179055e7151026e05c37`
   - Expect identical hashes.
   - Rollback: none.

3. Reconfirm deterministic replay with the standalone harness.
   - Run 3 times:
     - `build-fuzz-libfuzzer/bin/open_htj2k_deep_decode_focus_v3_harness fuzz-artifacts/runs/20260416_201732_1d5b676/crashes/crash-b3c5e4eb4b2827051ee3179055e7151026e05c37`
   - Expect ASan failure each run with the same source location.
   - Rollback: remove any temporary logs only.

4. Reconfirm deterministic replay with the libFuzzer binary.
   - Run 3 times:
     - `ASAN_OPTIONS=abort_on_error=1:symbolize=1 build-fuzz-libfuzzer/bin/open_htj2k_deep_decode_focus_v3_fuzzer -runs=1 fuzz-artifacts/runs/20260416_201732_1d5b676/crashes/crash-b3c5e4eb4b2827051ee3179055e7151026e05c37`
   - Expect exit 134 and the same ASan summary each run.
   - Rollback: remove any temporary logs only.

5. Verify whether the crash is parser-bound rather than deep-stage-bound.
   - Inspect the stack for `deep_decode_focus_v3_harness.cpp:143` (`decoder.parse()`) and absence of a later `RunStage(...)` frame.
   - If the stack remains parser-only, triage this as a header/main-marker parsing issue first.
   - Rollback: none.

6. Compare the crashing artifact with its parent seed.
   - Base seed from fuzz log: sha1 `0688e8a9e6883a1623a38a3ed6e3329ef9431c0c` = `fuzz/corpus-afl/deep-decode-v3/p0_11.j2k`
   - Mutation recorded by libFuzzer: `MS: 1 EraseBytes-`
   - Compare with:
     - `xxd -g1 -l 64 fuzz/corpus-afl/deep-decode-v3/p0_11.j2k`
     - `xxd -g1 -l 64 fuzz-artifacts/runs/20260416_201732_1d5b676/crashes/crash-b3c5e4eb4b2827051ee3179055e7151026e05c37`
   - Expect a truncated/shifted header layout consistent with malformed SIZ parsing.
   - Rollback: none.

7. Re-run a non-destructive corpus acceptance check on the current deep-decode-v3 seeds.
   - Run:
     - `for f in fuzz/corpus-afl/deep-decode-v3/*; do build-fuzz-libfuzzer/bin/open_htj2k_deep_decode_focus_v3_harness --expect-ok "$f"; done`
   - Current observation: some hashed corpus entries fail `--expect-ok` while named conformance-style files pass.
   - Action: log which seeds fail, but do not delete or rewrite the corpus automatically.
   - Rollback: none unless you create side files.

8. Before proposing any patch, verify the bounds assumption at the fault site.
   - Inspect:
     - `source/core/codestream/j2kmarkers.cpp:50-90`
   - Key condition: `get_byte()` relies on `assert(pos < Lmar)`, which disappears in release-like configurations and is not a runtime guard.
   - Rollback: none.

## Safe follow-up tasks for the main operator

- Keep this crash family recorded as duplicate/known-bad coverage.
- Triage the bug as parser/main-header bounds handling first, not as confirmed late decode instability.
- Expand smoke validation to include the actual deep-decode-v3 corpus or a fixed representative subset before trusting future harness-stability conclusions.
- If a code fix is later proposed, require an explicit patch review plus replay on:
  - the known-bad artifact above
  - the first-seen artifact from the prior run
  - the current passing conformance inputs
