# Hermes Watch replay-derived corpus refinement plan closure v0.1

- Date: 2026-04-16 21:37:35 KST
- Scope: `scripts/hermes_watch.py`, `tests/test_hermes_watch.py`, live refiner artifacts
- Cold label: **duplicate replay에서 생긴 `minimize_and_reseed` queue를 그냥 registry에 두지 않고, 실제 plan/orchestration/dispatch request까지 닫기 시작한 low-risk closure slice**

## 왜 이 slice를 골랐나
- latest `corpus_refinements.json`에는 `j2kmarkers.cpp:52` stable duplicate replay에서 파생된 `minimize_and_reseed` entry가 이미 recorded 상태로 있었다.
- 하지만 실제 refiner executor/plan surface는 `review_duplicate_crash_replay` 쪽에 비해 빈약해서, duplicate replay evidence가 minimization/reseed phase로 내려오면서 다시 얇은 generic plan으로 퇴화했다.
- 즉 true north 관점에서 `artifact preservation -> trigger/replay -> revision queue`는 있었지만, 그 다음 `revision queue -> self-contained execution artifact` closure가 corpus refinement rail에서는 약했다.

## root cause
1. `write_refiner_plan(...)`의 extra section은 duplicate replay review 전용이었다.
2. `minimize_and_reseed` entry는 duplicate replay source key, first/latest artifact, replay markdown path를 들고 있어도 plan과 prompt에 노출되지 않았다.
3. 그래서 live queue를 consume해도 cron prompt/request는 generic corpus-maintenance 텍스트만 남기고, 왜 이 reseed가 필요한지와 어떤 artifact를 기준으로 검증해야 하는지가 빠졌다.

## 이번에 바꾼 것
- `scripts/hermes_watch.py`
  - `_refiner_corpus_refinement_plan_sections(repo_root, entry)` 추가
  - `minimize_and_reseed` plan에 다음을 자동 노출하도록 확장
    - `candidate_route`
    - `derived_from_action_code`
    - `duplicate_replay_source_key`
    - crash fingerprint/location/summary
    - occurrence count
    - first/latest artifact path
    - replay markdown path / harness path
  - 같은 section에서 low-risk command draft를 자동 생성
    - triage/regression/known-bad bucket 준비용 `mkdir -p`
    - latest artifact의 non-destructive `cp -n`
    - first/latest artifact `sha1sum` / `cmp -l`
    - replay markdown preview용 `sed -n`
  - `_refiner_extra_context_lines(...)`도 `minimize_and_reseed`를 이해하도록 확장해 cron/subagent prompt에 같은 duplicate replay context가 들어가게 함
  - `_refiner_extra_plan_sections(...)`가 `repo_root`를 받아 corpus bucket command를 실제 repo 기준으로 계산하도록 변경
- `tests/test_hermes_watch.py`
  - duplicate replay-derived corpus refinement plan section regression test 추가
  - corpus refinement orchestration prompt가 duplicate replay context를 포함하는지 regression test 추가

## TDD / verification
### RED
- `pytest -q tests/test_hermes_watch.py -k 'duplicate_replay_derived_corpus_refinement_plan or includes_duplicate_replay_context_for_corpus_refinement'`
- 초기 결과: 2 fail
  - `## Corpus Refinement Context` 부재
  - cron prompt에 duplicate replay context 부재

### GREEN
- 같은 명령 재실행 -> 2 pass
- 관련 범위 회귀:
  - `pytest -q tests/test_hermes_watch.py -k 'minimize_and_reseed or corpus_refinement or prepare_next_refiner_orchestration or execute_next_refiner_action'` -> 18 pass
- 전체 회귀:
  - `pytest -q` -> 326 pass

## live closure
- live queue consume:
  - `prepare_next_refiner_orchestration(...)` 실행으로 current `minimize_and_reseed` entry를 실제 consume
  - 생성 산출물:
    - `fuzz-records/refiner-plans/minimize_and_reseed-home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_202702_1d5b676.md`
    - `fuzz-records/refiner-orchestration/minimize_and_reseed-home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_202702_1d5b676-cron.txt`
    - `fuzz-records/refiner-orchestration/minimize_and_reseed-home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_202702_1d5b676.json`
- live dispatch draft:
  - `dispatch_next_refiner_orchestration(...)` 실행
  - 생성 산출물:
    - `fuzz-records/refiner-dispatch/minimize_and_reseed-home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_202702_1d5b676-cronjob-request.json`
- registry closure 확인:
  - `corpus_refinements.json` entry가 `status=completed`, `orchestration_status=prepared`, `dispatch_status=ready`, `lifecycle=dispatch_ready`로 올라감

## 왜 이게 mattered
- duplicate replay evidence가 이제 review 단계에서만 rich하고 reseed 단계에서 다시 빈약해지는 문제가 줄었다.
- 현재 시스템은 아직 minimization을 자동 실행하지 않지만, 적어도 **어떤 artifact를 기준으로 어떤 bounded command를 검토해야 하는지**를 fresh session-friendly prompt/request로 넘길 수 있게 됐다.
- 즉 `artifact preservation -> trigger/replay -> minimization/reseed planning artifact` 고리가 처음으로 corpus refinement rail에서도 실제로 닫히기 시작했다.

## 한계
- 아직 crash minimization 자체를 실행하거나 결과 seed 품질을 검증하지는 않는다.
- `cp -n` command는 draft일 뿐이며, 실제 실행/검증/rollback policy는 아직 후속 slice다.
- current latest top-level crash (`coding_units.cpp:3076`) 문제는 그대로 남아 있다.

## next best move
1. `minimize_and_reseed` dispatch request를 실제 bounded follow-up runner가 읽게 해서 minimization command plan markdown을 한 단계 더 생성
2. minimization 결과 artifact에 대해 sha/size/replay-signature retention 검증 추가
3. 그 다음에야 duplicate family를 coverage bucket에서 얼마나 덜 재발견하는지 measure loop를 붙이는 것이 맞다
