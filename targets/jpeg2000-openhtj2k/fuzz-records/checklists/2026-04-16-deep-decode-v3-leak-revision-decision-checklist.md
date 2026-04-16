# Deep Decode V3 Leak Revision Decision Checklist

- Updated: 2026-04-16 18:39:00 KST
- Project: `fuzzing-jpeg2000`

---

## 목표
- [x] 새 leak signal이 진전 신호인지 확인
- [x] current suggested action이 stale한지 판단
- [x] next revision을 triage-first / harness-adjustment / seed-strategy / deeper-promotion 중에서 결정

## 판정
- [x] deep-decode-v3 방향 자체는 유지
- [x] immediate next는 `triage-first`
- [x] `shift_weight_to_deeper_harness`는 immediate next로는 stale 판정

## 근거
- [x] startup-dominating toxic seed 제거 후 새 signal이 나옴
- [x] base seed는 clean하고 mutated artifact에서 leak 발생
- [x] deeper-path signal은 이미 확보됨
- [x] 지금은 promotion보다 classification이 우선

## 지금 하지 말 것
- [x] deeper promotion
- [x] broad seed rewrite
- [x] premature patching
- [x] leak detection disable

## 다음 review 포인트
- [x] saved leak artifact 재현성
- [x] clean parent seed 비교
- [x] `j2k_tile::decode()` cleanup/lifetime 검토
- [x] decoder invoke / reuse 정책 검토
- [x] decoder bug vs harness artifact 분류
