# Hermes Watch State Model Cleanup Checklist

**Goal:** refiner pipeline의 분산 상태 필드를 유지한 채, 우선 canonical lifecycle field를 도입해 상태 해석을 일관되게 만든다.

**Scope:** 이번 단계는 파괴적 리팩터링 없이
- lifecycle derivation helper 추가
- 각 단계 mutation 시 lifecycle 동기화
- 테스트로 주요 phase invariant 고정
까지 한다.

---

## 냉정한 사전 평가

### 현재 상태
- `status`, `orchestration_status`, `dispatch_status`, `bridge_status`, `launch_status`, `verification_status`, `verification_policy_status`가 분산돼 있다.
- 특히 `status=completed`가 plan-emitted 수준인데 의미가 과장돼 있다.
- 지금 당장 전체 상태모델을 갈아엎기보다, 먼저 **canonical lifecycle field**를 추가하는 게 안전하다.

### 이번 단계에서 실제로 붙일 것
- `derive_refiner_lifecycle(...)`
- `sync_refiner_lifecycle(...)`
- executor/orchestration/dispatch/bridge/launch/verify/policy 단계에서 lifecycle 기록
- lifecycle-focused 테스트 추가

### 이번 단계에서 일부러 안 할 것
- 기존 status 필드 제거
- registry 스키마 대개편
- retry runner 실제 실행 의미 변경

### 설계 원칙
- additive change 우선
- 기존 필드는 compatibility 때문에 유지
- lifecycle는 single source of truth 후보로 먼저 도입

---

## 작업 체크리스트

### Phase 1 — 구조 설계
- [ ] canonical lifecycle enum 정의
- [ ] existing field -> lifecycle mapping 정의
- [ ] terminal/non-terminal phase 구분

### Phase 2 — 테스트 먼저 작성
- [ ] lifecycle derivation helper 테스트
- [ ] executor -> planned lifecycle 테스트
- [ ] dispatch/bridge/launch/verify/policy lifecycle progression 테스트
- [ ] 먼저 테스트를 돌려 failure 확인

### Phase 3 — 구현
- [ ] lifecycle helper 추가
- [ ] 단계별 mutation에 lifecycle sync 추가
- [ ] selected finder functions가 lifecycle와 모순되지 않는지 확인

### Phase 4 — 검증
- [ ] targeted lifecycle tests 실행
- [ ] full watcher tests 실행
- [ ] 회귀 확인

### Phase 5 — 냉정한 사후 평가
- [ ] 아직 legacy fields가 남아 있다는 점 명시
- [ ] 다음 단계에서 finder/state transition을 lifecycle 우선으로 바꿀지 결정 포인트 기록

---

## 성공 기준
- 주요 refiner entries에 canonical lifecycle field가 남는다.
- lifecycle가 단계 의미를 기존 분산 필드보다 더 명확히 표현한다.
- 전체 테스트가 유지된다.

## 실패 기준
- lifecycle가 기존 상태와 자주 모순된다.
- 기존 테스트/흐름을 크게 깨뜨린다.
- additive가 아니라 파괴적 리팩터링이 되어버린다.

## 한 줄 냉정 평가 기준
**이번 단계가 끝나면 watcher는 분산 상태 필드 위에 canonical lifecycle field를 얹어, refiner work의 실제 단계 의미를 일관되게 기록한다.**
