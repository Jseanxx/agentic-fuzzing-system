# Hermes Watch Refiner Result Parsing Checklist

**Goal:** launcher가 bridge script 실행 결과에서 **cron job id / delegate child 결과 요약**을 파싱하고 registry에 반영하게 만든다.

**Scope:** 이번 단계는 launch 결과 로그를 해석해서
- cron job id
- delegate session id
- delegate status
- delegate summary
- bridge result summary
를 registry와 launcher 반환값에 반영하는 수준까지 한다.

---

## 냉정한 사전 평가

### 현재 상태
- launcher는 armed bridge script를 실제 실행한다.
- stdout/stderr와 exit code는 남긴다.
- 하지만 실행이 성공해도 **무엇이 실제로 생성되었는지** 구조적으로 못 읽는다.

### 이번 단계에서 실제로 붙일 것
- cron bridge output parser
- delegate bridge output parser
- channel-aware result extraction helper
- parsed metadata registry 반영

### 이번 단계에서 일부러 안 할 것
- cron CLI 실제 다양한 출력 포맷 전부 지원
- delegate child transcript 심층 요약
- semantic success verification
- retry/repair policy

### 설계 원칙
- 먼저 **작고 명확한 패턴**만 파싱한다.
- output 포맷이 불명확하면 억지 추론하지 않는다.
- 파싱 실패는 무시 가능하지만, 오탐 파싱은 위험하므로 보수적으로 간다.

---

## 작업 체크리스트

### Phase 1 — 구조 설계
- [x] cron output 패턴 정의
- [x] delegate output 패턴 정의
- [x] channel-aware extraction helper 정의

### Phase 2 — 테스트 먼저 작성
- [x] cron job id 파싱 테스트
- [x] delegate child result 파싱 테스트
- [x] 먼저 테스트를 돌려 실패 확인

### Phase 3 — 구현
- [x] `parse_cron_bridge_output(...)` 추가
- [x] `parse_delegate_bridge_output(...)` 추가
- [x] `extract_bridge_result_metadata(...)` 추가
- [x] launcher registry/result merge 연결

### Phase 4 — 검증
- [x] launcher 테스트 재실행
- [x] dispatch/bridge/launcher 묶음 테스트 실행
- [x] 전체 watcher 테스트 실행

### Phase 5 — 냉정한 사후 평가
- [x] parser가 아직 conservative subset임을 명시
- [x] 다음 단계에서 actual CLI output fixture 확대가 필요하다고 기록

---

## 성공 기준
- cron launch 성공 시 `cron_job_id`가 registry에 들어간다.
- delegate launch 성공 시 session/status/summary가 registry에 들어간다.
- full test suite가 유지된다.

## 실패 기준
- 잘못된 문자열을 job id/session id로 오탐한다.
- parser가 output variation에 과신해서 거짓 성공을 만든다.
- launcher가 원래 남기던 기본 성공/실패 상태를 깨뜨린다.

## 한 줄 냉정 평가 기준
**이번 단계가 끝나면 watcher는 bridge script를 실행하는 데서 멈추지 않고, 그 결과에서 cron job id와 delegate child 요약까지 구조적으로 회수한다.**
