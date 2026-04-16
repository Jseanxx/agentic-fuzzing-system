# Refiner Plan: review_duplicate_crash_replay

- run_dir: /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_202702_1d5b676
- report_path: /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_202702_1d5b676/FUZZING_REPORT.md
- outcome: crash
- recommended_action: Preserve duplicate family evidence, compare first and latest repros, and prepare replay/minimization triage instead of only filing this as known-bad.

## Duplicate Crash Comparison

- occurrence_count: 3
- crash_fingerprint: asan|j2kmarkers.cpp:52|heap-buffer-overflow /home/hermes/work/fuzzing-jpeg2000/source/core/codestream/j2kmarkers.cpp:52:17 in j2k_marker_io_base::get_byte()
- crash_location: j2kmarkers.cpp:52
- crash_summary: heap-buffer-overflow /home/hermes/work/fuzzing-jpeg2000/source/core/codestream/j2kmarkers.cpp:52:17 in j2k_marker_io_base::get_byte()
- first_seen_run: /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_200858_1d5b676
- first_seen_report_path: /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_200858_1d5b676/FUZZING_REPORT.md
- latest_run: /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_202702_1d5b676
- latest_report_path: /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_202702_1d5b676/FUZZING_REPORT.md
- first_artifact_path: /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_200858_1d5b676/crashes/crash-964206b1bbf197c651b1198941e6e35a8830b2bf
- latest_artifact_path: /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_202702_1d5b676/crashes/crash-5e1dbfc1e1257014678913af52217fa8eb380818

## Suggested Low-Risk Commands

- sha1sum /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_200858_1d5b676/crashes/crash-964206b1bbf197c651b1198941e6e35a8830b2bf /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_202702_1d5b676/crashes/crash-5e1dbfc1e1257014678913af52217fa8eb380818
- cmp -l /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_200858_1d5b676/crashes/crash-964206b1bbf197c651b1198941e6e35a8830b2bf /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_202702_1d5b676/crashes/crash-5e1dbfc1e1257014678913af52217fa8eb380818 || true
- sed -n '1,160p' /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_200858_1d5b676/FUZZING_REPORT.md
- sed -n '1,160p' /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_202702_1d5b676/FUZZING_REPORT.md

## Replay Execution

- replay_execution_status: completed
- replay_execution_markdown_path: /home/hermes/work/fuzzing-jpeg2000/fuzz-records/duplicate-crash-replays/home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_202702_1d5b676.md
- replay_harness_path: /home/hermes/work/fuzzing-jpeg2000/build-fuzz-libfuzzer/bin/open_htj2k_deep_decode_focus_v3_harness
- replay_artifact_bytes_equal: False
- first_replay_exit_code: -6
- latest_replay_exit_code: -6
- first_replay_signature: {'kind': 'asan', 'location': 'j2kmarkers.cpp:52', 'summary': 'heap-buffer-overflow /home/hermes/work/fuzzing-jpeg2000/source/core/codestream/j2kmarkers.cpp:52:17 in j2k_marker_io_base::get_byte()', 'artifact_path': None, 'artifact_sha1': None, 'fingerprint': 'asan|j2kmarkers.cpp:52|heap-buffer-overflow /home/hermes/work/fuzzing-jpeg2000/source/core/codestream/j2kmarkers.cpp:52:17 in j2k_marker_io_base::get_byte()'}
- latest_replay_signature: {'kind': 'asan', 'location': 'j2kmarkers.cpp:52', 'summary': 'heap-buffer-overflow /home/hermes/work/fuzzing-jpeg2000/source/core/codestream/j2kmarkers.cpp:52:17 in j2k_marker_io_base::get_byte()', 'artifact_path': None, 'artifact_sha1': None, 'fingerprint': 'asan|j2kmarkers.cpp:52|heap-buffer-overflow /home/hermes/work/fuzzing-jpeg2000/source/core/codestream/j2kmarkers.cpp:52:17 in j2k_marker_io_base::get_byte()'}

## Notes

- Auto-generated low-risk executor draft.
- Review this plan before any destructive corpus or harness mutation.
