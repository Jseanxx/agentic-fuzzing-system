# Hermes Watch Timeout/Corpus Trigger Checklist

**Goal:** `hermes_watch.py`가 history registry를 바탕으로 `timeout_surge`와 `corpus_bloat_low_gain`의 보수적 subset을 평가하도록 만든다.

**Scope:** 이번 단계는 **timeout rate + corpus growth 대비 coverage gain**만 다룬다. stability trend는 다음 단계로 미룬다.

---

## 냉정한 사전 평가

### 현재 상태
- recent run history 저장 완료
- `coverage_plateau` / `shallow_crash_dominance` subset 평가 완료
- 하지만 timeout pressure와 corpus quality 저하를 아직 history decision에 못 쓴다.

### 현실적인 제한
이번에도 아래는 아직 어렵다.
- full `stability_drop`
- corpus minimization의 실제 실행
- timeout root-cause 분해(느린 seed vs harness 자체 문제)

### 이번 단계에서 실제로 붙일 것
- history에 `timeout_detected`, `corpus_units`, `seconds_since_progress` 기록
- `timeout_surge`의 history-based subset 평가
- `corpus_bloat_low_gain`의 history-based subset 평가

### 설계 원칙
- timeout_surge는 최근 run 수가 충분하고 timeout 비율이 명확히 높을 때만 발동
- corpus_bloat는 corpus 증가가 큰데 coverage gain이 작을 때만 발동
- 표본 부족 / missing field가 있으면 미발동이 기본
- 오탐보다 미탐이 낫다

---

## 작업 체크리스트

### Phase 1 — 구조 확인
- [x] history에 추가 저장할 필드 정의
- [x] timeout/corpus trigger 계산 규칙 정의
- [x] 현재 데이터로 계산 가능한 보수적 subset 확정

### Phase 2 — 테스트 먼저 작성
- [x] timeout_surge 감지 테스트 추가
- [x] corpus_bloat_low_gain 감지 테스트 추가
- [x] 데이터 부족 시 미발동 테스트 추가
- [x] history append가 새 필드를 저장하는지 테스트 추가
- [x] 먼저 테스트를 돌려 실패 확인

### Phase 3 — 구현
- [x] history append 필드 확장
- [x] timeout_surge evaluator 추가
- [x] corpus_bloat_low_gain evaluator 추가
- [x] history override를 policy decision에 병합

### Phase 4 — 검증
- [x] 신규 테스트 실행
- [x] 전체 watcher 테스트 실행
- [x] 실패 시 root cause 확인 후 수정

### Phase 5 — 냉정한 사후 평가
- [x] 지원되는 trigger subset 명시
- [x] 아직 미지원인 stability/semantic telemetry 명시
- [x] 다음 단계 요구사항 적기

---

## 성공 기준
- recent timeout pressure를 watcher가 감지한다.
- corpus growth 대비 coverage gain 저하를 watcher가 감지한다.
- 결과가 policy action으로 반영된다.
- 전체 테스트가 유지된다.

## 실패 기준
- timeout 한두 번으로 쉽게 overreact 한다.
- corpus_units만 커졌다고 무조건 bloat로 본다.
- missing data를 0으로 간주해 오탐을 만든다.

## 한 줄 냉정 평가 기준
**이번 단계가 끝나면 watcher는 stage/cov뿐 아니라 자원 소모 패턴까지 일부 해석하는 운영 refiner에 가까워진다.**
