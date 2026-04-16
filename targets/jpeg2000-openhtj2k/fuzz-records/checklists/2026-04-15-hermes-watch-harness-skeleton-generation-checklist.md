# Hermes Watch Harness Skeleton Generation + Revision Loop Checklist

**Goal:** R19에서 probe/evaluation/candidate registry 위에 low-risk harness skeleton draft와 revision loop를 붙인다.

---

## 냉정한 사전 평가
- R18까지는 candidate ranking / probe / feedback / refiner handoff는 이어졌지만, 실제 harness code skeleton artifact는 없었다.
- 지금 필요한 건 바로 컴파일 강행이 아니라, **selected candidate 기준 draft skeleton source + revision note**를 보수적으로 만드는 단계다.
- revision loop는 build/smoke review feedback을 다음 skeleton revision에 연결하는 shallow artifact loop 수준이면 충분하다.

---

## 작업 체크리스트

### Phase 1 — 구조 설계
- [x] skeleton draft 입력원 정의 (evaluation + ranked candidate registry + latest feedback)
- [x] revision trigger 정의 (existing skeleton + review/reseed feedback)
- [x] source/manifest/markdown artifact schema 정의

### Phase 2 — 테스트 먼저 작성
- [x] initial skeleton draft 생성 테스트
- [x] review feedback 기반 revision 전환 테스트
- [x] manifest/markdown/source emission 테스트
- [x] CLI `--draft-harness-skeleton` 테스트
- [x] 먼저 테스트를 돌려 failure 확인

### Phase 3 — 구현
- [x] `scripts/hermes_watch_support/harness_skeleton.py` 추가
- [x] `build_harness_skeleton_draft(...)` 추가
- [x] `write_harness_skeleton_draft(...)` 추가
- [x] hermes_watch wrapper + CLI 연결
- [x] support package export 반영

### Phase 4 — 검증
- [x] skeleton draft 타깃 테스트 재실행
- [x] `py_compile` 검증
- [x] `tests/test_hermes_watch.py` 전체 실행
- [x] `pytest tests -q` 전체 실행

### Phase 5 — 사후 평가
- [x] 이 단계는 draft skeleton artifact와 shallow revision loop까지만 제공함을 명시
- [x] 다음 단계에서 build/smoke result를 skeleton revision scoring에 더 강하게 닫아야 함을 기록

---

## 성공 기준
- selected candidate 기준 harness skeleton source artifact가 생성된다.
- review feedback가 있을 때 draft가 revision으로 전환되고 revision 번호가 증가한다.
- revision loop markdown이 smoke/build review 포인트를 명시한다.
- 전체 테스트가 유지된다.

## 한 줄 냉정 평가 기준
**이번 단계가 끝나면 watcher는 selected candidate에 대해 low-risk harness skeleton source를 뽑고, review feedback를 다음 skeleton revision artifact로 되먹이는 얕은 revision loop를 가진다.**
