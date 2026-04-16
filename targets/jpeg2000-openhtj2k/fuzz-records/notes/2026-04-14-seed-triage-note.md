# Seed Triage Note — 2026-04-14

## 확인된 사실
- `fuzz/corpus/valid/p0_12.j2k`가 smoke와 fuzz 양쪽에서 동일한 UBSan 이슈를 유발함
- 생성된 crash artifact의 SHA1이 기존 corpus seed와 동일함

## 의미
- 현재 crash는 새 mutation 발견이라기보다 **baseline corpus의 known-bad seed** 성격이 강함
- 따라서 coverage 관찰용 러닝과 crash 재현/수정용 러닝을 분리하는 게 좋음

## 권장 운영
### A. clean-corpus run
- 즉시 크래시를 일으키지 않는 seed만 사용
- 목적: coverage/ft/corpus 성장 확인

### B. triage run
- `p0_12.j2k` 유지
- 목적: sanitizer stack 재현, 원인 분석, 수정 검증

## 다음 액션 후보
- `fuzz/corpus/valid`를 clean / triage로 분리
- watcher나 run script에 corpus override를 붙여 모드별 실행 가능하게 하기
