# Checklist — full recovery ecosystem recursion v0.1

- [x] retry / hold / abort / reingest interaction map을 lane-priority 관점으로 정리
- [x] ecosystem stop reason taxonomy 추가 (`retry-lane-*`, `downstream-lane-*`, `no-eligible-lane`, `ecosystem-round-budget-exhausted`)
- [x] reverse-linked follow-up escalation이 있으면 downstream lane 우선 선택
- [x] retry lane에서 `hold` 후 다음 라운드 downstream lane으로 넘어가는 최소 cross-lane recursion 추가
- [x] ecosystem round count / last lane / lane sequence lineage 기록
- [x] failing test 3개로 RED 확인
- [x] 타깃 테스트 통과
- [x] `py_compile` 통과
- [x] `tests/test_hermes_watch.py` 전체 통과
- [x] `tests` 전체 통과
