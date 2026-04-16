# Hermes Watch Evidence Review Follow-up Queue v0.1 Checklist

- [x] deep crash review route gap 확인 (packet은 review, rail은 미연결)
- [x] failing regression test added for evidence-driven review queue entry creation
- [x] failing regression test added for CLI queue path success
- [x] `queue_latest_evidence_review_followup(repo_root)` 추가
- [x] latest LLM evidence packet -> `harness_review_queue.json` 연결
- [x] evidence lineage (`llm_evidence_json_path`, route, crash fingerprint, stage) queue entry에 보존
- [x] `--queue-latest-evidence-review-followup` CLI 추가
- [x] real repo queue entry 생성 확인
- [x] `--prepare-refiner-orchestration`로 review follow-up orchestration artifact 생성 확인
- [x] `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/llm_evidence.py tests/test_hermes_watch.py`
- [x] `python -m pytest tests/test_hermes_watch.py::HermesWatchLLMEvidencePacketV09Tests tests/test_hermes_watch.py::HermesWatchAutonomousSupervisorTests -q`
- [x] `python -m pytest tests/test_hermes_watch.py -q`
- [x] `python -m pytest tests -q`
- [ ] prepared review orchestration의 실제 subagent launch/result verification auto-chain
