# Note — multi-target adapter generalization v0.2 editable-region policy seam slice

- Date: 2026-04-16 07:24:55 KST
- Scope: `scripts/hermes_watch.py`, `scripts/hermes_watch_support/target_adapter.py`, `scripts/hermes_watch_support/profile_summary.py`, `tests/test_hermes_watch.py`

## 이번 단계에서 한 일
- target adapter에 editable-region policy 관련 필드를 추가했다.
  - `editable_harness_relpath`
  - `fuzz_entrypoint_names`
- profile summary가 이 adapter policy 필드들도 함께 보존하도록 확장했다.
- apply safety 계층이 이제 runtime target adapter를 읽어:
  - editable harness root directory
  - fuzz entrypoint name
  를 policy source로 사용한다.
- 그 결과 `_diff_safety_guardrails(...)`, `_find_fuzzer_entrypoint_region(...)`, `_guard_only_line_allowed(...)`가 더 이상 `fuzz-records/harness-skeletons` + `LLVMFuzzerTestOneInput`에 완전히 고정되지 않는다.

## 왜 가치가 있나
이전 단계까지는 multi-target adapter가 build/smoke/fuzz command 쪽으로는 퍼졌지만,
mutation safety rail은 여전히 거의 OpenHTJ2K/LLVMFuzzer shaped 가정에 묶여 있었다.
즉 command만 generalize되고,
어디를 수정 가능한 generated harness로 볼지 / 어떤 fuzz entrypoint를 보호할지 는 여전히 하드코딩이었다.

이번 단계로 최소한 다음은 가능해졌다.
1. custom target이 별도 generated harness 디렉터리를 써도 editable root policy가 adapter를 통해 전달된다.
2. custom fuzz entrypoint 이름을 쓰는 target도 guard-only touched-region safety를 policy로 해석할 수 있다.
3. multi-target 일반화가 command seam에서 mutation-safety seam 쪽으로 한 단계 더 이동했다.

## 아직 남은 점
- `_inject_guarded_patch(...)` 자체는 여전히 LLVMFuzzer-shaped 기본 rail에 가깝다.
- 즉, 이번 단계는 **editable-region policy seam**이지 완전한 target-specific mutation generation seam은 아니다.
- regression smoke matrix도 아직 없다.
- draft/evaluation/revision 쪽의 추가 target leakage도 더 걷어내야 한다.

## 검증
- targeted tests
  - custom adapter policy field unit test
  - custom editable harness dir + custom fuzz entrypoint를 쓰는 guarded apply 경로 test
- broader regression
  - `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/target_adapter.py scripts/hermes_watch_support/profile_summary.py tests/test_hermes_watch.py`
  - `python -m pytest tests/test_hermes_watch.py::HermesWatchTargetAdapterTests tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests -q`
  - `python -m pytest tests/test_hermes_watch.py -q`
  - `python -m pytest tests -q`

## 냉정한 평가
이 단계는 화려하지 않다.
하지만 multi-target substrate를 진짜로 만들려면 이런 seam이 더 중요하다.
command만 분리되고 mutation safety가 특정 target 이름/디렉터리에 묶여 있으면,
결국 일반화는 겉보기만 좋아진다.

그래서 이번 단계는 규모는 작지만 구조적으로는 꽤 의미 있다.
다만 아직 mutation generation 자체가 target-aware해진 건 아니므로,
과장 없이 말하면 **policy seam만 한 단계 분리한 것**이다.
