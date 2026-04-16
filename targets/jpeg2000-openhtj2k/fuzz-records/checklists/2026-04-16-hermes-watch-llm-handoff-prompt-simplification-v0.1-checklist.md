# 2026-04-16 — LLM handoff prompt simplification v0.1 checklist

- [x] 현재 delegate handoff / bridge prompt 경로 조사
- [x] failing test 먼저 추가/확장
  - [x] promoted apply candidate delegate request가 evidence packet 필드를 포함해야 함
  - [x] bridge prompt가 evidence packet 우선 읽기를 명시해야 함
- [x] RED 확인
  - [x] delegate request context에 `llm_evidence_json_path` 없음
  - [x] bridge prompt에 `failure_reasons` / evidence 우선 읽기 지시 없음
- [x] `harness_skeleton.py`에서 latest evidence packet 주입
- [x] delegate request goal/context simplification
- [x] `build_delegate_bridge_prompt(...)`에 evidence-first instruction 추가
- [x] GREEN 확인
  - [x] targeted tests → 2 passed
- [x] syntax 검증
  - [x] `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/harness_skeleton.py scripts/hermes_watch_support/llm_evidence.py tests/test_hermes_watch.py` → OK
- [x] regression 검증
  - [x] `python -m pytest tests/test_hermes_watch.py -q` → 240 passed
  - [x] `python -m pytest tests -q` → 259 passed
- [x] status / progress / note / checklist 갱신

## 냉정한 판정
- [x] evidence packet과 delegate handoff가 실제로 이어지기 시작했다
- [x] 하지만 아직 verification/apply lineage까지 evidence-aware한 건 아니다
- [x] 다음은 failure reason extraction v0.3 또는 evidence-aware result lineage가 자연스럽다
