# Duplicate Crash Replay Execution

- status: completed
- crash_fingerprint: asan|coding_units.cpp:3076|SEGV /home/hermes/work/fuzzing-jpeg2000/source/core/coding/coding_units.cpp:3076:16 in j2k_tile::add_tile_part(SOT_marker&, j2c_src_memory&, j2k_main_header&)
- replay_harness_path: /home/hermes/work/fuzzing-jpeg2000/build-fuzz-libfuzzer/bin/open_htj2k_deep_decode_focus_v3_harness
- first_artifact_path: /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_182632_1d5b676/crashes/crash-5a7442f89cdfd35db10098c2966f3b3296ab8d76
- latest_artifact_path: /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_205450_1d5b676/crashes/crash-a54fa005c53939e5b74e7ab86fe5d5df98eb2f9a
- replay_artifact_bytes_equal: False
- first_replay_exit_code: -6
- latest_replay_exit_code: -6
- first_replay_signature: {'kind': 'asan', 'location': 'coding_units.cpp:3076', 'summary': 'SEGV /home/hermes/work/fuzzing-jpeg2000/source/core/coding/coding_units.cpp:3076:16 in j2k_tile::add_tile_part(SOT_marker&, j2c_src_memory&, j2k_main_header&)', 'artifact_path': None, 'artifact_sha1': None, 'fingerprint': 'asan|coding_units.cpp:3076|SEGV /home/hermes/work/fuzzing-jpeg2000/source/core/coding/coding_units.cpp:3076:16 in j2k_tile::add_tile_part(SOT_marker&, j2c_src_memory&, j2k_main_header&)'}
- latest_replay_signature: {'kind': 'asan', 'location': 'coding_units.cpp:3076', 'summary': 'SEGV /home/hermes/work/fuzzing-jpeg2000/source/core/coding/coding_units.cpp:3076:16 in j2k_tile::add_tile_part(SOT_marker&, j2c_src_memory&, j2k_main_header&)', 'artifact_path': None, 'artifact_sha1': None, 'fingerprint': 'asan|coding_units.cpp:3076|SEGV /home/hermes/work/fuzzing-jpeg2000/source/core/coding/coding_units.cpp:3076:16 in j2k_tile::add_tile_part(SOT_marker&, j2c_src_memory&, j2k_main_header&)'}
- first_replay_log_path: /home/hermes/work/fuzzing-jpeg2000/fuzz-records/duplicate-crash-replays/home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_205450_1d5b676-first.log
- latest_replay_log_path: /home/hermes/work/fuzzing-jpeg2000/fuzz-records/duplicate-crash-replays/home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_205450_1d5b676-latest.log

## Replay Signals

- first: ['AddressSanitizer:DEADLYSIGNAL', '==558166==ERROR: AddressSanitizer: SEGV on unknown address 0x51600025b124 (pc 0x58b9b84b1d70 bp 0x7ffd9d4db970 sp 0x7ffd9d4db8a0 T0)', 'AddressSanitizer can not provide additional info.', 'SUMMARY: AddressSanitizer: SEGV /home/hermes/work/fuzzing-jpeg2000/source/core/coding/coding_units.cpp:3076:16 in j2k_tile::add_tile_part(SOT_marker&, j2c_src_memory&, j2k_main_header&)']
- latest: ['AddressSanitizer:DEADLYSIGNAL', '==558170==ERROR: AddressSanitizer: SEGV on unknown address 0x516000445cb4 (pc 0x642fcde60d70 bp 0x7ffdb4bb13d0 sp 0x7ffdb4bb1300 T0)', 'AddressSanitizer can not provide additional info.', 'SUMMARY: AddressSanitizer: SEGV /home/hermes/work/fuzzing-jpeg2000/source/core/coding/coding_units.cpp:3076:16 in j2k_tile::add_tile_part(SOT_marker&, j2c_src_memory&, j2k_main_header&)']
