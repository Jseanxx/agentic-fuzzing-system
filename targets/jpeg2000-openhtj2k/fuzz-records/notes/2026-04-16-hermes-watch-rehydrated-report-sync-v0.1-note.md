# Hermes Watch Rehydrated Report Sync v0.1

- 날짜: 2026-04-16 20:00:40 KST
- 단계 성격: report-level stale excerpt cleanup / canonical state sync hardening

## 왜 이 단계를 골랐나
직전 leak state rehydration v0.1으로 `current_status.json`, `run_history.json`, `crash_index.json`는 이미 `leak|coding_units.cpp:3927|...` 기준으로 복구됐다.
하지만 실제 operator가 가장 먼저 보는 `FUZZING_REPORT.md`는 여전히 stale한
- `artifact_category: crash`
- `policy_action_code: triage-new-crash`
- `crash_kind: asan`
- `crash_fingerprint: asan|unknown-location|...`
를 유지하고 있었다.

즉 canonical state와 report surface가 서로 다른 이야기를 하고 있었고, 이 상태는 artifact-first 운영에 바로 해가 된다.
LLM/사람/디스코드 요약 중 누구든 report를 먼저 읽으면 stale 판단을 다시 가져갈 수 있기 때문이다.

## 이번에 바꾼 것
### 1. `scripts/hermes_watch.py`
- `_replace_report_section(...)` 추가
  - 기존 report 전체를 새로 생성하지 않고, 지정 section만 교체한다.
- `rewrite_rehydrated_report(...)` 추가
  - rehydrate 이후 다음 section들을 canonical leak state로 다시 쓴다.
    - `## Artifact Classification`
    - `## Policy Action`
    - `## Crash Fingerprint`
    - `## Crash Or Timeout Excerpt`
- `rehydrate_run_artifacts(...)`
  - status/current_status/run_history/crash_index 복구 뒤 report rewrite도 수행
  - 결과 JSON에 `report_rewritten` 추가

### 2. `tests/test_hermes_watch.py`
- 기존 stale leak rehydration regression test를 확장
- stale `FUZZING_REPORT.md` fixture를 넣고,
  - leak classification
  - leak policy
  - leak fingerprint
  - LeakSanitizer excerpt
  로 실제 갱신되는지 확인하도록 강화

## 왜 이게 중요했나
이 단계는 보기 좋은 문서 정리가 아니라, loop의 evidence spine 정렬이다.

정렬 전:
- registry/state는 leak
- report는 generic crash
- 다음 operator/LLM handoff는 stale report를 다시 먹을 위험 존재

정렬 후:
- registry/state/report/LLM evidence가 모두 leak cleanup 방향을 가리킴
- 같은 run artifact를 어디서 열어도 해석이 덜 갈라짐
- 다음 bounded rerun 검증 전에도 현재 artifact surface는 honest해짐

## 검증
- RED
  - `pytest -q tests/test_hermes_watch.py -k rehydrate_run_artifacts_reclassifies_stale_leak_metadata_without_duplicating_history`
  - stale report가 그대로라 실패 확인
- GREEN
  - 같은 targeted test 통과
- broader targeted
  - `pytest -q tests/test_hermes_watch.py -k 'rehydrate_run_artifacts or leak or LeakSanitizer or classify_artifact_event_prefers_leak_over_generic_crash or decide_policy_action_handles_leak or build_crash_signature'`
- full
  - `pytest -q`
- real artifact replay
  - `python scripts/hermes_watch.py --repo /home/hermes/work/fuzzing-jpeg2000 --rehydrate-run-artifacts --rehydrate-run-dir /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_183444_1d5b676`
  - 결과: `report_rewritten: true`
- evidence refresh
  - `python scripts/hermes_watch.py --repo /home/hermes/work/fuzzing-jpeg2000 --write-llm-evidence-packet`

## 실제 확인 결과
latest `fuzz-artifacts/runs/20260416_183444_1d5b676/FUZZING_REPORT.md`가 이제 다음처럼 정렬됐다.
- `artifact_category: leak`
- `artifact_reason: sanitizer-leak`
- `policy_action_code: triage-leak-and-consider-coverage-policy`
- `policy_next_mode: coverage`
- `crash_kind: leak`
- `crash_location: coding_units.cpp:3927`
- `crash_stage: tile-part-load`
- `crash_fingerprint: leak|coding_units.cpp:3927|12312 byte(s) leaked in 1 allocation(s).`
- excerpt에도 `LeakSanitizer` line + artifact path + project stack frame 보존

## 한계
- 이 단계는 stale report 정렬이지, leak 자체를 닫은 게 아니다.
- `Recommended Next Action` section은 아직 generic crash 문구를 유지한다.
- repeated leak occurrence count는 rehydrate/packet 재생성 때문에 올라갈 수 있으므로, 중복 카운트 정책은 별도 냉정 점검이 필요하다.
- 진짜 다음 closure는 bounded rerun으로 새 run이 처음부터 올바른 report/state를 자연 생성하는지 확인하는 것이다.

## 다음 최선 수
1. deep-decode-v3 bounded rerun
   - 새 run이 report/state/evidence를 처음부터 leak-aware로 생성하는지 확인
2. leak cleanup closure slice
   - `coding_units.cpp:3927` allocation/free closure와 harness cleanup 경로를 실제 점검
3. 필요 시 `Recommended Next Action`도 policy/objective-aware로 정렬
