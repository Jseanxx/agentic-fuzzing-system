# Leak Triage Note — 2026-04-14

## Observed in
- run: `20260414_220545_1d5b676`
- corpus mode: `workflow-clean`

## Signal
```text
SUMMARY: AddressSanitizer: 12312 byte(s) leaked in 1 allocation(s).
```

## Allocation stack (top)
- `AlignedLargePool::alloc(unsigned long, unsigned long)`
- `source/core/common/utils.hpp:252`
- `j2k_tile::decode()`
- `source/core/coding/coding_units.cpp:3927`

## Meaning
- known-bad crash seed를 빼도 장시간 관찰용 러닝이 바로 깨질 수 있음
- 다만 이번 라운드 덕분에 progress metric 자체는 확인했으므로,
  leak 자체를 triage 대상으로 분리하고 coverage mode를 별도 정책으로 운영할 수 있음

## Candidate next actions
- leak root cause 조사
- leak 검증 전용 재현 커맨드 정리
- coverage 관찰만 우선이면 `ASAN_OPTIONS=detect_leaks=0:...` 정책 검토
