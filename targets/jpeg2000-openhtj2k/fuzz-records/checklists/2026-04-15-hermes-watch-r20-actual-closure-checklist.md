# R20 Actual Skeleton Compile/Smoke Closure Checklist

**Goal:** latest skeleton artifact를 실제 build/smoke probe와 연결해, revision intelligence가 advisory-only feedback가 아니라 skeleton-specific execution evidence를 읽게 만든다.

---

## 냉정한 사전 평가
- R20 revision intelligence v0.1까지는 skeleton layer가 build/smoke result를 구조화하지만, 그 입력은 주로 latest probe feedback에 의존했다.
- 지금 필요한 건 latest skeleton artifact 자체에 대해 build/smoke closure를 실행하고,
  그 결과를 다음 skeleton revision intelligence가 우선 사용하도록 만드는 것이다.
- 이 단계는 full auto-fix가 아니라 **actual skeleton execution closure**다.

---

## 작업 체크리스트

### Phase 1 — 범위 확정
- [x] skeleton-specific closure manifest/plan 경로 정의
- [x] closure 입력원을 latest skeleton artifact로 고정
- [x] 다음 revision intelligence가 closure evidence를 probe feedback보다 우선 사용하도록 설계

### Phase 2 — 테스트 먼저 작성
- [x] skeleton closure build→smoke 실행 테스트
- [x] skeleton closure evidence 우선 반영 테스트
- [x] CLI `--run-harness-skeleton-closure` 테스트
- [x] 먼저 테스트를 돌려 failure 확인

### Phase 3 — 구현
- [x] `run_harness_skeleton_closure(...)` 추가
- [x] closure markdown/manifest emission 추가
- [x] skeleton draft가 latest closure evidence를 우선 읽도록 확장
- [x] hermes_watch wrapper + CLI 연결
- [x] support package export 반영

### Phase 4 — 검증
- [x] skeleton draft 타깃 테스트 재실행
- [x] `tests/test_hermes_watch.py` 전체 실행
- [x] `pytest tests -q` 전체 실행
- [x] `py_compile` 검증

### Phase 5 — 사후 평가
- [x] actual compile/smoke closure까지는 들어왔지만 patch-level correction은 아직 아님을 명시
- [x] 다음 단계로 lifecycle cleanup과 autonomous correction 후보를 남김

---

## 성공 기준
- latest skeleton artifact 기준 build/smoke probe manifest가 생성된다.
- skeleton revision intelligence가 latest closure evidence를 probe feedback보다 우선 사용한다.
- CLI 경로로도 artifact를 생성할 수 있다.
- 전체 테스트가 유지된다.

## 한 줄 냉정 평가 기준
**이번 단계가 끝나면 R20은 skeleton layer를 실제 build/smoke execution evidence와 닫아, advisory-only revision loop에서 skeleton-specific closure loop로 한 단계 올라간다.**
