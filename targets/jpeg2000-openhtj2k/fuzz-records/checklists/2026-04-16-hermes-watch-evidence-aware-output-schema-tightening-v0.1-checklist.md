# 2026-04-16 — evidence-aware output schema tightening v0.1 checklist

- [x] 현재 delegate verification/output 흐름 점검
- [x] failing test 먼저 추가
  - [x] Evidence Response가 없으면 verification이 unverified여야 함
  - [x] Evidence Response가 objective/reason codes와 맞으면 verified여야 함
- [x] RED 확인
  - [x] `delegate_artifact_evidence_response_verified` 필드 없음
  - [x] `delegate_reported_llm_objective` 필드 없음
  - [x] `delegate_reported_failure_reason_codes` 필드 없음
- [x] delegate evidence response parser 추가
- [x] `verify_delegate_entry(...)`에 evidence response 검증 추가
- [x] `verify_harness_apply_candidate_result(...)` return schema 확장
- [x] `apply_verified_harness_patch_candidate(...)` result lineage 확장
- [x] bridge arm 기본 expected/quality sections에 `## Evidence Response` 추가
- [x] delegate request requirements에 Evidence Response section 요구 추가
- [x] GREEN 확인
  - [x] targeted verification tests 4개 통과
- [x] syntax 검증
  - [x] `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/harness_skeleton.py tests/test_hermes_watch.py` → OK
- [x] file-level regression 검증
  - [x] `python -m pytest tests/test_hermes_watch.py -q` → 246 passed
- [x] full regression 검증
  - [x] `python -m pytest tests -q` → 265 passed
- [x] status / progress / note / checklist 갱신

## 냉정한 판정
- [x] 이제 delegate output이 evidence에 직접 답하는 최소 형식 계약이 생겼다
- [x] 하지만 아직 evidence-faithful repair를 판정하는 수준은 아니다
- [x] 다음은 형식 검증이 아니라 reported evidence와 patch intent의 실제 정합성 쪽이 맞다
