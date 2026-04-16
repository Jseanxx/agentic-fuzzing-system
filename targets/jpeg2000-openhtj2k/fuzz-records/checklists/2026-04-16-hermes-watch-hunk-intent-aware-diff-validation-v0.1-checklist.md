# 2026-04-16 — hunk-intent-aware diff validation v0.1 checklist

- [x] 현재 diff-aware validation / apply 흐름 점검
- [x] failing test 먼저 추가
  - [x] comment-only apply 결과는 added hunk preview와 comment summary가 맞아야 함
  - [x] guard-only apply 결과는 added hunk preview와 guard summary가 맞아야 함
  - [x] preview와 summary가 충돌하면 `delegate_hunk_intent_alignment_verified=false`여야 함
- [x] RED 확인
  - [x] `delegate_hunk_intent_alignment_verified` 필드 없음
  - [x] `changed_hunk_added_lines_preview` 필드 없음
- [x] added hunk preview 추출 helper 추가
- [x] hunk line preview vs summary 정합성 helper 추가
- [x] apply/result lineage 확장
  - [x] `changed_hunk_added_lines_preview`
  - [x] `delegate_hunk_intent_alignment_verified`
- [x] GREEN 확인
  - [x] targeted apply tests 3개 통과
- [x] syntax 검증
  - [x] `python -m py_compile scripts/hermes_watch.py tests/test_hermes_watch.py` → OK
- [x] file-level regression 검증
  - [x] `python -m pytest tests/test_hermes_watch.py -q` → 248 passed
- [x] full regression 검증
  - [x] `python -m pytest tests -q` → 267 passed
- [x] status / progress / note / checklist 갱신

## 냉정한 판정
- [x] 이제 validation은 actual mutation shape를 넘어 added hunk preview까지 보기 시작했다
- [x] 하지만 아직 full hunk semantics를 읽는 수준은 아니다
- [x] 다음은 failure reason과 changed hunk를 더 직접 연결하는 쪽이 맞다
