# R20 Harness Compile/Smoke Revision Intelligence Checklist

**Goal:** R19 skeleton draft를 실제 build/smoke probe evidence와 더 강하게 연결해, 다음 revision이 무엇을 우선 고쳐야 하는지 구조화한다.

---

## 냉정한 사전 평가
- R19까지는 skeleton draft + shallow revision substrate는 생겼다.
- 하지만 아직 revision loop가 실제 compile/smoke outcome을 충분히 구조화해서 소비하진 않는다.
- 지금 필요한 건 full auto-fix가 아니라:
  1. latest probe feedback의 build/smoke result를 skeleton layer가 읽고
  2. revision priority / next revision focus / signals로 구조화하며
  3. markdown/source artifact가 그 신호를 노출하도록 만드는 것이다.

---

## 작업 체크리스트

### Phase 1 — 범위 확정
- [x] 이번 단계는 patch-level auto-fix가 아니라 revision intelligence structuring으로 제한
- [x] 입력원 확정
  - latest probe feedback
  - ranked candidate metadata
  - existing skeleton revision history
- [x] 출력원 확정
  - `revision_signals`
  - `revision_priority`
  - `next_revision_focus`
  - build/smoke-aware revision loop note

### Phase 2 — 테스트 먼저 작성
- [x] build failure 중심 revision intelligence 테스트
- [x] smoke failure 중심 revision intelligence 테스트
- [x] markdown/source emission에 revision intelligence가 드러나는지 테스트
- [x] 먼저 테스트를 돌려 failure 확인

### Phase 3 — 구현
- [x] skeleton draft에 build/smoke-aware revision intelligence 계산 추가
- [x] revision loop가 focus에 따라 더 구체적으로 달라지게 확장
- [x] markdown에 revision intelligence section 추가
- [x] write path가 새 metadata를 manifest에 저장하도록 반영

### Phase 4 — 검증
- [x] R20 관련 타깃 테스트 재실행
- [x] `tests/test_hermes_watch.py` 전체 실행
- [x] `pytest tests -q` 전체 실행
- [x] `py_compile` 검증

### Phase 5 — 사후 평가
- [x] 이번 단계는 still advisory intelligence layer임을 명시
- [x] 다음 단계로 actual skeleton compile/smoke execution closure를 남김

---

## 성공 기준
- skeleton draft가 latest feedback의 build/smoke 결과를 revision intelligence로 구조화한다.
- revision loop가 build-fix / smoke-fix / confidence-raise 류의 우선순위를 드러낸다.
- markdown/manifest에 사람이 바로 읽을 수 있게 표시된다.
- 전체 테스트가 유지된다.

## 한 줄 냉정 평가 기준
**이번 단계가 끝나면 R20 skeleton layer는 단순 draft 생성이 아니라, 실제 build/smoke evidence를 읽고 다음 revision의 초점을 구조화하는 advisory intelligence를 가진다.**
