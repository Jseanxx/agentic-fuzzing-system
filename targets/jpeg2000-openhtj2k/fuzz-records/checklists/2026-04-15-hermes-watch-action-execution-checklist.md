# Hermes Watch Action Execution Checklist

**Goal:** `hermes_watch.py`가 policy decision을 실제 후속 작업 아티팩트로 연결하도록 만든다.

**Scope:** 이번 단계는 destructive mutation 없이 **structured refiner registries**를 실제로 생성/갱신하는 수준까지 한다.

---

## 냉정한 사전 평가

### 현재 상태
- watcher가 action code는 계산한다.
- 하지만 대부분 action code가 아직 recommendation 문자열에 머문다.
- 즉 decision은 생겼지만 execution path가 약하다.

### 이번 단계에서 실제로 붙일 것
- `shift_weight_to_deeper_harness` -> mode refinement registry
- `split_slow_lane` -> slow lane candidate registry
- `minimize_and_reseed` -> corpus refinement registry
- `halt_and_review_harness` -> harness review registry

### 이번 단계에서 일부러 안 할 것
- 실제 하네스 코드 자동 수정
- 실제 corpus minimization 실행
- 실제 fuzz mode 자동 전환
- destructive file moves/deletes

### 설계 원칙
- recommendation-only 상태를 넘어서, **기계가 후속 처리할 structured queue**를 남긴다.
- side effect는 low-risk registry write 수준으로 제한한다.
- 오판 시 복구 가능해야 한다.

---

## 작업 체크리스트

### Phase 1 — 구조 확인
- [x] action code별 target registry 정의
- [x] registry 스키마 정의
- [x] low-risk execution 범위 확정

### Phase 2 — 테스트 먼저 작성
- [x] shift_weight_to_deeper_harness registry 기록 테스트
- [x] split_slow_lane registry 기록 테스트
- [x] minimize_and_reseed registry 기록 테스트
- [x] halt_and_review_harness registry 기록 테스트
- [x] 먼저 테스트를 돌려 실패 확인

### Phase 3 — 구현
- [x] refiner registry helper 추가
- [x] apply_policy_action에 action code별 registry write 연결
- [x] policy_execution updated 목록에 반영

### Phase 4 — 검증
- [x] 신규 테스트 실행
- [x] 전체 watcher 테스트 실행
- [x] 실패 시 root cause 확인 후 수정

### Phase 5 — 냉정한 사후 평가
- [x] execution이 실제 mutation인지 registry 수준인지 명확히 구분
- [x] 다음 단계에서 어느 registry를 실제 executor와 연결할지 적기

---

## 성공 기준
- 주요 refiner action code가 실제 registry 파일을 남긴다.
- 전체 watcher 테스트가 유지된다.
- side effect가 low-risk 수준에 머문다.

## 실패 기준
- destructive mutation이 섞인다.
- action code가 여전히 사실상 no-op이다.
- registry 스키마가 너무 불안정해서 후속 executor가 쓰기 어렵다.

## 한 줄 냉정 평가 기준
**이번 단계가 끝나면 watcher는 단순 판단기가 아니라, 다음 자동화 단계가 소비할 structured refiner work queue를 실제로 생산한다.**
