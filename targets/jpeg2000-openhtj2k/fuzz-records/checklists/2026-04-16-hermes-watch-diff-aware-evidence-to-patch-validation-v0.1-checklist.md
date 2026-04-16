# 2026-04-16 — diff-aware evidence-to-patch validation v0.1 checklist

- [x] 현재 patch alignment / apply diff 흐름 점검
- [x] failing test 먼저 추가
  - [x] comment-only apply 결과는 `actual_mutation_shape=comment-only`여야 함
  - [x] guard-only apply 결과는 `actual_mutation_shape=guard-only`여야 함
  - [x] summary와 actual mutation shape가 충돌하면 `delegate_diff_alignment_verified=false`여야 함
- [x] RED 확인
  - [x] `delegate_diff_alignment_verified` 필드 없음
  - [x] `actual_mutation_shape` 필드 없음
- [x] actual mutation shape 분류 helper 추가
- [x] summary vs mutation shape 정합성 helper 추가
- [x] apply/result lineage 확장
  - [x] `delegate_diff_alignment_verified`
  - [x] `actual_mutation_shape`
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
- [x] 이제 validation은 실제 mutation shape를 보기 시작했다
- [x] 하지만 아직 changed hunk meaning을 읽는 수준은 아니다
- [x] 다음은 hunk-intent-aware diff validation 쪽이 맞다
