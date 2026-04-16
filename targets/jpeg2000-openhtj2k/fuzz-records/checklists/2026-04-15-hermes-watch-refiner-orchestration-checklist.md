# Hermes Watch Refiner Orchestration Checklist

**Goal:** `hermes_watch.py`의 safe refiner executor를 subagent/cron이 바로 집행할 수 있는 **orchestration bundle** 단계까지 연결한다.

**Scope:** 이번 단계는 실제 destructive action 없이, pending refiner entry를 소비한 뒤
- markdown plan
- subagent prompt
- cron prompt
- orchestration manifest
를 남기는 수준까지 한다.

---

## 냉정한 사전 평가

### 현재 상태
- watcher는 policy를 계산하고 structured refiner queue를 남긴다.
- executor 초안은 queue를 consume해서 markdown plan까지는 만든다.
- 하지만 그 다음에 **누가 plan을 실행할지**가 아직 비어 있다.

### 이번 단계에서 실제로 붙일 것
- `prepare_next_refiner_orchestration(...)` 추가
- action별 dispatch channel 기본값 정의
- `fuzz-records/refiner-orchestration/` 아래 prompt bundle 생성
- CLI에서 orchestration-only 실행 경로 추가

### 이번 단계에서 일부러 안 할 것
- 실제 cronjob 생성
- 실제 subagent 자동 실행
- 실제 corpus 삭제/이동
- 실제 harness 코드 수정
- 실제 mode switch 강제 실행

### 설계 원칙
- **runner-ready artifacts**를 남기되 아직 실행은 보수적으로 멈춘다.
- fresh session에 넣을 수 있는 self-contained prompt를 만든다.
- registry entry에 orchestration 상태를 기록해 다음 계층이 이어받기 쉽게 한다.

---

## 작업 체크리스트

### Phase 1 — 구조 설계
- [x] action별 default dispatch channel 정의
- [x] subagent prompt / cron prompt / manifest 스키마 정의
- [x] low-risk 경계 유지

### Phase 2 — 테스트 먼저 작성
- [x] mode refinement -> subagent bundle 테스트
- [x] corpus refinement -> cron bundle 테스트
- [x] pending 없음 -> `None` 반환 테스트
- [x] 먼저 테스트를 돌려 실패 확인

### Phase 3 — 구현
- [x] orchestration spec helper 추가
- [x] subagent prompt builder 추가
- [x] cron prompt builder 추가
- [x] orchestration manifest writer 추가
- [x] `prepare_next_refiner_orchestration(...)` 추가
- [x] CLI `--prepare-refiner-orchestration` 추가

### Phase 4 — 검증
- [x] 신규 orchestration 테스트 실행
- [x] 전체 watcher 테스트 실행
- [x] 회귀 없는지 확인

### Phase 5 — 냉정한 사후 평가
- [x] 이 단계가 실제 executor가 아니라 runner-ready bundle 단계임을 명시
- [x] 다음 단계에서 실제 cron/subagent dispatch를 붙일 위치를 남김

---

## 성공 기준
- pending refiner entry 하나를 consume하고 orchestration bundle을 남긴다.
- registry entry에 `orchestration_status`와 prompt path가 기록된다.
- full test suite가 유지된다.

## 실패 기준
- destructive mutation이 섞인다.
- cron/subagent 연결이 실제로는 여전히 수동 메모 수준에 머문다.
- prompt가 fresh session에서 쓰기 어려울 정도로 context가 비어 있다.

## 한 줄 냉정 평가 기준
**이번 단계가 끝나면 watcher는 단순히 plan만 쓰는 게 아니라, 다음 runner가 바로 집행할 수 있는 subagent/cron prompt bundle까지 자동으로 준비한다.**
