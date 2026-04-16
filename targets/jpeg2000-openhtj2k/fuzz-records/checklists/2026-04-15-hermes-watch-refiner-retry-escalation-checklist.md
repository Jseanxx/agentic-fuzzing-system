# Hermes Watch Refiner Retry Escalation Checklist

**Goal:** verification failure 결과를 보고 conservative retry / escalation state를 남기도록 만든다.

**Scope:** 이번 단계는 actual relaunch를 자동으로 하지는 않고,
- unverified/partial 상태 분류
- retry eligibility 계산
- escalation note 생성
- registry policy fields 업데이트
까지 한다.

---

## 냉정한 사전 평가

### 현재 상태
- system은 existence/metadata/shape/quality/lineage verification까지 한다.
- 하지만 verification 실패를 아직 운영 정책으로 바꾸지 못한다.
- 즉 signal은 있는데 action policy가 없다.

### 이번 단계에서 실제로 붙일 것
- verification result classification helper
- retry vs escalation decision helper
- escalation note / retry plan artifact 생성
- registry policy state를 기록

### 이번 단계에서 일부러 안 할 것
- actual automatic retry launch
- repeated backoff scheduler
- destructive cleanup on repeated failure

### 설계 원칙
- partial evidence는 무조건 실패로 취급하지 않고 분류한다.
- retry와 escalation은 low-risk artifact/state update로 먼저 연결한다.
- 과도한 auto-relaunch는 아직 금지한다.

---

## 작업 체크리스트

### Phase 1 — 구조 설계
- [x] verification failure classes 정의
- [x] retry eligibility 기준 정의
- [x] escalation artifact 경로 정의

### Phase 2 — 테스트 먼저 작성
- [x] cron unverified -> retry candidate 테스트
- [x] delegate shape/quality miss -> escalation 테스트
- [x] 반복 실패 -> escalation 강화 테스트
- [x] 먼저 테스트를 돌려 failure 확인

### Phase 3 — 구현
- [x] classification helper 추가
- [x] policy decision helper 추가
- [x] retry/escalation artifact writer 추가
- [x] registry policy fields 반영
- [x] CLI `--apply-verification-policy` 추가

### Phase 4 — 검증
- [x] targeted tests 실행
- [x] full watcher tests 실행
- [x] 회귀 확인

### Phase 5 — 냉정한 사후 평가
- [x] actual relaunch는 아직 안 한다는 점 명시
- [x] 다음 단계 actual retry runner 위치 기록

---

## 성공 기준
- verification 실패가 retry/escalation state로 구조화된다.
- 반복 실패와 quality/lineage miss가 구분된다.
- full test suite가 유지된다.

## 실패 기준
- 단순 unverified를 무조건 escalation으로 과민 반응한다.
- quality/lineage 실패를 단순 retry로 덮어버린다.
- auto-relaunch가 섞인다.

## 한 줄 냉정 평가 기준
**이번 단계가 끝나면 watcher는 verification failure를 보고 retry와 escalation을 구분하는 운영 정책 상태를 남긴다.**
