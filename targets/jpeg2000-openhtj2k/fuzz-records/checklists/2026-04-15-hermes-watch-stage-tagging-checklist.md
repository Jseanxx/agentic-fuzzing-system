# Hermes Watch Stage Tagging Checklist

**Goal:** `hermes_watch.py`가 target profile을 읽어 crash stack/location을 `stage`와 `deep/shallow`로 태깅하도록 구현한다.

**Scope:** 이번 단계는 **profile-driven stage tagging + deep/shallow classification**까지만 한다. trigger execution 전체를 profile-driven으로 바꾸는 것은 다음 단계다.

---

## 냉정한 사전 평가

### 현재 상태
- target profile YAML 로딩은 이미 붙었다.
- 하지만 watcher는 아직 profile을 **읽기만 하고 실제 해석에 쓰지 않는다.**
- 따라서 지금 상태는 config ingestion이지 semantic telemetry는 아니다.

### 이번 단계의 핵심 리스크
1. `coding_units.cpp`처럼 **같은 파일이 여러 stage와 연결**되는 구간이 있다.
2. stack에 함수명이 항상 선명하게 찍힌다는 보장이 없다.
3. file-only 매칭은 오탐 가능성이 있다.
4. 억지로 하나를 고르는 것보다 **confidence/근거를 남기는 편이 안전**하다.

### 이번 단계의 설계 원칙
- 함수명 매칭 > signal substring 매칭 > 파일 경로 매칭 순으로 신뢰한다.
- ambiguous한 경우 억지로 과신하지 않는다.
- 결과에는 `stage`, `stage_class`, `depth_rank`, `confidence`, `reason`을 남긴다.
- TDD로 간다. 구현 전에 failing test를 만든다.

---

## 작업 체크리스트

### Phase 1 — 입력 구조 확인
- [x] target profile의 `telemetry.stack_tagging.stage_file_map` 확인
- [x] `hotspots.functions` / `stages.expected_signals`를 stage tagging에 활용 가능한지 확인
- [x] watcher의 crash_info 구조에서 어떤 필드를 확장해야 하는지 확인

### Phase 2 — 테스트 먼저 작성
- [x] 함수명 기반 stage 매칭 테스트 추가
- [x] file path 기반 fallback stage 매칭 테스트 추가
- [x] ambiguous/unknown 상황 테스트 추가
- [x] deep/shallow 판정 테스트 추가
- [x] snapshot에 stage 정보 포함 테스트 추가
- [x] 먼저 테스트를 돌려 실패를 확인

### Phase 3 — 구현
- [x] stack frame 파서 추가
- [x] profile에서 stage tagging용 lookup 구성 함수 추가
- [x] crash lines + summary/location 기반 stage resolver 추가
- [x] confidence / reason 계산 추가
- [x] crash_info에 stage metadata 병합
- [x] snapshot / report / Discord summary에 stage 정보 반영

### Phase 4 — 검증
- [x] 신규 테스트만 먼저 실행
- [x] 전체 `tests/test_hermes_watch.py` 실행
- [x] 실패 시 root cause 먼저 분석 후 수정

### Phase 5 — 냉정한 사후 평가
- [x] 지금 구현이 어디까지 자동화됐는지 명확히 구분
- [x] 오탐 가능성이 큰 부분을 적는다
- [x] 다음 단계(실제 trigger evaluation)로 넘길 준비 상태를 평가한다

---

## 성공 기준
- watcher가 crash stack/location에서 `stage`를 태깅한다.
- watcher가 `deep`/`shallow`를 산출한다.
- 결과가 `status.json`, `FUZZING_REPORT.md`, Discord summary에 반영된다.
- 테스트가 재현 가능하게 통과한다.

## 실패 기준
- file-only 매칭으로 무리하게 잘못 분류한다.
- confidence 없이 단정한다.
- 테스트 없이 구현을 밀어넣는다.
- 기존 watcher 회귀를 일으킨다.

## 한 줄 냉정 평가 기준
**이번 단계가 끝나도 trigger engine이 완성되는 건 아니다. 하지만 semantic tagging의 첫 실사용 단계는 된다.**
