# 2026-04-16 — hermes_watch multi-target adapter generalization v0.2 skeleton call-contract generalization note

## 한 줄 요약
harness skeleton source draft가 더 이상 generic `TODO: wire ...` 한 줄에만 머무르지 않고, runtime target adapter의 `target_call_todo`, `resource_lifetime_hint`를 읽어 target call shape와 lifetime guidance를 source artifact와 markdown metadata에 실제 반영하기 시작했다.

## 왜 이 slice가 필요했나
직전 단계에서 skeleton source draft는:
- entrypoint name
- initial guard condition
- early return policy
까지는 adapter-aware해졌지만,

실제 target wiring guidance는 여전히 generic했다.
남아 있던 leakage:
- `TODO: wire <entry_symbol_hint> from <entrypoint_path> (...)`
- resource lifetime / ownership guidance 부재
- correction/markdown/source artifact에서 target call shape가 거의 보이지 않음

즉 source body의 입구는 adapter-aware해졌는데, 실제 “무엇을 어떻게 연결할지”에 대한 가이드는 아직 generic placeholder 수준이었다.

## 이번에 바꾼 것
1. target adapter contract 확장
   - `target_call_todo`
   - `resource_lifetime_hint`

2. profile summary / regression matrix 확장
   - 위 두 필드도 adapter summary와 matrix artifact에 남기도록 확장

3. skeleton layer에 `_skeleton_call_contract(repo_root)` 추가
   - runtime adapter에서 call-shape TODO와 lifetime hint를 읽어옴

4. `_render_skeleton_code(...)` 확장
   - source draft의 TODO comment를 generic wire 문구 대신 adapter-driven `target_call_todo`로 치환
   - 별도 `Lifetime hint:` comment를 추가
   - 기존 entrypoint_path/mode 기반 binding hint는 보조 문구로 유지

5. draft payload / markdown metadata 확장
   - `skeleton_target_call_todo`
   - `skeleton_resource_lifetime_hint`
   를 artifact metadata로 남김

## 테스트 / 검증
### RED
먼저 다음 failing test를 추가했다.
- `test_build_harness_skeleton_draft_uses_profile_selected_call_todo_and_lifetime_hint`
- `test_write_harness_skeleton_draft_emits_custom_call_todo_and_lifetime_hint`

초기 실패:
- draft payload에 관련 metadata key가 없음
- source draft가 여전히 generic `TODO: wire ...` 문구를 사용
- lifetime hint가 source/markdown에 없음

### GREEN
검증 결과:
- `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/harness_skeleton.py scripts/hermes_watch_support/target_adapter.py scripts/hermes_watch_support/profile_summary.py tests/test_hermes_watch.py` → OK
- `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests -q` → 72 passed
- `python -m pytest tests/test_hermes_watch.py -q` → 236 passed
- `python -m pytest tests -q` → 255 passed

## 의미
이번 단계로 multi-target adapter seam이 이제:
- entrypoint naming
- initial guard policy
를 넘어서
- **target call TODO / resource-lifetime guidance**
까지 source artifact에 들어오기 시작했다.

즉 skeleton source draft가 단순 placeholder를 넘어서, 최소한 “어떤 호출을 연결하려는지 / 수명 가정이 무엇인지”를 artifact로 남기게 됐다.

## 냉정한 한계
여전히 과장 금지다.
- 이건 실제 target ABI 분석이나 ownership inference가 아니다
- adapter/profile이 준 string contract를 source/markdown에 반영하는 수준이다
- deeper semantics, cleanup ordering, partial object lifecycle, error-handling contract는 아직 generic하다

## 한 줄 냉정평
이 단계는 **generic wiring placeholder를 adapter-driven call contract comment로 치환한 것**이다.
좋은 진전이지만, 아직 real target-aware harness body synthesis와는 거리가 있다.
