# Hermes Watch Leak Signature Capture Hardening v0.1 Checklist

- Date: 2026-04-16 19:33:43 KST
- Status: done

## Goal
최신 deep-decode-v3 leak artifact가 allocator/common frame 때문에 `unknown-location`/generic crash 쪽으로 흐려지지 않게 하고,
summary + artifact path + meaningful project frame이 watcher signature에 남도록 만들기.

## Checklist
- [x] 최신 `fuzz-artifacts/current_status.json`, `FUZZING_REPORT.md`, `fuzz.log` 상태 확인
- [x] root cause 확인: long leak stack에서 summary/artifact line 손실 + allocator frame 우선 location 선택
- [x] failing test 추가: long leak stack에서도 project frame / summary / artifact path 보존 요구
- [x] RED 확인
- [x] `Metrics.update_from_line(...)` crash context capture hardening
- [x] `extract_primary_location(...)` leak-aware frame selection hardening
- [x] targeted leak tests 통과
- [x] full `pytest -q` 통과
- [x] 실제 최신 `fuzz.log` 재파싱으로 `leak|coding_units.cpp:3927|...` 복구 확인
- [x] canonical status/progress 문서 업데이트

## Verification commands
- `pytest -q tests/test_hermes_watch.py -k 'preserve_leak_summary_artifact_and_deep_project_frame_when_allocator_frames_are_first'`
- `pytest -q tests/test_hermes_watch.py -k 'leak or LeakSanitizer or classify_artifact_event_prefers_leak_over_generic_crash or decide_policy_action_handles_leak or build_llm_evidence_packet_v9_routes_leak_signal_to_reviewable_cleanup_objective'`
- `pytest -q`
- `python scripts/hermes_watch.py --repo /home/hermes/work/fuzzing-jpeg2000 --write-llm-evidence-packet`

## Cold assessment
이번 단계는 leak-aware evidence packet 위에 있던 약한 원본 crash signature를 보강한 것이다.
아직 stale registry backfill은 안 했으므로, 다음 step은 과거/current artifact repair 또는 bounded rerun 확인 쪽이 맞다.
