# 2026-04-16 — failure reason extraction v0.7 checklist

- [x] 현재 explanation/template 흐름 점검
- [x] failing test 먼저 추가
  - [x] build reason에 causal chain이 있어야 함
  - [x] smoke reason에 causal chain이 있어야 함
  - [x] `top_failure_reason_chains`가 노출되어야 함
- [x] RED 확인
  - [x] reason entry에 `causal_chain` 없음
  - [x] `top_failure_reason_chains` 필드 없음
- [x] per-reason causal chain helper 추가
- [x] packet 필드 확장
  - [x] `top_failure_reason_chains`
- [x] markdown 상단 causal chain 노출
- [x] GREEN 확인
  - [x] `python -m pytest tests/test_hermes_watch.py::HermesWatchLLMEvidencePacketV07Tests -q` → 2 passed
- [x] syntax 검증
  - [x] `python -m py_compile scripts/hermes_watch_support/llm_evidence.py tests/test_hermes_watch.py` → OK
- [x] targeted regression 검증
  - [x] `python -m pytest tests/test_hermes_watch.py::HermesWatchLLMEvidencePacketV03Tests tests/test_hermes_watch.py::HermesWatchLLMEvidencePacketV04Tests tests/test_hermes_watch.py::HermesWatchLLMEvidencePacketV05Tests tests/test_hermes_watch.py::HermesWatchLLMEvidencePacketV06Tests tests/test_hermes_watch.py::HermesWatchLLMEvidencePacketV07Tests -q` → 10 passed
- [x] file-level regression 검증
  - [x] `python -m pytest tests/test_hermes_watch.py -q` → 261 passed
- [x] full regression 검증
  - [x] `python -m pytest tests -q` → 280 passed
- [x] status / progress / note / checklist 갱신

## 냉정한 판정
- [x] 이번 단계는 causal diagnosis가 아니라 causal readability 강화다
- [x] explanation보다 한 단계 좋아졌지만 아직 multi-reason narrative는 아니다
- [x] 다음은 secondary-conflict-aware routing이나 richer multi-reason narrative가 자연스럽다
