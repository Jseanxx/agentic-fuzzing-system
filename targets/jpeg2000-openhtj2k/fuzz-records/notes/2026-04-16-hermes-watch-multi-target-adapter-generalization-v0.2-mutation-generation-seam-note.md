# 2026-04-16 — hermes_watch multi-target adapter generalization v0.2 mutation generation seam note

## 한 줄 요약
`guard-only` patch generation이 더 이상 `LLVMFuzzerTestOneInput` 하드코딩에만 의존하지 않고, runtime target adapter의 `fuzz_entrypoint_names` policy를 실제 소비하도록 확장했다.

## 왜 이 slice가 필요했나
이전 단계까지 adapter seam은:
- main runtime command
- probe / closure command
- editable-region safety policy
- regression inspection artifact
까지는 퍼졌지만,

정작 실제 mutation generation 쪽 `_inject_guarded_patch(...)`는 여전히:
- `LLVMFuzzerTestOneInput`
- `size < 4`
- 제한된 문자열 치환
중심이었다.

즉 safety policy는 multi-target처럼 보이는데, mutation generation은 single-target shaped 상태가 남아 있었다.

## 이번에 바꾼 것
1. `_build_guard_only_patch_plan(...)` helper 추가
   - guard-only patch generation을 apply path에서 분리해 review 가능한 작은 planning seam으로 분리
   - entrypoint 이름과 C / C++ signature shape를 기준으로 삽입 계획을 만든다

2. `_inject_guarded_patch(...)` 확장
   - `entrypoint_names`를 받아 custom fuzz entrypoint에도 guard patch를 삽입할 수 있게 함
   - `CustomFuzzEntry(...)` 같은 custom C signature
   - `extern "C" int CustomFuzzEntry(const std::uint8_t* data, std::size_t size)` 같은 custom C++ signature
   를 모두 처리

3. `apply_verified_harness_patch_candidate(...)`가 runtime adapter policy를 실제 소비
   - `_resolve_runtime_target_adapter(repo_root)`로 adapter를 읽고
   - 그 `fuzz_entrypoint_names`를 `_inject_guarded_patch(...)`로 전달
   - 즉 이제 guarded apply path의 mutation generation도 runtime adapter contract를 실제 따른다

4. 기존 monkeypatch 기반 tests와의 호환성 유지
   - 기존 테스트들이 `_inject_guarded_patch = lambda ...` 방식으로 patch generation을 대체하던 부분이 깨지지 않도록 fallback을 유지

## 테스트 / 검증
### RED
다음 새 테스트를 먼저 추가하고 실패를 확인했다.
- `test_inject_guarded_patch_uses_custom_entrypoint_name`
- `test_inject_guarded_patch_uses_custom_cpp_entrypoint_name`
- `test_apply_verified_harness_patch_candidate_uses_custom_editable_region_policy_from_profile`

초기 실패 형태:
- `_inject_guarded_patch(..., entrypoint_names=...)`에서 `TypeError`
- custom adapter profile이 있어도 실제 apply path는 guard를 함수 내부에 넣지 못하고 파일 끝에 comment만 append

### GREEN
검증 결과:
- `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/target_adapter.py scripts/hermes_watch_support/profile_summary.py tests/test_hermes_watch.py` → OK
- `python -m pytest tests/test_hermes_watch.py::HermesWatchTargetAdapterTests tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests -q` → 76 passed
- `python -m pytest tests/test_hermes_watch.py -q` → 229 passed
- `python -m pytest tests -q` → 248 passed

## 의미
이번 단계로 adapter seam이:
- command selection
- safety policy
를 넘어
- **guarded mutation generation**
까지 한 칸 더 퍼졌다.

즉 multi-target 이야기가 inspection layer나 allow/deny policy에만 머무르지 않고, 실제 patch insertion point 선택에도 조금 들어오기 시작했다.

## 냉정한 한계
여전히 과장하면 안 된다.
- `_inject_guarded_patch(...)`는 아직 heuristic string-based mutation generator다
- `size < 4` / `return 0` 형태의 단순 guard 패턴을 넘는 target-aware synthesis는 아니다
- editable region과 entrypoint 선택은 target-aware해졌지만, guard condition 자체의 의미 선택은 여전히 얕다

## 한 줄 냉정평
이건 **mutation generation seam의 입구를 연 단계**다.
좋은 진전이지만, 아직 “target-aware patch synthesis”라고 부르기엔 너무 이르다.
