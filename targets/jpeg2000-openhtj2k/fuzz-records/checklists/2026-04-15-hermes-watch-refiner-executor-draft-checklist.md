# Hermes Watch Refiner Executor Draft Checklist

**Goal:** refiner registries를 실제로 소비하는 low-risk executor 초안을 붙인다.

---

## 냉정한 사전 평가
- 지금 단계에서 destructive mutation까지 자동화하면 오판 비용이 너무 크다.
- 따라서 executor 초안은 `registry -> completed status -> executable markdown plan` 수준으로 제한한다.
- 즉 real actuator가 아니라 safe executor draft로 간다.

## 체크리스트
### Phase 1 — 범위 정의
- [x] destructive mutation 제외
- [x] 지원 registry 범위 정의
- [x] completed/status 모델 정의

### Phase 2 — 테스트 먼저 작성
- [x] mode refinement executor 테스트
- [x] slow lane executor 테스트
- [x] corpus refinement executor 테스트
- [x] harness review executor 테스트
- [x] 먼저 실패 확인

### Phase 3 — 구현
- [x] slug/path helper 추가
- [x] markdown refiner plan writer 추가
- [x] registry 소비 executor 추가
- [x] completed/status/plan_path 기록 추가

### Phase 4 — 검증
- [x] 신규 테스트 통과
- [x] 전체 watcher 테스트 통과

## 성공 기준
- registry를 실제로 소비한다.
- completed 상태를 남긴다.
- repo 안에 refiner plan markdown를 생성한다.
- 회귀가 없다.

## 한 줄 냉정 평가
**이 단계는 실제 자동변경이 아니라, 다음 executor 계층이 바로 쓸 수 있는 안전한 실행 초안이다.**
