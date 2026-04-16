# 2026-04-16 — failure reason extraction v0.2 checklist

- [x] v0.2에서 추가할 history-aware reason 범위 결정
- [x] failing test 먼저 추가
  - [x] `test_build_llm_evidence_packet_v2_extracts_no_progress_plateau_and_corpus_stagnation_reasons`
  - [x] `test_build_llm_evidence_packet_v2_extracts_shallow_crash_recurrence_from_history`
- [x] RED 확인
  - [x] `no-progress-stall` 미검출
  - [x] `shallow-crash-recurrence` 미검출
- [x] `llm_evidence.py`에 run history loading 추가
- [x] history-aware helpers 추가
  - [x] recent window 추출
  - [x] lightweight stage depth 분류
  - [x] semantic history summary
- [x] 새 reason codes 추가
  - [x] `no-progress-stall`
  - [x] `coverage-plateau`
  - [x] `corpus-bloat-low-gain`
  - [x] `shallow-crash-recurrence`
  - [x] `stage-reach-blocked`
- [x] `run_history_path`, `run_history`를 packet에 포함
- [x] markdown에 recent history summary 추가
- [x] GREEN 확인
  - [x] `python -m pytest tests/test_hermes_watch.py::HermesWatchLLMEvidencePacketV02Tests -q` → 2 passed
- [x] syntax 검증
  - [x] `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/llm_evidence.py tests/test_hermes_watch.py` → OK
- [x] regression 검증
  - [x] `python -m pytest tests/test_hermes_watch.py -q` → 240 passed
  - [x] `python -m pytest tests -q` → 259 passed
- [x] status / progress / note / checklist 갱신

## 냉정한 판정
- [x] 목적 적합한 작은 slice였다
- [x] 하지만 아직 raw log/body-level reasoning은 없다
- [x] 다음은 handoff simplification이 우선이다
