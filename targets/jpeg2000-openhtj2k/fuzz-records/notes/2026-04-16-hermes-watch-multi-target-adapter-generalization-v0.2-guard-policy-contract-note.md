# 2026-04-16 — hermes_watch multi-target adapter generalization v0.2 guard policy contract note

## 한 줄 요약
이제 runtime target adapter가 `fuzz_entrypoint_names`뿐 아니라 `guard_condition`, `guard_return_statement`까지 들고 다니며, guarded mutation generation과 diff whitelist가 그 계약을 실제 소비하기 시작했다.

## 왜 이 slice가 필요했나
직전 단계에서 mutation insertion point는 adapter-aware해졌지만, 실제 guard 내용은 여전히 하드코딩이었다.

남아 있던 single-target shaped leakage:
- `if (size < 4)`
- `return 0;`
- whitelist도 이 두 줄에 강하게 묶임

즉 entrypoint 이름만 일반화됐을 뿐, guard policy 자체는 아직 OpenHTJ2K-shaped였다.

## 이번에 바꾼 것
1. target adapter policy 확장
   - `guard_condition`
   - `guard_return_statement`

2. profile summary 보존 확장
   - target profile의 adapter spec summary가 위 필드도 유지

3. `_build_guard_only_patch_plan(...)`가 adapter-aware guard body 생성
   - custom condition
   - custom early return statement
   를 patch generation에 반영

4. `_inject_guarded_patch(...)` 확장
   - `guard_condition`
   - `guard_return_statement`
   를 받아 실제 injected guard lines를 adapter contract에 맞춰 생성

5. `_guard_only_line_allowed(...)` / `_diff_safety_guardrails(...)` 확장
   - guard whitelist도 custom condition / custom return statement를 허용하도록 변경
   - 즉 generation과 safety가 같은 adapter policy를 보게 됨

6. `apply_verified_harness_patch_candidate(...)` runtime wiring
   - runtime target adapter의
     - `fuzz_entrypoint_names`
     - `guard_condition`
     - `guard_return_statement`
   를 apply path에 실제 전달
   - 기존 monkeypatch lambda tests를 깨지 않도록 backward-compatible fallback 유지

7. regression smoke matrix metadata 확장
   - matrix artifact에도
     - `guard_condition`
     - `guard_return_statement`
   를 기록

## 테스트 / 검증
### RED
먼저 다음 failing test를 추가/확장했다.
- custom adapter fields가 `guard_condition`, `guard_return_statement`까지 읽히는지
- `_inject_guarded_patch(...)`가 custom guard policy를 직접 반영하는지
- regression smoke matrix가 custom guard policy metadata를 보존하는지
- runtime profile이 guarded apply E2E path에서 custom guard policy를 실제 적용하는지

초기 실패:
- `TargetAdapter`에 해당 필드가 없어서 `AttributeError`
- `_inject_guarded_patch(..., guard_condition=..., guard_return_statement=...)`가 `TypeError`
- matrix payload에 관련 key가 없음
- apply 결과가 여전히 `size < 4` / `return 0;`를 사용

### GREEN
검증 결과:
- `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/target_adapter.py scripts/hermes_watch_support/profile_summary.py tests/test_hermes_watch.py` → OK
- `python -m pytest tests/test_hermes_watch.py::HermesWatchTargetAdapterTests tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests -q` → 77 passed
- `python -m pytest tests/test_hermes_watch.py -q` → 230 passed
- `python -m pytest tests -q` → 249 passed

## 의미
이번 단계로 adapter seam이 이제:
- command
- editable region safety policy
- mutation insertion point
를 넘어서
- **guard condition / early return contract**
까지 먹기 시작했다.

즉 multi-target substrate가 이제 단순 “어느 함수에 넣을까”가 아니라 “어떤 형태의 최소 guard를 넣을까”의 아주 얕은 정책층까지 확장됐다.

## 냉정한 한계
여전히 과장 금지다.
- 이건 AST/CFG 수준 guard synthesis가 아니다
- `guard_condition`, `guard_return_statement`는 아직 profile-provided string contract일 뿐이다
- meaning-preserving patch generation을 스스로 추론하는 수준은 아니다
- policy contract는 넓어졌지만 intelligence는 여전히 얕다

## 한 줄 냉정평
이 단계는 **guard body의 하드코딩을 adapter contract로 이동한 것**이다.
구조적으로는 중요하지만, 아직 target-aware patch reasoning이라고 부르기엔 이르다.
