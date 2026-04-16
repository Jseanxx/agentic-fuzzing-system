# Hermes Watch Refiner Dispatch Draft Checklist

**Goal:** `hermes_watch.py`가 prepared orchestration bundle을 읽고, 다음 실행 계층이 바로 사용할 수 있는 **delegate_task / cronjob request artifact**까지 만든다.

**Scope:** 이번 단계는 실제 destructive action이나 자동 코드 수정 없이,
- prepared refiner entry 탐색
- channel별 dispatch request 생성
- registry dispatch 상태 기록
- CLI dispatch-only 진입점
까지 한다.

---

## 냉정한 사전 평가

### 현재 상태
- watcher는 queue를 consume해서 executor plan을 만든다.
- orchestration 단계는 subagent/cron prompt bundle까지 만든다.
- 하지만 다음 계층이 실제로 어떤 tool payload를 써야 하는지 아직 비어 있다.

### 이번 단계에서 실제로 붙일 것
- prepared entry 탐색기
- `delegate_task`용 request JSON 생성
- `cronjob create`용 request JSON 생성
- dispatch registry fields 기록
- CLI `--dispatch-refiner-orchestration` 추가

### 이번 단계에서 일부러 안 할 것
- repo runtime 내부에서 실제 Hermes tool 직접 호출
- destructive corpus mutation
- 실제 harness patch 자동 적용
- unattended code rewrite

### 설계 원칙
- tool schema에 맞는 **exact request artifact**를 남긴다.
- state transition은 `prepared -> ready` 수준으로 보수적으로 둔다.
- fresh session/runner가 그대로 집어가도 되도록 payload를 self-contained에 가깝게 만든다.

---

## 작업 체크리스트

### Phase 1 — 구조 설계
- [x] action별 subagent toolsets / cron schedule 기본값 정의
- [x] prepared entry 선택 조건 정의
- [x] dispatch artifact 경로 정의

### Phase 2 — 테스트 먼저 작성
- [x] subagent delegate request 생성 테스트
- [x] cronjob request 생성 테스트
- [x] prepared entry 없음 테스트
- [x] 먼저 테스트를 돌려 실패 확인

### Phase 3 — 구현
- [x] prepared entry finder 추가
- [x] delegate request builder 추가
- [x] cronjob request builder 추가
- [x] dispatch bundle writer 추가
- [x] `dispatch_next_refiner_orchestration(...)` 추가
- [x] CLI dispatch-only 경로 추가

### Phase 4 — 검증
- [x] dispatch draft 테스트 실행
- [x] orchestration 관련 테스트 재실행
- [x] 전체 watcher 테스트 실행

### Phase 5 — 냉정한 사후 평가
- [x] 이것이 direct tool invocation이 아니라 tool-aligned request artifact 단계임을 명시
- [x] 다음 단계 actual runner/bridge 위치를 남김

---

## 성공 기준
- prepared refiner entry에서 channel별 request JSON이 생성된다.
- registry에 `dispatch_status`와 request path가 기록된다.
- full test suite가 유지된다.

## 실패 기준
- request payload가 tool schema와 어긋난다.
- dispatch 상태가 실제 실행과 초안 단계를 혼동하게 만든다.
- 자동 destructive action이 슬며시 섞인다.

## 한 줄 냉정 평가 기준
**이번 단계가 끝나면 watcher는 prepared refiner work를 실제 Hermes runner가 바로 집어갈 수 있는 delegate_task / cronjob request artifact로 변환한다.**
