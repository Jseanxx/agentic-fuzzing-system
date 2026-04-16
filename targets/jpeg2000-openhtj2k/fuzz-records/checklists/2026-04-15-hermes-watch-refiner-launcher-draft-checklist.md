# Hermes Watch Refiner Launcher Draft Checklist

**Goal:** `hermes_watch.py`가 armed refiner bridge script를 실제로 실행하고, 결과를 registry에 기록하도록 만든다.

**Scope:** 이번 단계는 bridge script를 실제 실행하되,
- foreground launch
- stdout/stderr log 저장
- exit code 기록
- success/failure 상태 전이
까지 한다.

---

## 냉정한 사전 평가

### 현재 상태
- queue -> plan -> orchestration -> dispatch -> bridge script 까지는 이어졌다.
- 하지만 `armed` 상태가 아직 실제 실행으로 이어지지 않는다.
- 지금 병목은 script launch와 결과 기록이다.

### 이번 단계에서 실제로 붙일 것
- armed entry finder
- bridge script launcher
- launch log 저장
- exit code / success / failure 기록
- CLI `--launch-refiner-bridge` 추가

### 이번 단계에서 일부러 안 할 것
- background supervisor
- retry policy
- job/session id 파싱 고도화
- launcher success 이후 semantic verification

### 설계 원칙
- launch는 최대한 단순하고 관측 가능해야 한다.
- 결과는 `succeeded` / `failed`로 명확히 남긴다.
- script missing 같은 기본 실패도 registry에 기록한다.

---

## 작업 체크리스트

### Phase 1 — 구조 설계
- [x] armed entry 조건 정의
- [x] launch result 스키마 정의
- [x] launch log 경로 정의

### Phase 2 — 테스트 먼저 작성
- [x] 성공 launch 테스트
- [x] 실패 launch 테스트
- [x] armed entry 없음 테스트
- [x] 먼저 테스트를 돌려 실패 확인

### Phase 3 — 구현
- [x] `find_armed_refiner_entry(...)` 추가
- [x] `launch_bridge_script(...)` 추가
- [x] `launch_next_refiner_bridge(...)` 추가
- [x] CLI `--launch-refiner-bridge` 추가

### Phase 4 — 검증
- [x] launcher draft 테스트 실행
- [x] dispatch/bridge/launcher 묶음 테스트 실행
- [x] 전체 watcher 테스트 실행

### Phase 5 — 냉정한 사후 평가
- [x] foreground one-shot launcher 수준임을 명시
- [x] 다음 단계 retry / async supervision / result parsing 위치를 남김

---

## 성공 기준
- armed bridge script가 실제 실행된다.
- stdout/stderr가 launch log로 저장된다.
- registry에 exit code와 success/failure가 기록된다.
- full test suite가 유지된다.

## 실패 기준
- launch 결과가 registry에 안 남는다.
- success/failure 상태가 불명확하다.
- destructive action 통제가 무너진다.

## 한 줄 냉정 평가 기준
**이번 단계가 끝나면 watcher는 armed refiner bridge script를 실제로 실행하고, 그 결과를 registry에 남기는 launcher까지 가진다.**
