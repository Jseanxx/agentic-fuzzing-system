# LLM Evidence Packet

- generated_from_project: fuzzing-jpeg2000
- generated_at: 2026-04-16T11:13:07
- llm_objective: smoke-enable-or-fix
- current_status_path: /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/current_status.json
- probe_feedback_manifest_path: None
- run_history_path: /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/automation/run_history.json
- probe_manifest_path: None
- apply_candidate_manifest_path: None
- apply_result_manifest_path: None

## Current Status

- outcome: smoke-failed
- artifact_reason: baseline-input-failed
- crash_detected: False
- crash_fingerprint: None
- crash_stage: None
- target_profile_primary_mode: None

## Failure Reasons

- smoke-invalid-or-harness-mismatch: Latest run failed during smoke; fix seed validity or harness assumptions before deeper fuzzing.
- no-crash-yet: The system has not produced a crash yet; bias the next iteration toward stage reach and observability.
- smoke-log-memory-safety-signal: The latest smoke log already contains sanitizer-style memory-safety signals; treat this as a concrete debugging clue, not just a generic smoke failure.

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

- run_history_entries: 0
- last_run_outcome: None
- last_run_cov: None
- last_run_corpus_units: None

## Raw Log Signals

- smoke_log_path: /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260414_235458_1d5b676/smoke.log
- smoke_log_signal_count: 2
- smoke_log_signals: ['/home/hermes/work/fuzzing-jpeg2000/source/core/coding/block_decoding.cpp:86:23: runtime error: addition of unsigned offset to 0x52f000000420 overflowed to 0x52f000000400', 'SUMMARY: UndefinedBehaviorSanitizer: undefined-behavior /home/hermes/work/fuzzing-jpeg2000/source/core/coding/block_decoding.cpp:86:23']
- build_log_signal_count: 0
- build_log_signals: []
- fuzz_log_signal_count: 0
- fuzz_log_signals: []
- probe_signal_count: 0
- probe_signals: []
- apply_signal_count: 0
- apply_signals: []

## Suggested LLM Use

- Read the failure reasons first, not raw logs first.
- Propose the smallest change that improves build, smoke, or deeper-stage reach.
- Stay within bounded mutation scope unless the evidence explicitly justifies widening it.
