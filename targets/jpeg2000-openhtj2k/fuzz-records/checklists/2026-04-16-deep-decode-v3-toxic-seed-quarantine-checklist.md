# Deep Decode V3 Toxic Seed Quarantine Checklist

- Updated: 2026-04-16 18:34:58 KST
- Project: `fuzzing-jpeg2000`

---

## 목표
- [x] startup-dominating reproducer가 active corpus를 지배하는지 확인
- [x] 해당 seed를 triage/regression으로 보존하고 active corpus에서 제거
- [x] 재실행 후 mutation-time signal이 다시 보이는지 확인

## 확인
- [x] `sha1sum`으로 crash artifact와 `p0_11.latebodyflip.j2k` 동일성 확인
- [x] active corpus path
  - [x] `fuzz/corpus-afl/deep-decode-v3/p0_11.latebodyflip.j2k`
- [x] quarantine 보존 경로
  - [x] `fuzz/corpus/triage/p0_11.latebodyflip.j2k`
  - [x] `fuzz/corpus/regression/p0_11.latebodyflip.j2k`

## 실행
- [x] toxic seed를 active corpus에서 제거
- [x] watcher 재실행
- [x] evidence packet 재생성

## 결과
- [x] startup SEGV 반복 중단
- [x] deep-decode-v3 corpus 3개로 시작 확인
- [x] mutation-time leak signal 재등장 확인
- [x] same startup reproducer dominance 완화

## 냉정한 상태
- [x] corpus discipline은 개선됨
- [x] 새로운 leak signal triage는 아직 남아 있음
- [x] 즉 다음은 deeper promotion보다 triage/review가 더 우선일 수 있음
