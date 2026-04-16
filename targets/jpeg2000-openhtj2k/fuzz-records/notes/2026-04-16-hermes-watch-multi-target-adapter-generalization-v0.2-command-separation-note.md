# Note — multi-target adapter generalization v0.2 command separation slice

- Date: 2026-04-16 07:12:28 KST
- Scope: `scripts/hermes_watch_support/harness_probe.py`, `tests/test_hermes_watch.py`

## 이번 단계에서 한 일
- short harness probe와 harness skeleton closure가 이제 repo의 target profile adapter spec을 읽어 build/smoke probe command를 결정하도록 확장했다.
- 기존에는 main watcher path만 adapter-driven runtime command를 썼고,
  probe/closure 보조 루프는 여전히 build system 추정(`cmake`, `meson`, `make`) + `run-smoke.sh` 탐색에 강하게 의존했다.
- 이번 단계로 `harness_probe` 계층에서:
  - default target profile resolve
  - target profile load
  - profile summary build
  - adapter selection
  을 수행하고, explicit adapter spec이 있으면 그 command를 우선 사용한다.
- 그 결과 `build_harness_probe_draft(...)`와 `run_harness_skeleton_closure(...)`가 custom adapter command를 실제 runtime에서 소비할 수 있게 됐다.

## 왜 가치가 있나
이전 v0.1은 main watcher runtime만 generalize했다.
그래서 겉보기엔 multi-target adapter seam이 생겼지만,
실제로 harness probe / skeleton closure 같은 중요한 하위 loop는 여전히 OpenHTJ2K-shaped command derivation에 묶여 있었다.

이번 단계의 의미는:
1. adapter seam이 main loop에만 국한되지 않고 probe/closure 보조 loop까지 퍼지기 시작했다.
2. broader command separation의 첫 실제 closure가 생겼다.
3. multi-target narrative가 "report/notification만 바뀌는 수준"에서 벗어나, build/smoke probe command derivation 자체를 바꾸기 시작했다.

## 아직 남은 점
- 이건 여전히 `v0.2`의 한 slice일 뿐이다.
- 남아 있는 것:
  - editable-region policy seam 분리
  - regression smoke matrix 정리
  - harness draft/evaluation/revision 쪽 추가 adapter leakage 제거
  - profile/adapter validation 강화

## 검증
- RED
  - custom profile adapter spec이 있어도 `build_harness_probe_draft(...)`와 `run_harness_skeleton_closure(...)`가 여전히 `make -n`을 쓰는 실패 확인
- GREEN / regression
  - `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessProbeTests::test_build_harness_probe_draft_uses_profile_selected_adapter_commands tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_run_harness_skeleton_closure_uses_profile_selected_adapter_commands -q`
  - `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/harness_probe.py scripts/hermes_watch_support/harness_skeleton.py scripts/hermes_watch_support/profile_summary.py scripts/hermes_watch_support/target_adapter.py tests/test_hermes_watch.py`
  - `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessProbeTests tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests -q`
  - `python -m pytest tests/test_hermes_watch.py -q`
  - `python -m pytest tests -q`

## 냉정한 평가
좋아진 건 분명하다.
하지만 아직 multi-target substrate가 완성된 건 아니다.
정확한 표현은:
- **main runtime adapter seam을 probe/closure command derivation까지 확장한 slice**
이다.

즉 이번 단계는 구조적 의미가 꽤 있지만,
아직 broader editable-region policy나 regression matrix가 없어서
"이제 진짜 여러 타겟에 바로 쓸 수 있다"고 말하긴 이르다.
그래도 command separation 관점에서는 꽤 중요한 진전이다.
