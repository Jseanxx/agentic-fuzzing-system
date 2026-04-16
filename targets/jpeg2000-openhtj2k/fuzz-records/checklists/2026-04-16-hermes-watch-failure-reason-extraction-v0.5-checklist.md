# 2026-04-16 — failure reason extraction v0.5 checklist

- [x] 현재 llm_evidence collector / raw_signal_summary / reason ordering 흐름 점검
- [x] failing test 먼저 추가
  - [x] repeated raw body signal line이 dedup되어 count와 summary가 줄어들어야 함
  - [x] plane별 signal summary가 생겨야 함
  - [x] failure reason code가 더 operator-friendly한 우선순위로 정렬되어야 함
  - [x] `top_failure_reason_codes`가 노출되어야 함
- [x] RED 확인
  - [x] dedup 전 `smoke_log_signal_count`가 과도하게 큼
  - [x] `top_failure_reason_codes` 필드 없음
- [x] raw signal dedup helper 강화
- [x] body-to-summary reduction 필드 추가
  - [x] `smoke_log_signal_summary`
  - [x] `build_log_signal_summary`
  - [x] `fuzz_log_signal_summary`
  - [x] `probe_signal_summary`
  - [x] `apply_signal_summary`
  - [x] `body_signal_priority`
- [x] failure reason prioritization helper 추가
- [x] packet 필드 확장
  - [x] `top_failure_reason_codes`
- [x] GREEN 확인
  - [x] `python -m pytest tests/test_hermes_watch.py::HermesWatchLLMEvidencePacketV05Tests -q` → 2 passed
- [x] syntax 검증
  - [x] `python -m py_compile scripts/hermes_watch_support/llm_evidence.py tests/test_hermes_watch.py` → OK
- [x] targeted regression 검증
  - [x] `python -m pytest tests/test_hermes_watch.py::HermesWatchLLMEvidencePacketV03Tests tests/test_hermes_watch.py::HermesWatchLLMEvidencePacketV04Tests tests/test_hermes_watch.py::HermesWatchLLMEvidencePacketV05Tests -q` → 6 passed
- [x] file-level regression 검증
  - [x] `python -m pytest tests/test_hermes_watch.py -q` → 253 passed
- [x] full regression 검증
  - [x] `python -m pytest tests -q` → 272 passed
- [x] status / progress / note / checklist 갱신

## 냉정한 판정
- [x] 이번 단계는 signal pickup 확대가 아니라 evidence packet 정리 품질 개선에 가깝다
- [x] dedup / prioritization / summary reduction은 좋아졌지만 아직 root-cause diagnosis는 아니다
- [x] 다음은 multi-reason 우선순위나 reason explanation 품질 쪽이 자연스럽다
