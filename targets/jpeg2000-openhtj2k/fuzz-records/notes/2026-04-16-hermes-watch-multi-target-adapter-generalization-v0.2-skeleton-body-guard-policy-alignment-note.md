# 2026-04-16 — hermes_watch multi-target adapter generalization v0.2 skeleton body guard-policy alignment note

## 한 줄 요약
harness skeleton source draft의 body가 더 이상 고정 `hermes_prepare_input(...) -> return 0` 패턴만 쓰지 않고, runtime target adapter의 `guard_condition`, `guard_return_statement`를 읽어 source body의 초기 guard까지 실제 반영하기 시작했다.

## 왜 이 slice가 필요했나
직전 단계에서 skeleton source draft의 entrypoint 이름은 adapter-aware해졌지만, body는 여전히 generic했다.

남아 있던 leakage:
- C skeleton의 `hermes_prepare_input(...) != 0 -> return 0;`
- C++ skeleton의 `!hermes_prepare_input(...) -> return 0;`
- custom adapter가 이미 가진 `guard_condition`, `guard_return_statement`와 source draft body가 분리됨

즉 apply/runtime 쪽의 guard policy contract는 adapter-aware한데, skeleton source draft body는 아직 그 계약을 반영하지 못하고 있었다.

## 이번에 바꾼 것
1. `_skeleton_guard_contract(repo_root)` 추가
   - runtime target adapter에서
     - `guard_condition`
     - `guard_return_statement`
   를 skeleton layer에서도 읽을 수 있게 함

2. `_render_skeleton_code(...)` 확장
   - `guard_condition`
   - `guard_return_statement`
   를 받아 source body의 초기 guard에 직접 반영

3. generic prepare helper 제거
   - C / C++ skeleton source draft에서 `hermes_prepare_input(...)` helper를 제거
   - 대신 source body에
     - null-pointer check
     - adapter-driven guard condition
     - adapter-driven early return
   를 직접 배치

4. skeleton artifact metadata 확장
   - `skeleton_guard_condition`
   - `skeleton_guard_return_statement`
   를 draft payload/markdown에 기록

## 테스트 / 검증
### RED
먼저 failing test를 추가했다.
- `test_build_harness_skeleton_draft_uses_profile_selected_guard_policy_in_body`
- `test_write_harness_skeleton_draft_emits_custom_guard_policy_into_source`

초기 실패:
- skeleton source/body가 여전히 `hermes_prepare_input(...)`와 `return 0;` 패턴을 사용
- custom profile adapter의 `size <= 8`, `return -1;`는 source draft에 반영되지 않음

### GREEN
검증 결과:
- `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/harness_skeleton.py scripts/hermes_watch_support/target_adapter.py scripts/hermes_watch_support/profile_summary.py tests/test_hermes_watch.py` → OK
- `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests -q` → 70 passed
- `python -m pytest tests/test_hermes_watch.py -q` → 234 passed
- `python -m pytest tests -q` → 253 passed

## 의미
이번 단계로 multi-target adapter seam이 이제:
- entrypoint naming
- guard policy contract
을 넘어서
- **skeleton source body의 초기 safety gate**
까지 퍼졌다.

즉 source draft artifact가 이제 visible ABI 이름뿐 아니라 최소 body guard semantics에서도 adapter contract를 일부 소비하기 시작했다.

## 냉정한 한계
여전히 과장 금지다.
- 이건 target ABI / real parser contract를 이해한 body synthesis가 아니다
- `guard_condition`, `guard_return_statement`를 source body에 끼워 넣는 수준이다
- TODO wiring guidance, target call shape, ownership/lifetime/resource semantics는 아직 generic하다

## 한 줄 냉정평
이 단계는 **skeleton body의 가장 얕은 초기 guard를 adapter contract에 맞춘 것**이다.
의미 있는 정리지만, 아직 target-aware harness body synthesis와는 거리가 멀다.
