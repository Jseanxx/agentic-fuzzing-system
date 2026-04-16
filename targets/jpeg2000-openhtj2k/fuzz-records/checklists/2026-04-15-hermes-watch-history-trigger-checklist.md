# Hermes Watch History-Aware Trigger Checklist

**Goal:** `hermes_watch.py`가 single-run 판단을 넘어서 recent run history를 저장하고, 지금 계산 가능한 multi-run trigger subset을 평가하도록 만든다.

**Scope:** 이번 단계는 **history snapshot 저장 + shallow_crash_dominance + coverage_plateau의 보수적 subset 평가**까지만 한다.

---

## 냉정한 사전 평가

### 현재 상태
- target profile 로딩 완료
- stage tagging 완료
- single-run semantic policy override 완료
- 하지만 recent runs의 누적 분포/정체 상태를 watcher가 아직 기억하지 못한다.

### 현실적인 제한
이번 단계에서도 아래는 여전히 어렵다.
- `timeout_surge`
- `corpus_bloat_low_gain`
- `stability_drop`

이유:
- per-run history는 저장 가능하지만 timeout ratio / corpus gain / stability trend를 충분히 안정적으로 계산하려면 추가 telemetry 설계가 더 필요하다.

### 이번 단계에서 실제로 붙일 것
- run completion 시 history registry 기록
- recent crash stage 분포 계산
- `shallow_crash_dominance`의 history-based subset 평가
- `coverage_plateau`의 보수적 subset 평가

### 설계 원칙
- history는 `automation/` 아래 JSON registry로 남긴다.
- 진행 중 snapshot이 아니라 **run 완료 결과** 기준으로 history를 쌓는다.
- plateau는 coverage/history 데이터가 부족하면 발동시키지 않는다.
- dominance는 최근 crash runs 표본 수가 부족하면 발동시키지 않는다.
- trigger는 “대충 맞는 것”보다 “발동이 드문 대신 신뢰도 높은 것”으로 간다.

---

## 작업 체크리스트

### Phase 1 — 구조 확인
- [x] history registry 경로와 스키마 정의
- [x] recent window 계산 규칙 정의
- [x] 지금 계산 가능한 trigger subset 확정

### Phase 2 — 테스트 먼저 작성
- [x] run history append 테스트 추가
- [x] shallow_crash_dominance trigger 테스트 추가
- [x] coverage_plateau trigger 테스트 추가
- [x] 표본 부족 시 trigger 미발동 테스트 추가
- [x] 먼저 테스트를 돌려 실패 확인

### Phase 3 — 구현
- [x] history registry load/save 함수 추가
- [x] final snapshot 기반 history append 구현
- [x] recent history 분석 함수 추가
- [x] supported history-based trigger evaluator 추가
- [x] matched history trigger를 policy_action에 병합

### Phase 4 — 검증
- [x] 신규 테스트 실행
- [x] 전체 watcher 테스트 실행
- [x] 실패 시 root cause 확인 후 수정

### Phase 5 — 냉정한 사후 평가
- [x] 지원되는 history trigger 명시
- [x] 아직 미지원인 history trigger 명시
- [x] 다음 단계 telemetry 요구사항 적기

---

## 성공 기준
- watcher가 completed run 결과를 history에 저장한다.
- recent stage 분포를 보고 shallow dominance를 판정할 수 있다.
- recent coverage stagnation을 보수적으로 plateau로 판정할 수 있다.
- 전체 watcher 테스트가 유지된다.

## 실패 기준
- 표본이 적은데도 trigger가 남발된다.
- 진행 중 상태와 완료 상태가 섞여 history가 오염된다.
- coverage plateau를 raw cov 하나만 보고 성급히 발동시킨다.

## 한 줄 냉정 평가 기준
**이번 단계가 끝나면 watcher는 드디어 single-run 도우미를 넘어서 recent-run memory를 가진 보수적 refiner 초입이 된다.**
