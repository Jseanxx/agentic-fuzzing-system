# Hermes Watch Runtime Hardening — Timeout + Env Parsing Checklist

**Goal:** R20로 가기 전, 운영 안정성의 가장 값싼 취약점 두 개를 먼저 막는다.
- subprocess hang에 대한 기본 timeout
- 잘못된 환경변수 정수값 때문에 main이 즉시 죽는 문제

---

## 냉정한 사전 평가
- 지금 시스템의 큰 리스크는 state-machine drift, artifact-heavy drift, runtime robustness 부족이다.
- 이 중 지금 바로 저위험으로 줄일 수 있는 건:
  1. `launch_bridge_script(...)` / `run_probe_command(...)` timeout 부재
  2. `MAX_TOTAL_TIME`, `NO_PROGRESS_SECONDS`, `PROGRESS_INTERVAL_SECONDS`의 직접 `int(...)` 파싱
- 이 단계는 구조 대수술이 아니라, 실제 운영에서 가장 싸게 죽는 경로를 먼저 막는 목적이다.

---

## 작업 체크리스트

### Phase 1 — 범위 확정
- [x] 이번 단계는 lifecycle 개편이 아니라 runtime hardening의 작은 첫 조각으로 제한
- [x] 대상 함수 확정
  - `launch_bridge_script(...)`
  - `run_probe_command(...)`
  - `main()`의 env default parsing

### Phase 2 — 테스트 먼저 작성
- [x] bridge script timeout 테스트
- [x] probe command timeout 테스트
- [x] invalid env int fallback 테스트
- [x] 먼저 테스트를 돌려 failure 확인

### Phase 3 — 구현
- [x] subprocess timeout handling 추가
- [x] timeout 결과를 registry/return value에서 구분 가능하게 유지
- [x] env int parsing helper 추가
- [x] `main()` default parsing을 helper로 교체

### Phase 4 — 검증
- [x] 타깃 테스트 재실행
- [x] `tests/test_hermes_watch.py` 전체 실행
- [x] `pytest tests -q` 전체 실행
- [x] `py_compile` 검증

### Phase 5 — 사후 평가
- [x] timeout/env parsing hardening만 했음을 명시
- [x] 다음 단계로 lifecycle cleanup과 malformed nested registry hardening을 남김

---

## 성공 기준
- bridge/probe subprocess가 hang하더라도 제한 시간 후 실패로 회수된다.
- 잘못된 정수 env 값이 있어도 `main()` 진입이 죽지 않고 안전한 default로 복구된다.
- 기존 테스트가 유지된다.

## 한 줄 냉정 평가 기준
**이번 단계가 끝나면 watcher는 가장 값싼 운영 취약점 두 개(timeout 부재, invalid env int)를 더 안전하게 처리한다.**
