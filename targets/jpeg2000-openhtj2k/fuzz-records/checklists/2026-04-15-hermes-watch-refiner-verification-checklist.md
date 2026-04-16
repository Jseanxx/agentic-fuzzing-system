# Hermes Watch Refiner Verification Checklist

**Goal:** launcher 성공 이후 실제로
- cron job이 scheduler에서 보이는지
- delegate child session과 artifact가 확인되는지
를 검증하고 registry에 `verified / unverified` 상태를 남긴다.

**Scope:** 이번 단계는 conservative verification만 한다.
- cron: `hermes cron list --all`에서 job id 확인
- delegate: `hermes sessions list --limit 200`에서 session id 확인 + artifact path 존재 확인

---

## 냉정한 사전 평가

### 현재 상태
- 시스템은 bridge script를 실행하고 결과를 파싱할 수 있다.
- 하지만 `succeeded`는 launch 성공일 뿐, 실제 상태 반영이 끝났다는 뜻은 아니다.
- 지금 필요한 건 `succeeded != verified`를 명확히 분리하는 것이다.

### 이번 단계에서 실제로 붙일 것
- verifiable entry finder
- cron visibility probe
- delegate session visibility probe
- delegate artifact existence check
- verification status / summary 기록
- CLI `--verify-refiner-result` 추가

### 이번 단계에서 일부러 안 할 것
- job/session 상세 metadata deep fetch
- async recheck/retry
- semantic artifact quality review
- scheduler/session DB direct parsing

### 설계 원칙
- verification은 **작고 보수적인 truth test**여야 한다.
- probe 실패나 evidence 부족은 억지 성공으로 올리지 않는다.
- parser/verification을 혼동하지 않고 단계 분리 유지한다.

---

## 작업 체크리스트

### Phase 1 — 구조 설계
- [x] verifiable entry 조건 정의
- [x] cron verification 기준 정의
- [x] delegate verification 기준 정의

### Phase 2 — 테스트 먼저 작성
- [x] cron existence verification 테스트
- [x] delegate session + artifact verification 테스트
- [x] verifiable entry 없음 테스트
- [x] 먼저 테스트를 돌려 실패 확인

### Phase 3 — 구현
- [x] `run_probe_command(...)` 추가
- [x] `find_verifiable_refiner_entry(...)` 추가
- [x] `verify_cron_entry(...)` 추가
- [x] `verify_delegate_entry(...)` 추가
- [x] `verify_next_refiner_result(...)` 추가
- [x] delegate parser에 artifact path 파싱 추가
- [x] CLI `--verify-refiner-result` 추가

### Phase 4 — 검증
- [x] verification 테스트 실행
- [x] launcher + verification 묶음 테스트 실행
- [x] 전체 watcher 테스트 실행

### Phase 5 — 냉정한 사후 평가
- [x] verification이 conservative subset임을 명시
- [x] 다음 단계 deeper evidence collection 필요성 기록

---

## 성공 기준
- cron result가 실제 list output에서 보이면 `verified`가 된다.
- delegate result가 session list와 artifact path 둘 다 확인되면 `verified`가 된다.
- full test suite가 유지된다.

## 실패 기준
- evidence 부족인데도 verified로 오판한다.
- cron/session probe 실패를 성공처럼 처리한다.
- artifact path 파싱이 잘못되어 존재하지 않는 파일을 성공으로 본다.

## 한 줄 냉정 평가 기준
**이번 단계가 끝나면 watcher는 launch 성공에서 멈추지 않고, cron 존재와 delegate artifact/session 가시성까지 확인해 `verified` 상태를 별도로 기록한다.**
