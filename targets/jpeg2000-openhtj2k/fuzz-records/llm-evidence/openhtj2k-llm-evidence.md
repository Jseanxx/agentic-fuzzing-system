# LLM Evidence Packet

- generated_from_project: openhtj2k
- generated_at: 2026-04-16T22:35:29
- llm_objective: stage-reach-or-new-signal
- top_failure_reason_codes: ['fuzz-log-memory-safety-signal']
- top_failure_reason_explanations: [{'code': 'fuzz-log-memory-safety-signal', 'explanation': 'The latest fuzz log already contains sanitizer-style memory-safety signals; use that body-level clue to guide the next corrective step. Evidence focus: fuzz_log_signal_summary=AddressSanitizer from fuzz_log.'}]
- top_failure_reason_chains: [{'code': 'fuzz-log-memory-safety-signal', 'causal_chain': 'fuzz_log => fuzz_log_signal_summary=AddressSanitizer => fuzz-log-memory-safety-signal'}]
- top_failure_reason_narrative_steps: [{'role': 'primary', 'code': 'fuzz-log-memory-safety-signal', 'narrative': 'primary fuzz-log-memory-safety-signal sets the first corrective frame because The latest fuzz log already contains sanitizer-style memory-safety signals; use that body-level clue to guide the next corrective step. Evidence focus: fuzz_log_signal_summary=AddressSanitizer from fuzz_log.', 'explanation': 'The latest fuzz log already contains sanitizer-style memory-safety signals; use that body-level clue to guide the next corrective step. Evidence focus: fuzz_log_signal_summary=AddressSanitizer from fuzz_log.', 'causal_chain': 'fuzz_log => fuzz_log_signal_summary=AddressSanitizer => fuzz-log-memory-safety-signal'}]
- top_failure_reason_narrative: primary fuzz-log-memory-safety-signal sets the first corrective frame because The latest fuzz log already contains sanitizer-style memory-safety signals; use that body-level clue to guide the next corrective step. Evidence focus: fuzz_log_signal_summary=AddressSanitizer from fuzz_log.
- finding_efficiency_summary: {'status': 'healthy', 'summary': 'recent run history does not yet show an obvious finding-efficiency bottleneck', 'coverage_delta': 8.0, 'corpus_growth': -1, 'unique_crash_fingerprints': 3, 'recent_window_size': 4, 'weak_signals': [], 'recommendation': 'maintain-current-loop-and-collect-more-signal'}
- finding_efficiency_recommendation: maintain-current-loop-and-collect-more-signal
- suggested_action_code: halt_and_review_harness
- suggested_candidate_route: review-current-candidate
- objective_routing_linkage_summary: llm objective stage-reach-or-new-signal links to halt_and_review_harness / review-current-candidate; finding recommendation=maintain-current-loop-and-collect-more-signal; top failure narrative=primary fuzz-log-memory-safety-signal sets the first corrective frame because The latest fuzz log already contains sanitizer-style memory-safety signals; use that body-level clue to guide the next corrective step. Evidence focus: fuzz_log_signal_summary=AddressSanitizer from fuzz_log.; override=deep-stage-crash-already-reached
- current_status_path: /home/hermes/work/fuzzing-jpeg2000/targets/jpeg2000-openhtj2k/fuzz-artifacts/current_status.json
- probe_feedback_manifest_path: None
- run_history_path: /home/hermes/work/fuzzing-jpeg2000/targets/jpeg2000-openhtj2k/fuzz-artifacts/automation/run_history.json
- probe_manifest_path: None
- apply_candidate_manifest_path: None
- apply_result_manifest_path: None

## Current Status

- outcome: crash
- artifact_reason: sanitizer-crash
- crash_detected: True
- crash_fingerprint: asan|coding_units.cpp:3076|SEGV /home/hermes/work/fuzzing-jpeg2000/targets/jpeg2000-openhtj2k/source/core/coding/coding_units.cpp:3076:16 in j2k_tile::add_tile_part(SOT_marker&, j2c_src_memory&, j2k_main_header&)
- crash_stage: tile-part-load
- target_profile_primary_mode: deep-decode-v3

## Failure Reasons

- fuzz-log-memory-safety-signal: The latest fuzz log already contains sanitizer-style memory-safety signals; use that body-level clue to guide the next corrective step.

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

- run_history_entries: 12
- last_run_outcome: crash
- last_run_cov: None
- last_run_corpus_units: None

## Raw Log Signals

- smoke_log_path: None
- smoke_log_signal_count: 0
- smoke_log_signals: []
- smoke_log_signal_summary: None
- build_log_signal_count: 0
- build_log_signals: []
- build_log_signal_summary: None
- fuzz_log_signal_count: 1
- fuzz_log_signals: ['AddressSanitizer:DEADLYSIGNAL']
- fuzz_log_signal_summary: AddressSanitizer
- probe_signal_count: 0
- probe_signals: []
- probe_signal_summary: None
- apply_signal_count: 0
- apply_signals: []
- apply_signal_summary: None
- body_signal_priority: ['fuzz_log']

## Duplicate Crash Review

- action_code: None
- status: None
- occurrence_count: None
- first_seen_run: None
- last_seen_run: None
- executor_plan_path: None
- replay_execution_status: None
- replay_execution_markdown_path: None
- first_replay_exit_code: None
- latest_replay_exit_code: None
- artifact_paths: None

## Finding Efficiency

- status: healthy
- summary: recent run history does not yet show an obvious finding-efficiency bottleneck
- coverage_delta: 8.0
- corpus_growth: -1
- unique_crash_fingerprints: 3
- weak_signals: []
- finding_efficiency_recommendation: maintain-current-loop-and-collect-more-signal

## Suggested LLM Use

- Read the failure reasons first, not raw logs first.
- Propose the smallest change that improves build, smoke, or deeper-stage reach.
- Stay within bounded mutation scope unless the evidence explicitly justifies widening it.
