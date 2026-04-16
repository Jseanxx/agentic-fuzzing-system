# R20 Patch-Level Autonomous Correction Checklist

**Goal:** latest closure/revision intelligence를 바탕으로 skeleton source에 대한 conservative correction draft를 생성해, 다음 단계의 자동 수정 후보를 구조화한다.

---

## 냉정한 사전 평가
- R20 actual closure v0.1까지는 skeleton artifact가 실제 build/smoke evidence와 닫혔다.
- 하지만 아직 failed closure를 보고도 system은 “무엇을 어떻게 고칠지”를 patch-level로 제안하지 못한다.
- 이번 단계의 목적은 실제 소스 자동수정이 아니라:
  1. focus(build-fix / smoke-fix / smoke-enable / confidence-raise)에 따라
  2. skeleton source에 대한 conservative correction draft를 만들고
  3. 사람이 검토하거나 다음 automation이 소비할 수 있게 artifact로 저장하는 것이다.

---

## 작업 체크리스트

### Phase 1 — 범위 확정
- [x] correction draft는 advisory artifact로 제한
- [x] latest revision intelligence / closure evidence를 기반으로 suggestion 생성
- [x] source patch가 아니라 structured suggestion + draft artifact 저장

### Phase 2 — 테스트 먼저 작성
- [x] build-fix correction suggestion 테스트
- [x] correction draft artifact emission 테스트
- [x] markdown에 patch suggestion section 노출 테스트
- [x] 먼저 테스트를 돌려 failure 확인

### Phase 3 — 구현
- [x] correction suggestion builder 추가
- [x] write path에서 correction draft json/md 저장
- [x] manifest에 correction draft metadata 연결
- [x] existing skeleton draft CLI가 correction draft까지 같이 내보내도록 유지

### Phase 4 — 검증
- [x] skeleton draft 타깃 테스트 재실행
- [x] `tests/test_hermes_watch.py` 전체 실행
- [x] `pytest tests -q` 전체 실행
- [x] `py_compile` 검증

### Phase 5 — 사후 평가
- [x] actual code mutation은 아직 안 했음을 명시
- [x] 다음 단계로 correction draft 소비/승격 규칙을 남김

---

## 성공 기준
- failed build/smoke focus에 따라 patch-level correction suggestion이 생성된다.
- correction draft json/md artifact가 저장된다.
- skeleton manifest/markdown에서 correction draft를 추적할 수 있다.
- 전체 테스트가 유지된다.

## 한 줄 냉정 평가 기준
**이번 단계가 끝나면 system은 failed closure를 보고 “다음에 뭘 고칠지”를 source-adjacent correction draft로 남기는 conservative autonomous correction substrate를 갖는다.**
