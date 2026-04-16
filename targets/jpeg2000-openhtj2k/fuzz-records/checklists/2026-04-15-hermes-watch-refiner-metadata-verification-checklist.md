# Hermes Watch Refiner Metadata Verification Checklist

**Goal:** verification 단계가 단순 존재 확인을 넘어서,
- cron metadata (name/schedule/deliver)
- delegate artifact shape/section
까지 확인하도록 만든다.

**Scope:** 이번 단계는 conservative metadata/shape verification만 한다.
- cron: `hermes cron list --all` output 내 expected metadata substring 확인
- delegate: artifact file 안 expected section headings 존재 확인

---

## 냉정한 사전 평가

### 현재 상태
- system은 launch success와 verified를 분리했다.
- 하지만 verified 기준이 아직 "보인다/존재한다" 수준이다.
- 지금 부족한 건 **맞는 것이 생성됐는지** 확인하는 얕은 shape check다.

### 이번 단계에서 실제로 붙일 것
- cron metadata visibility helper
- delegate artifact section/shape helper
- verification summary refinement
- delegate parser artifact path 연계 유지

### 이번 단계에서 일부러 안 할 것
- cron prompt/body deep equality 검증
- markdown semantic quality scoring
- artifact content LLM review
- retry/reprobe policy

### 설계 원칙
- substring/section 기반의 **보수적 shape verification**까지만 한다.
- 오탐이 생길 수 있는 과도한 semantic 판정은 아직 하지 않는다.
- metadata가 주어지지 않은 경우 기존 존재 verification을 깨지 않는다.

---

## 작업 체크리스트

### Phase 1 — 구조 설계
- [x] cron metadata verification 기준 정의
- [x] delegate expected sections verification 기준 정의
- [x] backward-compatible summary rules 정의

### Phase 2 — 테스트 먼저 작성
- [x] cron metadata verification 테스트
- [x] delegate artifact shape verification 테스트
- [x] 먼저 테스트를 돌려 failure 확인

### Phase 3 — 구현
- [x] `cron_metadata_visible(...)` 추가
- [x] `delegate_artifact_shape_visible(...)` 추가
- [x] `verify_cron_entry(...)` 확장
- [x] `verify_delegate_entry(...)` 확장

### Phase 4 — 검증
- [x] verification 테스트 재실행
- [x] launcher + verification 묶음 테스트 실행
- [x] 전체 watcher 테스트 실행

### Phase 5 — 냉정한 사후 평가
- [x] metadata/shape verification은 shallow subset임을 명시
- [x] 다음 단계 semantic content verification 필요성 기록

---

## 성공 기준
- cron verification이 job visibility뿐 아니라 metadata visibility도 구분 기록한다.
- delegate verification이 artifact 존재뿐 아니라 expected section presence도 기록한다.
- full test suite가 유지된다.

## 실패 기준
- metadata가 없는 기존 entry를 불필요하게 unverified로 내린다.
- artifact shape 검증이 optional/required 구분 없이 동작해 오탐을 만든다.
- substring 수준 검증을 semantic truth처럼 과장한다.

## 한 줄 냉정 평가 기준
**이번 단계가 끝나면 watcher는 단순 존재 확인을 넘어서, cron metadata와 delegate artifact section shape까지 보수적으로 검증한다.**
