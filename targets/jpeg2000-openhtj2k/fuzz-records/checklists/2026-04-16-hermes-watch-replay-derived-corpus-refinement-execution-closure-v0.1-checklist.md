# Hermes Watch replay-derived corpus refinement execution closure v0.1 checklist

- Date: 2026-04-16 21:50:28 KST
- Status: done

## Goal
- duplicate replay에서 파생된 `minimize_and_reseed` rail이 실제 corpus sync + retention replay evidence까지 bounded하게 닫히도록 만들기

## Completed
- [x] fresh `corpus_refinements.json` state inspected
- [x] existing `minimize_and_reseed` entry가 plan-only 상태였는지 확인
- [x] failing regression tests added for corpus refinement execution helper + lineage
- [x] RED 확인 (`2 failed`)
- [x] empty artifact path -> `Path('.')` latent bug 재현 및 원인 확인
- [x] `scripts/hermes_watch.py`에 `_optional_path(...)` 추가
- [x] `execute_corpus_refinement_probe(...)` 구현
- [x] latest artifact triage/regression/known-bad copy lineage 추가
- [x] copied regression seed retention replay + signature/log artifact 추가
- [x] `execute_next_refiner_action(...)`에 corpus refinement execution 연결
- [x] refiner plan에 `## Corpus Refinement Execution` section 노출 추가
- [x] targeted related tests passed (`9 passed`)
- [x] full pytest passed (`328 passed`)
- [x] live existing entry execution performed
- [x] live corpus buckets updated with duplicate replay artifact
- [x] live retention replay signature confirmed for copied regression seed
- [x] canonical plan/current-status/progress-index updated

## Evidence
- Tests:
  - `pytest -q tests/test_hermes_watch.py -k 'execute_corpus_refinement_probe_copies_seed_and_verifies_replay_retention or execute_next_refiner_action_records_corpus_refinement_execution_lineage'`
  - `pytest -q tests/test_hermes_watch.py -k 'minimize_and_reseed or corpus_refinement or duplicate_replay'`
  - `pytest -q`
- Live artifacts:
  - `fuzz-records/corpus-refinement-executions/home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_202702_1d5b676.json`
  - `fuzz-records/corpus-refinement-executions/home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_202702_1d5b676.md`
  - `fuzz-records/corpus-refinement-executions/home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_202702_1d5b676-retention-replay.log`
  - `fuzz-records/refiner-plans/minimize_and_reseed-home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_202702_1d5b676.md`
- Live copied seeds:
  - `fuzz/corpus/triage/crash-5e1dbfc1e1257014678913af52217fa8eb380818`
  - `fuzz/corpus/regression/crash-5e1dbfc1e1257014678913af52217fa8eb380818`
  - `fuzz/corpus/known-bad/crash-5e1dbfc1e1257014678913af52217fa8eb380818`

## Remaining
- [ ] actual crash minimization artifact generation
- [ ] reseed effectiveness measurement with bounded rerun
- [ ] medium duplicate family (`coding_units.cpp:3076`) replay-review escalation decision
