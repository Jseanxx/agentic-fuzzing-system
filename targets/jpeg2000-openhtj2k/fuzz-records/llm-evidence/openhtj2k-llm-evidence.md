# LLM Evidence Packet

- generated_from_project: openhtj2k
- generated_at: 2026-04-16T22:18:33
- llm_objective: deeper-stage-reach
- top_failure_reason_codes: ['fuzz-log-memory-safety-signal', 'repeated-crash-family']
- top_failure_reason_explanations: [{'code': 'fuzz-log-memory-safety-signal', 'explanation': 'The latest fuzz log already contains sanitizer-style memory-safety signals; use that body-level clue to guide the next corrective step. Evidence focus: fuzz_log_signal_summary=AddressSanitizer from fuzz_log.'}, {'code': 'repeated-crash-family', 'explanation': 'The latest crash family is repeating; reduce shallow rediscovery and push toward distinct/deeper signal.'}]
- top_failure_reason_chains: [{'code': 'fuzz-log-memory-safety-signal', 'causal_chain': 'fuzz_log => fuzz_log_signal_summary=AddressSanitizer => fuzz-log-memory-safety-signal'}, {'code': 'repeated-crash-family', 'causal_chain': 'current_status => repeated-crash-family'}]
- top_failure_reason_narrative_steps: [{'role': 'primary', 'code': 'fuzz-log-memory-safety-signal', 'narrative': 'primary fuzz-log-memory-safety-signal sets the first corrective frame because The latest fuzz log already contains sanitizer-style memory-safety signals; use that body-level clue to guide the next corrective step. Evidence focus: fuzz_log_signal_summary=AddressSanitizer from fuzz_log.', 'explanation': 'The latest fuzz log already contains sanitizer-style memory-safety signals; use that body-level clue to guide the next corrective step. Evidence focus: fuzz_log_signal_summary=AddressSanitizer from fuzz_log.', 'causal_chain': 'fuzz_log => fuzz_log_signal_summary=AddressSanitizer => fuzz-log-memory-safety-signal'}, {'role': 'supporting', 'code': 'repeated-crash-family', 'narrative': 'supporting repeated-crash-family sharpens or corroborates that frame via current_status => repeated-crash-family', 'explanation': 'The latest crash family is repeating; reduce shallow rediscovery and push toward distinct/deeper signal.', 'causal_chain': 'current_status => repeated-crash-family'}]
- top_failure_reason_narrative: primary fuzz-log-memory-safety-signal sets the first corrective frame because The latest fuzz log already contains sanitizer-style memory-safety signals; use that body-level clue to guide the next corrective step. Evidence focus: fuzz_log_signal_summary=AddressSanitizer from fuzz_log.; supporting repeated-crash-family sharpens or corroborates that frame via current_status => repeated-crash-family
- finding_efficiency_summary: {'status': 'weak', 'summary': 'repeated crash family with low novelty', 'coverage_delta': 8.0, 'corpus_growth': -1, 'unique_crash_fingerprints': 2, 'recent_window_size': 4, 'weak_signals': ['repeated crash family with low novelty'], 'recommendation': 'bias-llm-toward-novelty-and-stage-reach'}
- finding_efficiency_recommendation: bias-llm-toward-novelty-and-stage-reach
- suggested_action_code: minimize_and_reseed
- suggested_candidate_route: reseed-before-retry
- objective_routing_linkage_summary: stable duplicate replay across distinct artifacts confirms the same crash family; prefer bounded minimization and reseed planning before another blind rerun
- current_status_path: /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/current_status.json
- probe_feedback_manifest_path: None
- run_history_path: /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/automation/run_history.json
- probe_manifest_path: None
- apply_candidate_manifest_path: None
- apply_result_manifest_path: None

## Current Status

- outcome: crash
- artifact_reason: sanitizer-crash
- crash_detected: True
- crash_fingerprint: asan|j2kmarkers.cpp:52|heap-buffer-overflow /home/hermes/work/fuzzing-jpeg2000/source/core/codestream/j2kmarkers.cpp:52:17 in j2k_marker_io_base::get_byte()
- crash_stage: ht-block-decode
- target_profile_primary_mode: deep-decode-v3

## Failure Reasons

- fuzz-log-memory-safety-signal: The latest fuzz log already contains sanitizer-style memory-safety signals; use that body-level clue to guide the next corrective step.
- repeated-crash-family: The latest crash family is repeating; reduce shallow rediscovery and push toward distinct/deeper signal.

## Latest Probe Feedback

- action_code: None
- bridge_reason: None
- candidate_id: None
- smoke_probe_status: None

## Latest Apply Result

- apply_status: None
- candidate_semantics_status: None
- candidate_semantics_reasons: None
- diff_safety_status: None

## Recent Run History

- run_history_entries: 11
- last_run_outcome: crash
- last_run_cov: 53
- last_run_corpus_units: 7

## Raw Log Signals

- smoke_log_path: None
- smoke_log_signal_count: 0
- smoke_log_signals: []
- smoke_log_signal_summary: None
- build_log_signal_count: 0
- build_log_signals: []
- build_log_signal_summary: None
- fuzz_log_signal_count: 1
- fuzz_log_signals: ['==560602==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x511000008970 at pc 0x62c2c9cbc22b bp 0x7ffe4f1b89a0 sp 0x7ffe4f1b8998']
- fuzz_log_signal_summary: AddressSanitizer
- probe_signal_count: 0
- probe_signals: []
- probe_signal_summary: None
- apply_signal_count: 0
- apply_signals: []
- apply_signal_summary: None
- body_signal_priority: ['fuzz_log']

## Duplicate Crash Review

- action_code: review_duplicate_crash_replay
- status: completed
- occurrence_count: 6
- first_seen_run: /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_200858_1d5b676
- last_seen_run: /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/modes/coverage/20260416_221832_coverage
- executor_plan_path: /home/hermes/work/fuzzing-jpeg2000/fuzz-records/refiner-plans/review_duplicate_crash_replay-home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_202702_1d5b676.md
- replay_execution_status: completed
- replay_execution_markdown_path: /home/hermes/work/fuzzing-jpeg2000/fuzz-records/duplicate-crash-replays/home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_202702_1d5b676.md
- first_replay_exit_code: -6
- latest_replay_exit_code: -6
- artifact_paths: ['/home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_200858_1d5b676/crashes/crash-964206b1bbf197c651b1198941e6e35a8830b2bf', '/home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_201732_1d5b676/crashes/crash-b3c5e4eb4b2827051ee3179055e7151026e05c37', '/home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_202702_1d5b676/crashes/crash-5e1dbfc1e1257014678913af52217fa8eb380818', '/home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_205116_1d5b676/crashes/crash-33785f9915a4429ab43505601b52818c3ad1ebd4', '/home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/modes/coverage/20260416_221705_coverage/crashes/crash-0e00eab812ff07a48a1cbc1915b02d07ad402eb1', '/home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/modes/coverage/20260416_221832_coverage/crashes/crash-07e93f6953e036f83b1649bc50857d0d0562a2ab']

## Finding Efficiency

- status: weak
- summary: repeated crash family with low novelty
- coverage_delta: 8.0
- corpus_growth: -1
- unique_crash_fingerprints: 2
- weak_signals: ['repeated crash family with low novelty']
- finding_efficiency_recommendation: bias-llm-toward-novelty-and-stage-reach

## Suggested LLM Use

- Read the failure reasons first, not raw logs first.
- Propose the smallest change that improves build, smoke, or deeper-stage reach.
- Stay within bounded mutation scope unless the evidence explicitly justifies widening it.
