# 2026-04-16 — multi-reason hunk prioritization v0.1 checklist

- [x] 현재 failure_reason ordering / hunk alignment 흐름 점검
- [x] failing test 먼저 추가
  - [x] `top_failure_reason_codes`가 multi-reason conflict에서 primary basis로 우선 사용되어야 함
  - [x] top priority reason이 hunk와 맞으면 lower-priority conflict reason이 있어도 aligned 처리되어야 함
  - [x] top priority reason이 hunk와 충돌하면 priority mismatch가 기록되어야 함
- [x] RED 확인
  - [x] top priority reason이 있어도 기존 flat reason flow를 타서 conflict가 그대로 남음
  - [x] `failure_reason_hunk_priority_basis` 필드 없음
- [x] priority-aware hunk alignment helper 확장
- [x] apply/result lineage 확장
  - [x] `failure_reason_hunk_primary_reason_code`
  - [x] `failure_reason_hunk_priority_basis`
- [x] GREEN 확인
  - [x] targeted multi-reason apply tests 2개 통과
- [x] syntax 검증
  - [x] `python -m py_compile scripts/hermes_watch.py tests/test_hermes_watch.py` → OK
- [x] targeted class regression 검증
  - [x] `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests -q` → 81 passed
- [x] file-level regression 검증
  - [x] `python -m pytest tests/test_hermes_watch.py -q` → 255 passed
- [x] full regression 검증
  - [x] `python -m pytest tests -q` → 274 passed
- [x] status / progress / note / checklist 갱신

## 냉정한 판정
- [x] 이번 단계는 multi-reason conflict를 완전히 푼 게 아니라 packet priority와 apply priority를 일치시키는 단계다
- [x] deferred secondary reason tension은 아직 약하다
- [x] 다음은 reason explanation 품질이나 secondary conflict surfacing이 자연스럽다
