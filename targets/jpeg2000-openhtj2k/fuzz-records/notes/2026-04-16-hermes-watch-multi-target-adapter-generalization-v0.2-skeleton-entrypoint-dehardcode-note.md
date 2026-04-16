# 2026-04-16 — hermes_watch multi-target adapter generalization v0.2 skeleton entrypoint de-hardcode note

## 한 줄 요약
harness skeleton source draft가 더 이상 무조건 `LLVMFuzzerTestOneInput`를 찍지 않고, runtime target adapter의 `fuzz_entrypoint_names`를 읽어 skeleton entrypoint 이름을 실제 반영하기 시작했다.

## 왜 이 slice가 필요했나
이전까지 multi-target adapter seam은:
- main runtime command
- probe / closure command
- editable-region safety policy
- mutation insertion point
- guard policy contract
까지 확장됐지만,

`scripts/hermes_watch_support/harness_skeleton.py`의 source draft는 여전히:
- C skeleton: `int LLVMFuzzerTestOneInput(...)`
- C++ skeleton: `extern "C" int LLVMFuzzerTestOneInput(...)`
으로 하드코딩되어 있었다.

즉 apply/runtime 쪽은 adapter-aware해지는데, 가장 눈에 띄는 skeleton source draft는 아직 single-target shaped 상태였다.

## 이번에 바꾼 것
1. `harness_skeleton.py`에 runtime adapter resolve helper 추가
   - profile loading / summary / adapter resolution을 skeleton layer에서도 직접 사용할 수 있게 함

2. `_skeleton_entrypoint_name(repo_root)` 추가
   - runtime adapter의 `fuzz_entrypoint_names` 첫 값을 skeleton draft의 target entrypoint 이름으로 사용
   - 없으면 fallback으로 `LLVMFuzzerTestOneInput`

3. `_render_skeleton_code(...)` 확장
   - `skeleton_entrypoint_name` parameter를 받아
   - C / C++ skeleton source draft에 custom entrypoint 이름을 실제 반영

4. `build_harness_skeleton_draft(...)` metadata 확장
   - `skeleton_entrypoint_name`를 draft payload에 기록
   - markdown도 이 값을 함께 보여 줌

5. `write_harness_skeleton_draft(...)` 경로 검증
   - 실제 source artifact가 custom entrypoint 이름을 포함하는지 regression test로 확인

## 테스트 / 검증
### RED
먼저 다음 failing test를 추가했다.
- `test_build_harness_skeleton_draft_uses_profile_selected_adapter_entrypoint_name`
- `test_write_harness_skeleton_draft_emits_custom_adapter_entrypoint_name_into_source`

초기 실패:
- skeleton_code / source file가 여전히 `LLVMFuzzerTestOneInput`를 포함
- custom profile adapter의 `CustomFuzzEntry`는 반영되지 않음

### GREEN
검증 결과:
- `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/harness_skeleton.py scripts/hermes_watch_support/target_adapter.py scripts/hermes_watch_support/profile_summary.py tests/test_hermes_watch.py` → OK
- `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests -q` → 68 passed
- `python -m pytest tests/test_hermes_watch.py -q` → 232 passed
- `python -m pytest tests -q` → 251 passed

## 의미
이번 단계로 multi-target adapter seam이 이제:
- runtime command
- safety policy
- mutation generation
뿐 아니라
- **source draft artifact의 visible entrypoint naming**
까지 퍼졌다.

즉 사람과 다음 automation layer가 보는 skeleton artifact 자체가 조금 더 target-aware해졌다.

## 냉정한 한계
여전히 과장하면 안 된다.
- skeleton draft의 함수 body/prepare logic/TODO wiring guidance는 아직 generic하다
- `fuzz_entrypoint_names[0]`를 가져다 쓰는 정도이지, 실제 target ABI나 harness contract를 깊게 이해하는 건 아니다
- entrypoint 이름 leakage 하나를 줄였을 뿐, skeleton semantics 전반이 multi-target화된 건 아니다

## 한 줄 냉정평
이 단계는 **가장 눈에 띄는 source draft hardcoding 하나를 제거한 것**이다.
작지만 의미 있는 정리이고, 아직 skeleton semantics generalization과는 거리가 있다.
