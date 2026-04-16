# Duplicate Crash Replay Execution

- status: completed
- crash_fingerprint: asan|j2kmarkers.cpp:52|heap-buffer-overflow /home/hermes/work/fuzzing-jpeg2000/source/core/codestream/j2kmarkers.cpp:52:17 in j2k_marker_io_base::get_byte()
- replay_harness_path: /home/hermes/work/fuzzing-jpeg2000/build-fuzz-libfuzzer/bin/open_htj2k_deep_decode_focus_v3_harness
- first_artifact_path: /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_200858_1d5b676/crashes/crash-964206b1bbf197c651b1198941e6e35a8830b2bf
- latest_artifact_path: /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_202702_1d5b676/crashes/crash-5e1dbfc1e1257014678913af52217fa8eb380818
- replay_artifact_bytes_equal: False
- first_replay_exit_code: -6
- latest_replay_exit_code: -6
- first_replay_signature: {'kind': 'asan', 'location': 'j2kmarkers.cpp:52', 'summary': 'heap-buffer-overflow /home/hermes/work/fuzzing-jpeg2000/source/core/codestream/j2kmarkers.cpp:52:17 in j2k_marker_io_base::get_byte()', 'artifact_path': None, 'artifact_sha1': None, 'fingerprint': 'asan|j2kmarkers.cpp:52|heap-buffer-overflow /home/hermes/work/fuzzing-jpeg2000/source/core/codestream/j2kmarkers.cpp:52:17 in j2k_marker_io_base::get_byte()'}
- latest_replay_signature: {'kind': 'asan', 'location': 'j2kmarkers.cpp:52', 'summary': 'heap-buffer-overflow /home/hermes/work/fuzzing-jpeg2000/source/core/codestream/j2kmarkers.cpp:52:17 in j2k_marker_io_base::get_byte()', 'artifact_path': None, 'artifact_sha1': None, 'fingerprint': 'asan|j2kmarkers.cpp:52|heap-buffer-overflow /home/hermes/work/fuzzing-jpeg2000/source/core/codestream/j2kmarkers.cpp:52:17 in j2k_marker_io_base::get_byte()'}
- first_replay_log_path: /home/hermes/work/fuzzing-jpeg2000/fuzz-records/duplicate-crash-replays/home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_202702_1d5b676-first.log
- latest_replay_log_path: /home/hermes/work/fuzzing-jpeg2000/fuzz-records/duplicate-crash-replays/home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_202702_1d5b676-latest.log

## Replay Signals

- first: ['==553387==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x511000000108 at pc 0x5b7c13d94eaf bp 0x7ffefd3b7800 sp 0x7ffefd3b77f8', 'SUMMARY: AddressSanitizer: heap-buffer-overflow /home/hermes/work/fuzzing-jpeg2000/source/core/codestream/j2kmarkers.cpp:52:17 in j2k_marker_io_base::get_byte()']
- latest: ['==553391==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x5110000000f1 at pc 0x5ae7a01e9e7b bp 0x7ffdcf9a0be0 sp 0x7ffdcf9a0bd8', 'SUMMARY: AddressSanitizer: heap-buffer-overflow /home/hermes/work/fuzzing-jpeg2000/source/core/codestream/j2kmarkers.cpp:52:17 in j2k_marker_io_base::get_byte()']
