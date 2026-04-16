# Refiner Plan: review_duplicate_crash_replay

- run_dir: /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_205450_1d5b676
- report_path: /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_205450_1d5b676/FUZZING_REPORT.md
- outcome: crash
- recommended_action: Preserve duplicate family evidence, compare first and latest repros, and prepare replay/minimization triage instead of only filing this as known-bad.

## Duplicate Crash Comparison

- occurrence_count: 2
- crash_fingerprint: asan|coding_units.cpp:3076|SEGV /home/hermes/work/fuzzing-jpeg2000/source/core/coding/coding_units.cpp:3076:16 in j2k_tile::add_tile_part(SOT_marker&, j2c_src_memory&, j2k_main_header&)
- crash_location: coding_units.cpp:3076
- crash_summary: SEGV /home/hermes/work/fuzzing-jpeg2000/source/core/coding/coding_units.cpp:3076:16 in j2k_tile::add_tile_part(SOT_marker&, j2c_src_memory&, j2k_main_header&)
- first_seen_run: /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_182632_1d5b676
- first_seen_report_path: /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_182632_1d5b676/FUZZING_REPORT.md
- latest_run: /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_205450_1d5b676
- latest_report_path: /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_205450_1d5b676/FUZZING_REPORT.md
- first_artifact_path: /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_182632_1d5b676/crashes/crash-5a7442f89cdfd35db10098c2966f3b3296ab8d76
- latest_artifact_path: /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_205450_1d5b676/crashes/crash-a54fa005c53939e5b74e7ab86fe5d5df98eb2f9a

## Suggested Low-Risk Commands

- sha1sum /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_182632_1d5b676/crashes/crash-5a7442f89cdfd35db10098c2966f3b3296ab8d76 /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_205450_1d5b676/crashes/crash-a54fa005c53939e5b74e7ab86fe5d5df98eb2f9a
- cmp -l /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_182632_1d5b676/crashes/crash-5a7442f89cdfd35db10098c2966f3b3296ab8d76 /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_205450_1d5b676/crashes/crash-a54fa005c53939e5b74e7ab86fe5d5df98eb2f9a || true
- sed -n '1,160p' /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_182632_1d5b676/FUZZING_REPORT.md
- sed -n '1,160p' /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_205450_1d5b676/FUZZING_REPORT.md

## Replay Execution

- replay_execution_status: completed
- replay_execution_markdown_path: /home/hermes/work/fuzzing-jpeg2000/fuzz-records/duplicate-crash-replays/home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_205450_1d5b676.md
- replay_harness_path: /home/hermes/work/fuzzing-jpeg2000/build-fuzz-libfuzzer/bin/open_htj2k_deep_decode_focus_v3_harness
- replay_artifact_bytes_equal: False
- first_replay_exit_code: -6
- latest_replay_exit_code: -6
- first_replay_signature: {'kind': 'asan', 'location': 'coding_units.cpp:3076', 'summary': 'SEGV /home/hermes/work/fuzzing-jpeg2000/source/core/coding/coding_units.cpp:3076:16 in j2k_tile::add_tile_part(SOT_marker&, j2c_src_memory&, j2k_main_header&)', 'artifact_path': None, 'artifact_sha1': None, 'fingerprint': 'asan|coding_units.cpp:3076|SEGV /home/hermes/work/fuzzing-jpeg2000/source/core/coding/coding_units.cpp:3076:16 in j2k_tile::add_tile_part(SOT_marker&, j2c_src_memory&, j2k_main_header&)'}
- latest_replay_signature: {'kind': 'asan', 'location': 'coding_units.cpp:3076', 'summary': 'SEGV /home/hermes/work/fuzzing-jpeg2000/source/core/coding/coding_units.cpp:3076:16 in j2k_tile::add_tile_part(SOT_marker&, j2c_src_memory&, j2k_main_header&)', 'artifact_path': None, 'artifact_sha1': None, 'fingerprint': 'asan|coding_units.cpp:3076|SEGV /home/hermes/work/fuzzing-jpeg2000/source/core/coding/coding_units.cpp:3076:16 in j2k_tile::add_tile_part(SOT_marker&, j2c_src_memory&, j2k_main_header&)'}

## Notes

- Auto-generated low-risk executor draft.
- Review this plan before any destructive corpus or harness mutation.
