# 2026-04-16 — failure reason extraction v0.8 checklist

- [x] 현재 explanation / causal chain packet 구조 점검
- [x] failing test 먼저 추가
  - [x] build packet에 multi-reason narrative 필드가 있어야 함
  - [x] markdown 상단에 top failure reason narrative가 노출되어야 함
- [x] RED 확인
  - [x] `top_failure_reason_narrative` 없음
  - [x] `top_failure_reason_narrative_steps` 없음
- [x] top reason narrative helper 추가
- [x] packet 필드 확장
  - [x] `top_failure_reason_narrative_steps`
  - [x] `top_failure_reason_narrative`
- [x] markdown 상단 narrative 노출
- [x] GREEN 확인
  - [x] `python -m pytest tests/test_hermes_watch.py::HermesWatchLLMEvidencePacketV08Tests -q` → 2 passed
- [x] syntax 검증
  - [x] `python -m py_compile scripts/hermes_watch_support/llm_evidence.py tests/test_hermes_watch.py` → OK
- [x] targeted regression 검증
  - [x] `python -m pytest tests/test_hermes_watch.py::HermesWatchLLMEvidencePacketV03Tests tests/test_hermes_watch.py::HermesWatchLLMEvidencePacketV04Tests tests/test_hermes_watch.py::HermesWatchLLMEvidencePacketV05Tests tests/test_hermes_watch.py::HermesWatchLLMEvidencePacketV06Tests tests/test_hermes_watch.py::HermesWatchLLMEvidencePacketV07Tests tests/test_hermes_watch.py::HermesWatchLLMEvidencePacketV08Tests -q` → 12 passed
- [x] file-level regression 검증
  - [x] `python -m pytest tests/test_hermes_watch.py -q` → 265 passed
- [x] full regression 검증
  - [x] `python -m pytest tests -q` → 284 passed
- [x] status / progress / note / checklist 갱신

## 냉정한 판정
- [x] 이번 단계는 multi-reason reasoning이 아니라 multi-reason readability 강화다
- [x] top reason ordering / explanation / causal chain 위에 narrative layer를 하나 더 얹었다
- [x] 다음은 secondary-conflict severity/actionability 또는 finding-efficiency-facing intelligence가 자연스럽다
