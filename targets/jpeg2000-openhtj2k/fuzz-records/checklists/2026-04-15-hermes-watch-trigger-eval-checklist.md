# Hermes Watch Trigger Evaluation Checklist

**Goal:** `hermes_watch.py`가 target profile의 `crash_policy`와 `triggers` 일부를 실제로 읽고 policy decision에 반영하도록 만든다.

**Scope:** 이번 단계는 **profile-driven severity/bucket override + 현재 watcher가 계산 가능한 trigger subset 평가**까지만 한다.

---

## 냉정한 사전 평가

### 현재 상태
- target profile 로딩 완료
- stage tagging 완료
- 하지만 policy decision은 아직 하드코딩된 watcher 로직이다.

### 현실적인 제한
다음 trigger들은 지금 당장 정확히 계산하기 어렵다.
- `coverage_plateau`
- `shallow_crash_dominance`
- `timeout_surge`
- `corpus_bloat_low_gain`
- `stability_drop`

이유:
- watcher가 아직 history window / corpus trend / stability telemetry를 충분히 계산하지 않음
- 즉 프로파일은 있어도 입력 telemetry가 아직 부족함

### 이번 단계에서 실제로 붙일 것
- `crash_policy` 기반 severity/bucket 해석
- `deep_write_crash` 트리거 평가
- `deep_signal_emergence` 트리거 평가
- profile trigger/action 결과를 `policy_action`에 반영

### 설계 원칙
- 못 계산하는 trigger는 억지로 계산하지 않는다.
- 지원되는 trigger와 미지원 trigger를 명확히 구분한다.
- 기존 하드코딩 policy를 완전히 버리기보다, **profile 결과로 override/upgrade**하는 방식으로 간다.
- 테스트 먼저 작성한다.

---

## 작업 체크리스트

### Phase 1 — 구조 확인
- [x] `crash_policy.buckets`와 현재 sanitizer summary 간 연결 방식 정의
- [x] 어떤 trigger를 지금 계산할 수 있는지 냉정하게 선별
- [x] `policy_action`에 어떤 필드를 추가할지 정의

### Phase 2 — 테스트 먼저 작성
- [x] deep write crash가 `high_priority_alert`로 승격되는 테스트 추가
- [x] deep signal emergence가 trigger 매칭되는 테스트 추가
- [x] parser shallow crash가 과도하게 승격되지 않는 테스트 추가
- [x] snapshot/report로 trigger 결과 전달되는 테스트 추가
- [x] 먼저 테스트를 돌려 실패 확인

### Phase 3 — 구현
- [x] crash summary -> profile label 추론 함수 추가
- [x] `crash_policy` 기반 severity 계산 추가
- [x] 지원되는 trigger evaluator 추가
- [x] matched trigger/action을 기존 policy_action에 병합
- [x] snapshot/report/Discord summary에 trigger 결과 반영

### Phase 4 — 검증
- [x] 신규 테스트만 먼저 실행
- [x] 전체 watcher 테스트 실행
- [x] 실패 시 root cause 확인 후 수정

### Phase 5 — 냉정한 사후 평가
- [x] 지금 지원되는 trigger subset 명시
- [x] 아직 미지원인 trigger 명시
- [x] 다음 단계에서 필요한 telemetry 적기

---

## 성공 기준
- deep write/deep signal이 profile 기반으로 승격된다.
- stage-aware crash severity가 watcher decision에 반영된다.
- 결과가 status/report/Discord summary에 남는다.
- 전체 watcher 테스트가 유지된다.

## 실패 기준
- shallow parser crash까지 과도하게 critical로 승격된다.
- profile trigger를 읽는 척만 하고 실제 decision에 반영되지 않는다.
- 계산 불가능한 trigger를 억지로 처리한다.

## 한 줄 냉정 평가 기준
**이번 단계가 끝나면 watcher는 stage-aware semantic signal을 실제 policy decision에 쓰기 시작하지만, 아직 full trigger engine은 아니다.**
