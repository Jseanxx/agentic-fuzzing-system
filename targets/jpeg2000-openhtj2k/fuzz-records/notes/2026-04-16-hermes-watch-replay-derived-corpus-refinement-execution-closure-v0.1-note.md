# Hermes Watch replay-derived corpus refinement execution closure v0.1

- Date: 2026-04-16 21:50:28 KST
- Scope: `scripts/hermes_watch.py`, `tests/test_hermes_watch.py`, live corpus refinement artifacts
- Cold label: **duplicate replay에서 나온 `minimize_and_reseed` rail을 문서 단계에서 멈추지 않고 실제 corpus bucket sync + retention replay evidence까지 닫은 low-risk execution slice**

## 왜 이 slice를 골랐나
- 직전 상태에서는 `minimize_and_reseed`가 plan/orchestration/dispatch artifact까지는 갔지만, 실제 loop는 여전히 사람이 나중에 읽을 문서에서 멈췄다.
- duplicate replay로 `j2kmarkers.cpp:52` family가 stable하다는 것은 이미 증명됐는데, 그 결과를 triage/regression/known-bad corpus로 안전하게 내려보내고 copied seed가 같은 family를 유지하는지 확인하는 bounded execution artifact가 없었다.
- true north 관점에서 지금 필요한 것은 control-plane ornament보다 실제 `artifact preservation -> trigger/replay -> reseed execution -> rerun evidence` closure다.

## root cause
1. `minimize_and_reseed` executor는 사실상 plan writer 역할만 했다.
2. latest duplicate artifact를 triage/regression bucket으로 sync해도 되는 안전한 범위와 그 결과를 검증하는 표준 artifact가 없었다.
3. empty artifact path가 `Path('.')`로 해석될 수 있는 latent bug도 남아 있어, 얕은 placeholder entry에서 실제 execution helper를 붙이면 오히려 잘못된 로컬 path를 열 위험이 있었다.

## 이번에 바꾼 것
- `scripts/hermes_watch.py`
  - `_optional_path(...)` 추가로 empty path를 `Path('.')`로 잘못 해석하지 않도록 보강
  - `execute_corpus_refinement_probe(repo_root, entry, replay_runner=...)` 추가
    - latest artifact를 `fuzz/corpus/triage`, `fuzz/corpus/regression`, `fuzz/corpus/known-bad`로 non-destructive copy
    - first/latest/copy SHA1 lineage 기록
    - regression bucket copy를 standalone harness로 bounded replay
    - retention replay exit/signature/log 저장
    - 결과를 `fuzz-records/corpus-refinement-executions/*.json|md|log`에 기록
    - entry에 `corpus_refinement_execution_*`, `triage_bucket_path`, `regression_bucket_path`, `known_bad_bucket_path`, `retention_replay_*` lineage 반영
  - `_refiner_corpus_refinement_plan_sections(...)`가 execution section을 함께 보여주도록 확장
  - `execute_next_refiner_action(...)`가 `minimize_and_reseed`에서 실제 execution helper를 호출하도록 연결
  - duplicate replay helper도 optional path handling을 같이 적용해 latent empty-path bug를 줄임
- `tests/test_hermes_watch.py`
  - corpus refinement execution artifact regression test 추가
  - execute-next-refiner lineage/plan section regression test 추가
  - 기존 corpus refinement/orchestration regression이 empty artifact path에서도 깨지지 않도록 실제 버그를 같이 복구

## TDD / verification
### RED
- `pytest -q tests/test_hermes_watch.py -k 'execute_corpus_refinement_probe_copies_seed_and_verifies_replay_retention or execute_next_refiner_action_records_corpus_refinement_execution_lineage'`
- 초기 결과: `2 failed`
  - `execute_corpus_refinement_probe` 부재
  - `minimize_and_reseed` execution lineage 부재
- 추가 회귀에서 latent bug 확인:
  - empty artifact path가 `Path('.')`로 해석돼 `IsADirectoryError` 발생

### GREEN
- 같은 명령 재실행 -> `2 passed`
- 관련 범위 회귀:
  - `pytest -q tests/test_hermes_watch.py -k 'minimize_and_reseed or corpus_refinement or duplicate_replay'` -> `9 passed`
- 전체 회귀:
  - `pytest -q` -> `328 passed`

## live verification
- existing entry 실행:
  - `python - <<'PY' ... hw.execute_corpus_refinement_probe(...) ... PY`
- 생성 artifact:
  - `fuzz-records/corpus-refinement-executions/home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_202702_1d5b676.json`
  - `fuzz-records/corpus-refinement-executions/home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_202702_1d5b676.md`
  - `fuzz-records/corpus-refinement-executions/home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_202702_1d5b676-retention-replay.log`
- corpus sync 확인:
  - `fuzz/corpus/triage/crash-5e1dbfc1e1257014678913af52217fa8eb380818`
  - `fuzz/corpus/regression/crash-5e1dbfc1e1257014678913af52217fa8eb380818`
  - `fuzz/corpus/known-bad/crash-5e1dbfc1e1257014678913af52217fa8eb380818`
- retention replay 결과:
  - exit code: `-6`
  - fingerprint: `asan|j2kmarkers.cpp:52|heap-buffer-overflow ...`
  - copied regression seed에서도 same family 유지 확인
- plan refresh 확인:
  - `fuzz-records/refiner-plans/minimize_and_reseed-home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_202702_1d5b676.md`
  - `## Corpus Refinement Execution` section 추가 확인

## 왜 이게 mattered
- duplicate replay evidence가 이제 단순 planning substrate가 아니라 실제 corpus bucket과 rerun evidence로 내려간다.
- 시스템이 같은 family를 또 coverage loop에서 다시 밟지 않도록 할 수 있는 첫 번째 bounded operational input이 생겼다.
- "실행은 나중"이 아니라, 실제 seed copy + replay retention evidence를 남겼기 때문에 LLM이 다음 minimization/reseed slice를 훨씬 더 grounded하게 잡을 수 있다.

## 한계
- 아직 crash minimization 자체는 하지 않는다.
- reseed 후 bounded rerun에서 coverage가 정말 더 좋아지는지 측정하지 않았다.
- `coding_units.cpp:3076` medium duplicate family는 여전히 별도 review 대상이다.

## next best move
1. copied regression seed를 기준으로 bounded minimization artifact를 만들고 retention replay를 다시 붙이기
2. reseed 후 짧은 watcher rerun으로 duplicate recurrence/coverage delta를 측정하기
3. 그 다음 `coding_units.cpp:3076` family도 replay-review 승격 규칙을 재평가하기
