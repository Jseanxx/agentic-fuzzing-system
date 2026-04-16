# 2026-04-16 — failure reason extraction v0.6 checklist

- [x] 현재 signal summary / top reason ordering / failure reason payload 흐름 점검
- [x] failing test 먼저 추가
  - [x] build-log memory-safety reason에 body-to-reason explanation이 있어야 함
  - [x] smoke-log memory-safety reason에 body-to-reason explanation이 있어야 함
  - [x] `top_failure_reason_explanations`가 노출되어야 함
- [x] RED 확인
  - [x] reason entry에 `explanation` 없음
  - [x] `top_failure_reason_explanations` 필드 없음
- [x] per-reason explanation helper 추가
- [x] packet 필드 확장
  - [x] `top_failure_reason_explanations`
- [x] markdown 상단 explanation 노출
- [x] GREEN 확인
  - [x] `python -m pytest tests/test_hermes_watch.py::HermesWatchLLMEvidencePacketV06Tests -q` → 2 passed
- [x] syntax 검증
  - [x] `python -m py_compile scripts/hermes_watch_support/llm_evidence.py tests/test_hermes_watch.py` → OK
- [x] targeted regression 검증
  - [x] `python -m pytest tests/test_hermes_watch.py::HermesWatchLLMEvidencePacketV03Tests tests/test_hermes_watch.py::HermesWatchLLMEvidencePacketV04Tests tests/test_hermes_watch.py::HermesWatchLLMEvidencePacketV05Tests tests/test_hermes_watch.py::HermesWatchLLMEvidencePacketV06Tests -q` → 8 passed
- [x] file-level regression 검증
  - [x] `python -m pytest tests/test_hermes_watch.py -q` → 257 passed
- [x] full regression 검증
  - [x] `python -m pytest tests -q` → 276 passed
- [x] status / progress / note / checklist 갱신

## 냉정한 판정
- [x] 이번 단계는 reason explanation readability 강화이지 diagnosis engine 강화는 아니다
- [x] body-to-reason linkage는 좋아졌지만 causal chain 설명은 아직 약하다
- [x] 다음은 deferred secondary conflict surfacing이나 richer causal compression이 자연스럽다
