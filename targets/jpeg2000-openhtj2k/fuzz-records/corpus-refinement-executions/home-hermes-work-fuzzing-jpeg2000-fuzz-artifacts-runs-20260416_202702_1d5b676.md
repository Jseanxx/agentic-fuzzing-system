# Corpus Refinement Execution

- status: completed
- crash_fingerprint: asan|j2kmarkers.cpp:52|heap-buffer-overflow /home/hermes/work/fuzzing-jpeg2000/source/core/codestream/j2kmarkers.cpp:52:17 in j2k_marker_io_base::get_byte()
- latest_artifact_path: /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_202702_1d5b676/crashes/crash-5e1dbfc1e1257014678913af52217fa8eb380818
- triage_bucket_path: /home/hermes/work/fuzzing-jpeg2000/fuzz/corpus/triage/crash-5e1dbfc1e1257014678913af52217fa8eb380818
- regression_bucket_path: /home/hermes/work/fuzzing-jpeg2000/fuzz/corpus/regression/crash-5e1dbfc1e1257014678913af52217fa8eb380818
- known_bad_bucket_path: /home/hermes/work/fuzzing-jpeg2000/fuzz/corpus/known-bad/crash-5e1dbfc1e1257014678913af52217fa8eb380818
- retention_replay_status: completed
- retention_replay_exit_code: -6
- retention_replay_signature: {'kind': 'asan', 'location': 'j2kmarkers.cpp:52', 'summary': 'heap-buffer-overflow /home/hermes/work/fuzzing-jpeg2000/source/core/codestream/j2kmarkers.cpp:52:17 in j2k_marker_io_base::get_byte()', 'artifact_path': None, 'artifact_sha1': None, 'fingerprint': 'asan|j2kmarkers.cpp:52|heap-buffer-overflow /home/hermes/work/fuzzing-jpeg2000/source/core/codestream/j2kmarkers.cpp:52:17 in j2k_marker_io_base::get_byte()'}
- retention_replay_log_path: /home/hermes/work/fuzzing-jpeg2000/fuzz-records/corpus-refinement-executions/home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_202702_1d5b676-retention-replay.log

## Retention Replay Signals

- signals: ['==557277==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x5110000000f1 at pc 0x5f6995885e7b bp 0x7fffafc33520 sp 0x7fffafc33518', 'SUMMARY: AddressSanitizer: heap-buffer-overflow /home/hermes/work/fuzzing-jpeg2000/source/core/codestream/j2kmarkers.cpp:52:17 in j2k_marker_io_base::get_byte()']
