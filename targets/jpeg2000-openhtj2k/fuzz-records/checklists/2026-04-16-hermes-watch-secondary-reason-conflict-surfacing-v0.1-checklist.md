# 2026-04-16 — secondary-reason conflict surfacing v0.1 checklist

- [x] 현재 primary reason / top reason / hunk alignment lineage 흐름 점검
- [x] failing test 먼저 추가
  - [x] primary reason이 맞아도 deferred secondary reason과 충돌하면 conflict를 artifact에 남겨야 함
  - [x] mapped secondary reasons가 모두 같은 hunk intent를 기대하면 secondary conflict는 없어야 함
- [x] RED 확인
  - [x] `failure_reason_hunk_secondary_conflict_status` 필드 없음
  - [x] deferred secondary reason tension이 artifact에 남지 않음
- [x] deferred secondary conflict surfacing helper 확장
- [x] apply/result lineage 확장
  - [x] `failure_reason_hunk_secondary_conflict_status`
  - [x] `failure_reason_hunk_secondary_conflict_count`
  - [x] `failure_reason_hunk_secondary_conflict_reasons`
  - [x] `failure_reason_hunk_deferred_reason_codes`
- [x] GREEN 확인
  - [x] targeted secondary-conflict apply tests 2개 통과
- [x] syntax 검증
  - [x] `python -m py_compile scripts/hermes_watch.py tests/test_hermes_watch.py` → OK
- [x] targeted class regression 검증
  - [x] `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests -q` → 83 passed
- [x] file-level regression 검증
  - [x] `python -m pytest tests/test_hermes_watch.py -q` → 259 passed
- [x] full regression 검증
  - [x] `python -m pytest tests -q` → 278 passed
- [x] status / progress / note / checklist 갱신

## 냉정한 판정
- [x] 이번 단계는 secondary tension visibility 강화이지 multi-reason resolution은 아니다
- [x] deferred conflict는 보이기 시작했지만 아직 routing/action 쪽 자동 반영은 없다
- [x] 다음은 causal compression이나 secondary-conflict-aware routing 쪽이 자연스럽다
