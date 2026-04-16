# 2026-04-16 — failure reason extraction v0.9 checklist

- [x] 현재 narrative / finding efficiency recommendation / llm objective 흐름 점검
- [x] failing test 먼저 추가
  - [x] deeper-stage objective가 suggested action/route로 연결되어야 함
  - [x] build-fix objective가 review route로 markdown에 보여야 함
- [x] RED 확인
  - [x] `suggested_action_code` 없음
  - [x] `suggested_candidate_route` 없음
  - [x] `objective_routing_linkage_summary` 없음
- [x] objective → routing linkage helper 추가
- [x] packet 필드 확장
  - [x] `suggested_action_code`
  - [x] `suggested_candidate_route`
  - [x] `objective_routing_linkage_summary`
- [x] markdown 상단 linkage 노출
- [x] GREEN 확인
  - [x] `python -m pytest tests/test_hermes_watch.py::HermesWatchLLMEvidencePacketV09Tests -q` → 2 passed
- [x] syntax 검증
  - [x] `python -m py_compile scripts/hermes_watch_support/llm_evidence.py tests/test_hermes_watch.py` → OK
- [x] targeted regression 검증
  - [x] `python -m pytest tests/test_hermes_watch.py::HermesWatchLLMEvidencePacketV03Tests tests/test_hermes_watch.py::HermesWatchLLMEvidencePacketV04Tests tests/test_hermes_watch.py::HermesWatchLLMEvidencePacketV05Tests tests/test_hermes_watch.py::HermesWatchLLMEvidencePacketV06Tests tests/test_hermes_watch.py::HermesWatchLLMEvidencePacketV07Tests tests/test_hermes_watch.py::HermesWatchLLMEvidencePacketV08Tests tests/test_hermes_watch.py::HermesWatchLLMEvidencePacketFindingEfficiencyTests tests/test_hermes_watch.py::HermesWatchLLMEvidencePacketV09Tests -q` → 16 passed
- [x] file-level regression 검증
  - [x] `python -m pytest tests/test_hermes_watch.py -q` → 270 passed
- [x] full regression 검증
  - [x] `python -m pytest tests -q` → 289 passed
- [x] status / progress / note / checklist 갱신

## 냉정한 판정
- [x] 이번 단계는 smarter planner가 아니라 why→next-action readability 강화다
- [x] packet이 이제 얇은 next-action guide 역할까지 하기 시작했다
- [x] 다음은 usable v1 cutline review가 자연스럽다
