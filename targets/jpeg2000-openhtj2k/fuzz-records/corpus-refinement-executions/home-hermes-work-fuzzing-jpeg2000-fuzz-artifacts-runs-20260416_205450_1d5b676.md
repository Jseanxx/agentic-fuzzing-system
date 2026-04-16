# Corpus Refinement Execution

- status: completed
- crash_fingerprint: asan|coding_units.cpp:3076|SEGV /home/hermes/work/fuzzing-jpeg2000/source/core/coding/coding_units.cpp:3076:16 in j2k_tile::add_tile_part(SOT_marker&, j2c_src_memory&, j2k_main_header&)
- latest_artifact_path: /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_205450_1d5b676/crashes/crash-a54fa005c53939e5b74e7ab86fe5d5df98eb2f9a
- triage_bucket_path: /home/hermes/work/fuzzing-jpeg2000/fuzz/corpus/triage/crash-a54fa005c53939e5b74e7ab86fe5d5df98eb2f9a
- regression_bucket_path: /home/hermes/work/fuzzing-jpeg2000/fuzz/corpus/regression/crash-a54fa005c53939e5b74e7ab86fe5d5df98eb2f9a
- known_bad_bucket_path: /home/hermes/work/fuzzing-jpeg2000/fuzz/corpus/known-bad/crash-a54fa005c53939e5b74e7ab86fe5d5df98eb2f9a
- retention_replay_status: completed
- retention_replay_exit_code: -6
- retention_replay_signature: {'kind': 'asan', 'location': 'coding_units.cpp:3076', 'summary': 'SEGV /home/hermes/work/fuzzing-jpeg2000/source/core/coding/coding_units.cpp:3076:16 in j2k_tile::add_tile_part(SOT_marker&, j2c_src_memory&, j2k_main_header&)', 'artifact_path': None, 'artifact_sha1': None, 'fingerprint': 'asan|coding_units.cpp:3076|SEGV /home/hermes/work/fuzzing-jpeg2000/source/core/coding/coding_units.cpp:3076:16 in j2k_tile::add_tile_part(SOT_marker&, j2c_src_memory&, j2k_main_header&)'}
- retention_replay_log_path: /home/hermes/work/fuzzing-jpeg2000/fuzz-records/corpus-refinement-executions/home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_205450_1d5b676-retention-replay.log

## Retention Replay Signals

- signals: ['AddressSanitizer:DEADLYSIGNAL', '==559395==ERROR: AddressSanitizer: SEGV on unknown address 0x516000445cb4 (pc 0x58176849dd70 bp 0x7ffe4eb1c2d0 sp 0x7ffe4eb1c200 T0)', 'AddressSanitizer can not provide additional info.', 'SUMMARY: AddressSanitizer: SEGV /home/hermes/work/fuzzing-jpeg2000/source/core/coding/coding_units.cpp:3076:16 in j2k_tile::add_tile_part(SOT_marker&, j2c_src_memory&, j2k_main_header&)']
