# Corpus Split Note — 2026-04-14

## workflow-clean
- 목적: coverage/progress 관찰용
- 포함 seed:
  - `ds0_ht_12_b11.j2k`
  - `p0_11.j2k`
- 제외 seed:
  - `p0_12.j2k` (known sanitizer-triggering seed)

## triage seed
- `p0_12.j2k`
- 목적: 즉시 재현, stack 확인, 수정 검증
