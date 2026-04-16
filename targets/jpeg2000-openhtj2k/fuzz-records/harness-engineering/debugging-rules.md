# Harness Debugging Rules

## 기본 원칙
- build/smoke 성공만으로 하네스 개선이라고 부르지 않는다.
- 진짜 기준은 `stage reach`, `duplicate pressure`, `crash quality`다.
- 먼저 evidence를 읽고, 나중에 source를 읽는다.
- seed toxicity 문제를 harness 구조 문제로 오진하지 않는다.

## 수정 전 확인
- 현재 병목이 build/smoke/probe/fuzz 중 어디인지 적는다.
- shallow duplicate dominance인지 적는다.
- 이번 수정이 기대하는 signal 변화 1~3개를 적는다.

## 수정 후 확인
- 기대한 signal이 실제로 바뀌었는지 비교한다.
- 더 깊은 stage로 갔는지 본다.
- duplicate family 재발견 압력이 줄었는지 본다.
- fake fix(build-friendly but fuzz-useless) 여부를 의심한다.
