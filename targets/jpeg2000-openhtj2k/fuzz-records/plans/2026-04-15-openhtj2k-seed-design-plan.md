# OpenHTJ2K Seed Design Plan

> Goal: 방어 가치가 높은 memory-safety finding을 더 잘 드러내기 위해 seed를 구조적으로 설계하고, coverage를 오염시키는 toxic seed를 분리한다.

Date: 2026-04-15
Repo: `/home/hermes/work/fuzzing-jpeg2000`

---

## Seed design principles

좋은 seed는 단순히 많다고 좋은 게 아니다.
중요한 건 아래 세 가지다.

1. 깊은 경로에 들어갈 것
2. 매번 동일 crash로 즉사하지 않을 것
3. parser / tile / cleanup 경로 다양성을 줄 것

---

## Bucket model

### coverage bucket
Path:
- `fuzz/corpus/coverage/`

Purpose:
- 새로운 distinct finding 탐색
- 깊은 경로 진입
- 즉사 toxic seed 최소화

Include:
- [ ] clean baseline decodable seed
- [ ] 구조가 서로 다른 정상/near-valid seed
- [ ] marker variation seed
- [ ] tile layout variation seed

Exclude:
- [ ] 매번 같은 crash로 바로 죽는 toxic seed
- [ ] triage 전용 known-bad reproducer

### triage bucket
Path:
- `fuzz/corpus/triage/`

Purpose:
- distinct crash artifact 재현
- 새 finding 분석

Include:
- [ ] 새 crash artifact
- [ ] toxic seed로 판정된 coverage seed
- [ ] parser-side / lifecycle-side 대표 reproducer

### regression bucket
Path:
- `fuzz/corpus/regression/`

Purpose:
- known issue 재현 확인
- 수정 후 재실행

Include:
- [ ] `p0_12.j2k` lineage
- [ ] smoke failure seed
- [ ] distinct crash 중 유지 가치 높은 것

### known-bad bucket
Path:
- `fuzz/corpus/known-bad/`

Purpose:
- coverage 오염 방지
- toxic artifact 분리 보존

Include:
- [ ] crash artifact
- [ ] duplicate toxic seed

---

## OpenHTJ2K-specific seed categories

### Category A — clean decodable baseline
Examples:
- `ds0_ht_12_b11.j2k`
- `p0_11.j2k`

Why:
- parser + decode 정상 경로 baseline 제공
- coverage 시작점으로 중요

### Category B — known failing regression seed
Examples:
- `p0_12.j2k`

Why:
- smoke known issue 재현
- regression 필수
- coverage에는 직접 섞지 않음

### Category C — parser-stressing near-valid seed
Characteristics:
- marker sequence는 대체로 맞음
- segment length / truncation / marker boundary 일부 깨짐
- parser가 충분히 진행하다 실패함

Why:
- `j2kmarkers.cpp` 같은 parser-side OOB/HBO를 더 잘 노출

### Category D — tile/packet layout stressing seed
Characteristics:
- tile-part layout 다양성
- packet / codeblock path 진입 가능
- decode deeper path 도달 가능

Why:
- `coding_units.cpp` / tile-part lifecycle 계열 crash 노출 가능성 증가

### Category E — cleanup-stressing seed
Characteristics:
- 어느 정도 parse/decode 진행 후 실패
- partial allocation/free 경로 유도
- truncated but near-valid profile

Why:
- UAF / invalid free / stale pointer / cleanup race-like lifetime bug 노출 가능성 상승

---

## Seed construction workflow

### Step 1 — curate baseline set
- [ ] 가장 작은 decodable seed 선정
- [ ] marker/layout이 다른 정상 seed 선정
- [ ] 현재 coverage bucket에서 toxic seed 제거

### Step 2 — derive near-valid parser seeds
- [ ] 정상 seed에서 tail truncation 파생
- [ ] marker length mismatch 파생
- [ ] marker sequence corruption 파생
- [ ] parser reject만 유도하는 완전 garbage는 비중 낮춤

### Step 3 — derive cleanup/lifecycle seeds
- [ ] 정상 seed 일부 body corruption
- [ ] deep path 진입 후 실패 유도
- [ ] tile/packet/codeblock 관련 구조 손상 seed 생성

### Step 4 — triage feedback loop
- [ ] 새 crash artifact를 triage로 편입
- [ ] coverage를 오염시키는 base seed는 triage/known-bad로 격리
- [ ] distinct finding이면 regression 편입 여부 판단

---

## Toxic seed rules

A seed is toxic for coverage if:
- [ ] 거의 항상 같은 crash만 즉시 유도함
- [ ] distinct finding 다양성을 막음
- [ ] path 깊이보다 crash fixation이 더 강함

Action:
- [ ] coverage에서 제거
- [ ] triage 또는 known-bad로 이동
- [ ] regression 가치가 있으면 regression에 별도 유지

---

## Seed quality review rubric

### Strong coverage seed
- [ ] decode path를 충분히 탐
- [ ] 즉사하지 않음
- [ ] parser/marker/tile 다양성을 줌

### Strong regression seed
- [ ] 특정 crash/UBSan issue를 안정적으로 재현
- [ ] 수정 후 재검증 가치가 큼

### Strong triage seed
- [ ] artifact 기반 distinct finding 재현 가능
- [ ] analysis에 필요한 최소 재현성 보장

---

## Immediate concrete actions

1. `coverage/`에서 현재 parser-side, lifecycle-side toxic seed 재검토
2. `p0_12.j2k`는 coverage에서 계속 제외
3. 최근 crash artifacts 2개는 triage 유지
4. near-valid truncation seed 세트 별도 생성
5. parser-heavy seed와 lifecycle-heavy seed를 coverage 내부에서도 서브세트로 관리 검토

---

## Bottom line

OpenHTJ2K seed 전략의 핵심은:
- 정상 seed를 무작정 많이 넣는 것이 아니라
- **깊게 들어가되 즉사하지 않는 coverage seed**와
- **재현성을 가진 triage/regression seed**를 분리하는 것이다.
