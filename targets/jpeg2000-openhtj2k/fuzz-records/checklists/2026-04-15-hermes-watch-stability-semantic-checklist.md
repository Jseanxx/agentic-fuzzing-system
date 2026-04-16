# Hermes Watch Stability + Semantic Quality Checklist

**Goal:** `hermes_watch.py`가 history 기반으로 `stability_drop` subset과 semantic quality 신호를 해석하도록 만든다.

**Scope:** 이번 단계는 **repro/duplicate instability 기반 stability_drop + recent deep/shallow semantic quality 요약**까지만 한다.

---

## 냉정한 사전 평가

### 현재 상태
- stage tagging 완료
- single-run semantic policy 완료
- history-aware plateau/dominance/timeout/corpus subset 완료
- 하지만 history가 semantic quality를 충분히 요약하지 못하고, stability도 사실상 미구현이다.

### 현실적인 제한
이번 단계에서도 완전한 stability는 어렵다.
이유:
- 실제 재현 재시도 결과를 watcher가 아직 반복 측정하지 않음
- deterministic instrumentation도 아직 없음

### 이번 단계에서 실제로 붙일 것
- history에서 duplicate crash family 재등장 패턴을 이용한 보수적 `stability_drop` subset
- recent history에서 deep vs shallow crash counts 요약
- policy decision에 semantic quality 요약 반영

### 설계 원칙
- flaky/nondeterministic를 과하게 단정하지 않는다.
- 같은 fingerprint가 짧은 window에 반복되고 shallow dominance도 강할 때만 instability 쪽으로 본다.
- semantic quality는 trigger뿐 아니라 watcher가 사람에게 보여주는 해석 자료로도 중요하다.

---

## 작업 체크리스트

### Phase 1 — 구조 확인
- [x] stability subset에 쓸 보수적 신호 정의
- [x] semantic quality 요약 필드 정의
- [x] 현재 history 데이터로 계산 가능한 범위 확정

### Phase 2 — 테스트 먼저 작성
- [x] stability_drop 감지 테스트 추가
- [x] semantic quality 요약 계산 테스트 추가
- [x] data 부족 시 미발동 테스트 추가
- [x] policy action에 semantic quality 반영 테스트 추가
- [x] 먼저 테스트를 돌려 실패 확인

### Phase 3 — 구현
- [x] history semantic summary 함수 추가
- [x] stability_drop evaluator 추가
- [x] policy decision에 semantic summary 병합
- [x] snapshot/report/summary에 semantic quality 반영

### Phase 4 — 검증
- [x] 신규 테스트 실행
- [x] 전체 watcher 테스트 실행
- [x] 실패 시 root cause 확인 후 수정

### Phase 5 — 냉정한 사후 평가
- [x] 지원되는 stability subset 명시
- [x] 아직 미지원인 deterministic telemetry 명시
- [x] 다음 단계 요구사항 적기

---

## 성공 기준
- watcher가 recent deep/shallow quality를 요약할 수 있다.
- 보수적 stability_drop subset이 동작한다.
- 전체 테스트가 유지된다.

## 실패 기준
- duplicate가 조금만 있어도 instability로 과잉 반응한다.
- semantic quality를 단순 deep count만으로 과장한다.
- missing data를 억지로 해석한다.

## 한 줄 냉정 평가 기준
**이번 단계가 끝나면 watcher는 단순 트리거 모음이 아니라 recent semantic quality를 읽고 설명할 수 있는 운영 평가기 성격이 더 강해진다.**
