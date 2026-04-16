# Note — multi-target adapter generalization v0.1

- Date: 2026-04-16 07:03:46 KST
- Scope: `scripts/hermes_watch_support/profile_summary.py`, `scripts/hermes_watch_support/target_adapter.py`, `tests/test_hermes_watch.py`

## 이번 단계에서 한 일
- target profile의 `target.adapter` spec을 `build_target_profile_summary(...)`가 summary에 포함하도록 확장했다.
- `get_target_adapter(...)`가 이제 summary 안의 adapter spec을 읽어 실제 `TargetAdapter`로 해석할 수 있게 했다.
- 그래서 더 이상 custom target을 쓰려면 테스트에서 `get_target_adapter` 자체를 monkeypatch해야만 하는 상태가 아니다.
- `main()` 경로에 대해 custom adapter가 실제로 선택되어:
  - custom build command
  - custom smoke command
  - custom fuzz command
  - custom notification label
  - custom report target
  을 smoke-success/final-summary path에서 그대로 쓰는 E2E test를 추가했다.

## 왜 가치가 있나
이전 상태의 target adapter는 "seam은 있는데 selection은 사실상 single-target fallback"에 가까웠다.
즉 구조는 생겼지만 runtime reality는 아직 OpenHTJ2K 중심이었다.

이번 단계로 최소한 다음은 성립한다.
1. target profile이 explicit adapter spec을 들고 오면 main path가 그걸 실제 runtime command/label/target에 반영한다.
2. multi-target narrative가 mock-level이 아니라 main smoke/final-summary path에서 한 번은 검증됐다.
3. OpenHTJ2K-shaped leakage를 줄이는 첫 runtime closure가 생겼다.

## 아직 남은 점
- 이건 어디까지나 **v0.1**이다.
- 아직 broader multi-target generalization은 안 끝났다.
- 남은 큰 것:
  - build/smoke/fuzz command 외 다른 OpenHTJ2K leakage 분리
  - target-specific harness editable region policy seam
  - richer adapter/profile validation
  - 여러 target에 대한 regression smoke matrix

## 검증
- RED
  - custom adapter spec을 summary/profile에 넣어도 여전히 `openhtj2k` adapter를 반환하던 실패 확인
  - main smoke/final-summary path가 여전히 `scripts/build-libfuzzer.sh`를 호출하던 실패 확인
- GREEN / regression
  - `python -m pytest tests/test_hermes_watch.py::HermesWatchTargetAdapterTests::test_get_target_adapter_uses_custom_profile_adapter_spec tests/test_hermes_watch.py::HermesWatchTargetAdapterTests::test_main_smoke_success_and_final_summary_use_profile_selected_adapter -q`
  - `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/profile_summary.py scripts/hermes_watch_support/target_adapter.py tests/test_hermes_watch.py`
  - `python -m pytest tests/test_hermes_watch.py::HermesWatchTargetAdapterTests -q`
  - `python -m pytest tests/test_hermes_watch.py -q`
  - `python -m pytest tests -q`

## 냉정한 평가
좋아진 건 맞다.
하지만 이걸로 multi-target generalization이 됐다고 말하면 과장이다.
정확히는:
- **adapter seam이 mockable abstraction에서 profile-driven runtime seam으로 한 단계 현실화됐다**
정도가 맞다.
그래도 이 단계는 작지만 중요하다. 구조가 실제 runtime behavior를 바꾸지 못하면 그 구조는 장식에 가깝기 때문이다.
이번엔 그 장식성을 한 단계 벗겼다.
