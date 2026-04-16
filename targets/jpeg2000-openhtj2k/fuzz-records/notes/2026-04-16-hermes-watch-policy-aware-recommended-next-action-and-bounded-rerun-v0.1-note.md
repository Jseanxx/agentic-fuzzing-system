# Hermes Watch Policy-Aware Recommended Next Action + Bounded Rerun v0.1

- 날짜: 2026-04-16 20:09:26 KST
- 단계 성격: report-surface contract hardening + real loop bounded rerun verification

## 왜 이 단계를 골랐나
직전 rehydrated report sync v0.1까지 끝난 뒤에도 `FUZZING_REPORT.md`의 `## Recommended Next Action`는 여전히 outcome-only 하드코딩 문구를 썼다.
즉:
- `Policy Action` section은 최신 policy/objective를 보여주는데
- 마지막 action summary는 여전히 generic `Ask Codex ...` 문구를 남겼다.

이건 surface drift다. operator/LLM이 report를 위에서 아래로 읽으면 마지막 한 줄에서 다시 stale 행동을 읽게 된다.
그리고 이 drift를 고친 뒤에는 실제 새 run이 처음부터 같은 정렬을 생성하는지 바로 확인해야 했다.

## root cause
`write_report(...)`와 `rewrite_rehydrated_report(...)`는 `policy_recommended_action`을 이미 계산/보존하고 있었지만,
`## Recommended Next Action`만 `recommended_action(outcome)`에 묶여 있었다.
그래서:
- leak rehydrate 후에도 generic crash 문구가 남을 수 있었고
- fresh bounded rerun에서도 report 말미가 policy-aware 행동을 반영하지 못했다.

## 이번에 바꾼 것
### 1. `scripts/hermes_watch.py`
- `recommended_action(...)`이 이제 optional `policy_action`을 받는다.
- `policy_action.recommended_action`이 있으면 그 문구를 report action summary의 우선 source로 사용한다.
- `write_report(...)`가 `Recommended Next Action`를 policy-aware로 출력한다.
- `rewrite_rehydrated_report(...)`도 stale report를 rehydrate할 때 같은 section을 다시 쓴다.

### 2. `tests/test_hermes_watch.py`
- rehydrate regression fixture에 stale `## Recommended Next Action` section을 추가하고,
  rehydrate 뒤 leak-aware action text로 교체되는지 확인했다.
- `write_report(...)`가 fresh report에서 policy action 문구를 말미 action summary로 쓰는 regression test를 추가했다.

## 실제 bounded rerun 검증
다음 명령으로 실제 새 run을 발생시켰다.
- `python scripts/hermes_watch.py --repo /home/hermes/work/fuzzing-jpeg2000 --max-total-time 5 --no-progress-seconds 30`

결과:
- 새 run dir: `fuzz-artifacts/runs/20260416_200858_1d5b676`
- corpus가 `3 -> 5`, `672b -> 1066b`, `cov 42 -> 45`, `ft 121 -> 137`
- 새 crash family:
  - `asan|j2kmarkers.cpp:52|heap-buffer-overflow ... j2k_marker_io_base::get_byte()`
- stage classification:
  - `crash_stage = ht-block-decode`
  - `crash_stage_class = deep`
  - `crash_stage_depth_rank = 4`
- profile trigger:
  - `policy_action_code = continue_and_prioritize_triage`
  - `policy_matched_triggers = ['deep_signal_emergence']`
  - `policy_profile_severity = critical`
- report 말미 action summary:
  - `- Keep the run going but prioritize this new deep-stage crash family in triage.`

즉 이번 bounded rerun은 두 가지를 동시에 확인했다.
1. fresh run이 처음부터 policy-aware `Recommended Next Action`를 자연 생성했다.
2. stale leak 재발만이 아니라 더 깊은 새 crash family를 실제로 하나 더 잡았다.

## 왜 이게 중요했나
이 단계는 문구 polish가 아니다.
`Recommended Next Action`는 report를 다 읽은 뒤 operator/LLM이 바로 따라갈 마지막 행동 contract다.
이게 stale하면 앞 section이 맞아도 실제 다음 행동이 틀어진다.

이번에 얻은 가치:
- report surface 전체가 policy/action spine으로 정렬됨
- rehydrate path와 fresh run path가 같은 행동 contract를 공유함
- bounded rerun이 실제로 새로운 deep-stage crash family까지 포착해 loop가 단순 stale repair에서 다시 finding loop로 돌아왔음

## 검증
- RED
  - `pytest -q tests/test_hermes_watch.py -k 'write_report_uses_policy_recommended_action_in_recommended_next_action_section or rehydrate_run_artifacts_reclassifies_stale_leak_metadata_without_duplicating_history'`
- GREEN
  - 같은 targeted test 재실행 통과
- full
  - `pytest -q`
- real loop
  - `python scripts/hermes_watch.py --repo /home/hermes/work/fuzzing-jpeg2000 --max-total-time 5 --no-progress-seconds 30`
- evidence refresh
  - `python scripts/hermes_watch.py --repo /home/hermes/work/fuzzing-jpeg2000 --write-llm-evidence-packet`

## 한계
- 이 단계는 report action contract를 맞춘 것이지 crash closure 자체를 수행한 건 아니다.
- 새 deep-stage crash는 `j2kmarkers.cpp:52` parser-side read OOB로 보이며, triage/seed isolation/closure는 아직 남아 있다.
- `llm_objective`는 현재 `stage-reach-or-new-signal`로 갔지만, 실제 다음 수는 이 새 crash family를 재현/분리/깊이 기준으로 평가하는 triage 쪽이 더 직접적이다.

## 다음 최선 수
1. 새 `crash-964206...` artifact를 중심으로 deep-decode-v3 triage/regression closure를 만든다.
2. toxic startup seed인지 아닌지 확인해 coverage bucket 오염 여부를 판단한다.
3. `j2kmarkers.cpp:52` family를 parser/marker-length 쪽 specialized harness or seed strategy와 어떻게 연결할지 검토한다.
