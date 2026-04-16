# Hermes Watch Refiner Quality And Lineage Checklist

**Goal:** verification 단계가
- cron prompt lineage
- delegate artifact section quality
까지 보수적으로 확인하도록 확장한다.

**Scope:** 이번 단계는 rule-based shallow verification만 한다.
- cron prompt lineage: prompt file에 expected lineage token 존재 여부 확인
- delegate section quality: required sections 아래 body content 존재 여부 확인

---

## 냉정한 사전 평가

### 현재 상태
- system은 existence와 basic shape verification까지는 된다.
- 하지만 아직 "맞는 lineage에서 나온 prompt인지"와 "section 아래 실제 내용이 있는지"는 안 본다.
- 지금 필요한 건 semantic LLM grading이 아니라, **low-risk rule-based content sanity**다.

### 이번 단계에서 실제로 붙일 것
- `cron_prompt_lineage_visible(...)`
- `delegate_artifact_quality_visible(...)`
- cron verification에 lineage token 체크 추가
- delegate verification에 quality section 체크 추가

### 이번 단계에서 일부러 안 할 것
- LLM 기반 문서 quality scoring
- prompt/body exact equality
- delegate note의 내용 정확성 판단
- subjective quality ranking

### 설계 원칙
- quality와 lineage는 **token/section/body presence** 수준까지만 본다.
- 잘못된 긍정 판정보다 conservative miss가 낫다.
- optional metadata/quality rules가 없으면 기존 verification을 깨지 않는다.

---

## 작업 체크리스트

### Phase 1 — 구조 설계
- [x] cron lineage token 기준 정의
- [x] delegate quality section 기준 정의
- [x] summary naming rule 정의

### Phase 2 — 테스트 먼저 작성
- [x] cron prompt lineage verification 테스트
- [x] delegate artifact quality verification 테스트
- [x] 먼저 테스트를 돌려 failure 확인

### Phase 3 — 구현
- [x] `cron_prompt_lineage_visible(...)` 추가
- [x] `delegate_artifact_quality_visible(...)` 추가
- [x] `verify_cron_entry(...)` 확장
- [x] `verify_delegate_entry(...)` 확장

### Phase 4 — 검증
- [x] verification 테스트 재실행
- [x] launcher + verification 묶음 테스트 실행
- [x] 전체 watcher 테스트 실행

### Phase 5 — 냉정한 사후 평가
- [x] lineage/quality 검증이 shallow rule-based subset임을 명시
- [x] 다음 단계 semantic content checks 필요성 기록

---

## 성공 기준
- cron entry가 expected lineage token을 prompt file에서 확인하면 lineage verified가 기록된다.
- delegate artifact의 quality sections에 실질 content가 있으면 quality verified가 기록된다.
- full test suite가 유지된다.

## 실패 기준
- token 존재만으로 semantic correctness를 과장한다.
- heading만 있고 body가 빈 섹션을 quality pass 시킨다.
- optional quality rules 때문에 기존 verified 흐름을 깨뜨린다.

## 한 줄 냉정 평가 기준
**이번 단계가 끝나면 watcher는 cron prompt lineage와 delegate artifact section body quality까지 보수적으로 검증한다.**
