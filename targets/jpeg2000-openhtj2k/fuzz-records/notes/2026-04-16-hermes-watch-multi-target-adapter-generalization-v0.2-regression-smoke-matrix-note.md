# Note — multi-target adapter generalization v0.2 regression smoke matrix slice

- Date: 2026-04-16 07:24:55 KST
- Scope: `scripts/hermes_watch.py`, `scripts/hermes_watch_support/target_adapter.py`, `tests/test_hermes_watch.py`

## 이번 단계에서 한 일
- target adapter 기준으로 main / harness-probe / skeleton-closure 경로의 build·smoke·fuzz command expectation을 한 곳에서 요약하는 regression smoke matrix artifact helper를 추가했다.
- 추가된 핵심 함수:
  - `build_target_adapter_regression_smoke_matrix(...)`
  - `render_target_adapter_regression_smoke_matrix_markdown(...)`
  - `write_target_adapter_regression_smoke_matrix(...)`
  - `write_runtime_target_adapter_regression_smoke_matrix(...)`
- 이 helper는 adapter command뿐 아니라
  - `editable_harness_relpath`
  - `fuzz_entrypoint_names`
  도 함께 기록해, command seam과 policy seam을 한 번에 읽을 수 있게 했다.

## 왜 가치가 있나
지금까지는 multi-target generalization slice들이 각각은 맞았지만,
"현재 adapter가 실제로 어떤 command/policy contract를 제공해야 하는지"를 한 장으로 검증하는 artifact가 없었다.
그러면 나중에 leakage가 다시 들어와도 금방 눈치채기 어렵다.

이번 단계의 의미:
1. adapter contract를 regression-readable matrix로 승격
2. main / probe / closure 경로가 같은 adapter contract를 공유하는지 한눈에 점검 가능
3. 이후 smoke matrix를 실제 multi-target smoke run checklist로 확장할 발판 확보

## 아직 부족한 점
- 이건 expectation matrix지, 실제 여러 target에 대한 live smoke execution matrix는 아니다.
- 아직 CLI subcommand까지 붙이지 않았다.
- mutation generation rail 자체를 target-aware하게 만드는 단계는 아직 남아 있다.
- 결국 이건 **검사/가시화 artifact**를 추가한 단계다.

## 검증
- RED
  - runtime default profile을 읽어 matrix artifact를 쓰는 helper 부재(`AttributeError`) 확인
- GREEN / regression
  - `python -m pytest tests/test_hermes_watch.py::HermesWatchTargetAdapterTests -q`
  - `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/target_adapter.py tests/test_hermes_watch.py`
  - `python -m pytest tests/test_hermes_watch.py -q`
  - `python -m pytest tests -q`

## 냉정한 평가
이 단계는 눈에 띄는 기능 강화라기보다, generalization 진행 상황을 더 속이기 어렵게 만드는 검사층 추가다.
즉 효율을 직접 올리진 않지만,
multi-target substrate가 실제로 얼마나 퍼졌는지 점검 가능한 surface를 만들었다는 점에서 의미가 있다.
과장 없이 말하면 **실행 엔진 확장이라기보다 regression visibility 강화 단계**다.
