# 2026-04-16 — evidence-faithful patch validation v0.1 checklist

- [x] 현재 Evidence Response / Patch Summary 흐름 점검
- [x] failing test 먼저 추가
  - [x] Evidence Response는 맞지만 Patch Summary가 objective와 충돌하면 unverified여야 함
  - [x] Evidence Response와 Patch Summary가 맞물리면 patch alignment verified여야 함
  - [x] apply result lineage도 patch alignment 필드를 유지해야 함
- [x] RED 확인
  - [x] `delegate_artifact_patch_alignment_verified` 필드 없음
  - [x] objective와 충돌하는 Patch Summary도 verified로 통과함
- [x] Patch Summary / Evidence Response parser 보강
  - [x] `delegate_reported_response_summary` 추출
  - [x] `delegate_reported_patch_summary` 추출
- [x] heuristic patch alignment 검사 추가
  - [x] token overlap check
  - [x] objective conflict rule
- [x] verification/apply/result lineage 확장
  - [x] `delegate_artifact_patch_alignment_verified`
  - [x] `delegate_reported_patch_summary`
  - [x] `delegate_reported_response_summary`
- [x] GREEN 확인
  - [x] targeted tests 3개 통과
- [x] syntax 검증
  - [x] `python -m py_compile scripts/hermes_watch.py tests/test_hermes_watch.py` → OK
- [x] file-level regression 검증
  - [x] `python -m pytest tests/test_hermes_watch.py -q` → 247 passed
- [x] full regression 검증
  - [x] `python -m pytest tests -q` → 266 passed
- [x] status / progress / note / checklist 갱신

## 냉정한 판정
- [x] 이제 delegate output은 evidence에 답하는지뿐 아니라 patch intent가 그 답과 맞는지도 최소한 보기 시작했다
- [x] 하지만 아직 diff-level semantic judge는 아니다
- [x] 다음은 Patch Summary / Evidence Response와 실제 changed diff 정합성 쪽이 맞다
