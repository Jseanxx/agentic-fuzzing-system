# 2026-04-16 — delegate verification / apply policy evidence-aware lineage v0.1 checklist

- [x] verification/apply lineage 주입 지점 조사
- [x] failing test 먼저 확장
  - [x] verification result가 evidence 핵심 필드를 유지해야 함
  - [x] apply result/result manifest가 evidence 핵심 필드를 유지해야 함
- [x] RED 확인
  - [x] `result["llm_objective"]` 없음
  - [x] `result["failure_reason_codes"]` 없음
- [x] `verify_harness_apply_candidate_result(...)`에 evidence lineage 유지 추가
- [x] `apply_verified_harness_patch_candidate(...)` blocked/applied path에 evidence lineage 유지 추가
- [x] GREEN 확인
  - [x] targeted tests → 2 passed
- [x] syntax 검증
  - [x] `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/llm_evidence.py tests/test_hermes_watch.py` → OK
- [x] regression 검증
  - [x] `python -m pytest tests/test_hermes_watch.py -q` → 242 passed
  - [x] `python -m pytest tests -q` → 261 passed
- [x] status / progress / note / checklist 갱신

## 냉정한 판정
- [x] 이제 input evidence가 verification/apply lineage로 이어지기 시작했다
- [x] 하지만 output schema 자체를 evidence-aware하게 강제한 단계는 아직 아니다
