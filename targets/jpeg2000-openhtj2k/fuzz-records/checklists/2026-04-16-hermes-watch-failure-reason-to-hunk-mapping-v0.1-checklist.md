# 2026-04-16 — failure-reason-to-hunk mapping v0.1 checklist

- [x] 현재 hunk-intent-aware validation / apply lineage 점검
- [x] failing test 먼저 추가
  - [x] smoke memory-safety signal + guard-only hunk면 `failure_reason_hunk_alignment_verified=true`
  - [x] smoke memory-safety signal + comment-only hunk면 `failure_reason_hunk_alignment_verified=false`
  - [x] build-blocker + guard-only hunk면 `failure_reason_hunk_alignment_verified=false`
- [x] RED 확인
  - [x] `failure_reason_hunk_alignment_verified` 필드 없음
  - [x] `failure_reason_hunk_alignment_reasons` 필드 없음
- [x] changed hunk intent 분류 helper 추가
- [x] failure reason -> expected hunk intent mapping helper 추가
- [x] apply/result lineage 확장
  - [x] `failure_reason_hunk_alignment_verified`
  - [x] `failure_reason_hunk_alignment_summary`
  - [x] `failure_reason_hunk_alignment_reasons`
  - [x] `failure_reason_hunk_intent`
- [x] GREEN 확인
  - [x] targeted apply tests 3개 통과
- [x] syntax 검증
  - [x] `python -m py_compile scripts/hermes_watch.py tests/test_hermes_watch.py` → OK
- [x] targeted class regression 검증
  - [x] `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests -q` → 79 passed
- [x] file-level regression 검증
  - [x] `python -m pytest tests/test_hermes_watch.py -q` → 251 passed
- [x] full regression 검증
  - [x] `python -m pytest tests -q` → 270 passed
- [x] status / progress / note / checklist 갱신

## 냉정한 판정
- [x] 이제 validation은 summary/hunk preview 정합성을 넘어 failure reason과 hunk intent를 직접 연결하기 시작했다
- [x] 하지만 여전히 preview-based heuristic이며 multi-reason prioritization은 아직 약하다
- [x] 다음은 reason 압축 품질이나 multi-reason 우선순위 쪽이 자연스럽다
