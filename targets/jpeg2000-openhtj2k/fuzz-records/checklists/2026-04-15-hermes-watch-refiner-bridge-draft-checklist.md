# Hermes Watch Refiner Bridge Draft Checklist

**Goal:** `hermes_watch.py`가 ready refiner dispatch entry를 읽고, 실제 Hermes CLI를 통해 **cronjob / delegate_task tool call**을 수행할 수 있는 bridge script까지 만든다.

**Scope:** 이번 단계는 직접 live 실행은 하지 않고,
- ready entry 탐색
- channel별 Hermes CLI bridge prompt/script 생성
- registry bridge 상태 기록
- CLI bridge-only 진입점
까지 한다.

---

## 냉정한 사전 평가

### 현재 상태
- queue -> plan -> orchestration bundle -> dispatch request 까지는 생겼다.
- 하지만 아직 실제 Hermes tool call로 넘기는 마지막 다리가 없다.
- 특히 `delegate_task`는 일반 Python 런타임에서 직접 못 부르므로 bridge 계층이 필요하다.

### 이번 단계에서 실제로 붙일 것
- ready entry finder
- `hermes chat` 기반 delegate bridge script
- `hermes cron create` 기반 cron bridge script
- bridge prompt/script 경로 기록
- CLI `--bridge-refiner-dispatch` 추가

### 이번 단계에서 일부러 안 할 것
- bridge script 자동 실행
- unattended destructive corpus mutation
- actual harness patch 자동 적용
- dispatch success/failure runtime feedback loop 완성

### 설계 원칙
- bridge script는 **실제 tool call을 수행하는 CLI command**를 포함해야 한다.
- low-risk를 위해 generation 단계와 live execution 단계를 분리한다.
- registry에는 `ready -> armed`까지만 기록한다.

---

## 작업 체크리스트

### Phase 1 — 구조 설계
- [x] ready entry 조건 정의
- [x] delegate bridge prompt/script 구조 정의
- [x] cron bridge script 구조 정의
- [x] bridge 상태 이름 정의

### Phase 2 — 테스트 먼저 작성
- [x] delegate bridge script 생성 테스트
- [x] cron bridge script 생성 테스트
- [x] ready entry 없음 테스트
- [x] 먼저 테스트를 돌려 실패 확인

### Phase 3 — 구현
- [x] `find_ready_refiner_entry(...)` 추가
- [x] `build_delegate_bridge_prompt(...)` 추가
- [x] `write_delegate_bridge_bundle(...)` 추가
- [x] `write_cron_bridge_bundle(...)` 추가
- [x] `bridge_next_refiner_dispatch(...)` 추가
- [x] CLI `--bridge-refiner-dispatch` 추가

### Phase 4 — 검증
- [x] bridge draft 테스트 실행
- [x] orchestration/dispatch/bridge 묶음 테스트 실행
- [x] 전체 watcher 테스트 실행

### Phase 5 — 냉정한 사후 평가
- [x] 이 단계가 live execution이 아니라 armed bridge script 단계임을 명시
- [x] 다음 단계 actual runner/feedback loop 위치를 남김

---

## 성공 기준
- ready entry에서 실제 Hermes CLI command가 들어 있는 bridge script가 생성된다.
- registry에 `bridge_status`와 `bridge_script_path`가 기록된다.
- full test suite가 유지된다.

## 실패 기준
- bridge script가 실제 tool call command를 포함하지 않는다.
- direct execution과 armed 상태가 섞여서 상태 머신이 불명확해진다.
- destructive action이 live run 없이도 섞인다.

## 한 줄 냉정 평가 기준
**이번 단계가 끝나면 watcher는 ready refiner dispatch를 실제 Hermes CLI가 cronjob/delegate_task tool call로 넘길 수 있는 bridge script까지 자동 생성한다.**
