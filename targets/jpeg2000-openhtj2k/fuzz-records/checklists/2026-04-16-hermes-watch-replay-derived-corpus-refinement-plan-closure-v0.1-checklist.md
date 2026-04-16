# Hermes Watch replay-derived corpus refinement plan closure v0.1 checklist

- Date: 2026-04-16 21:37:35 KST
- Status: done

## Goal
- duplicate replay에서 파생된 `minimize_and_reseed` entry가 generic placeholder가 아니라 실제 bounded plan/orchestration/dispatch artifact로 내려오게 만들기

## Completed
- [x] fresh `corpus_refinements.json` state inspected
- [x] duplicate replay-derived minimize/reseed entry 존재 확인
- [x] failing regression tests added for corpus refinement plan/prompt enrichment
- [x] RED 확인 (`2 failed`)
- [x] `scripts/hermes_watch.py`에 corpus refinement context/command section 추가
- [x] corpus refinement cron prompt에 duplicate replay context 노출 추가
- [x] targeted refiner tests passed (`18 passed`)
- [x] full pytest passed (`326 passed`)
- [x] live `prepare_next_refiner_orchestration(...)` 실행
- [x] live `dispatch_next_refiner_orchestration(...)` 실행
- [x] generated plan/orchestration/dispatch artifacts 확인
- [x] `corpus_refinements.json` lifecycle가 `dispatch_ready`까지 올라간 것 확인

## Evidence
- Tests:
  - `pytest -q tests/test_hermes_watch.py -k 'duplicate_replay_derived_corpus_refinement_plan or includes_duplicate_replay_context_for_corpus_refinement'`
  - `pytest -q tests/test_hermes_watch.py -k 'minimize_and_reseed or corpus_refinement or prepare_next_refiner_orchestration or execute_next_refiner_action'`
  - `pytest -q`
- Live artifacts:
  - `fuzz-records/refiner-plans/minimize_and_reseed-home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_202702_1d5b676.md`
  - `fuzz-records/refiner-orchestration/minimize_and_reseed-home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_202702_1d5b676-cron.txt`
  - `fuzz-records/refiner-dispatch/minimize_and_reseed-home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_202702_1d5b676-cronjob-request.json`

## Remaining
- [ ] actual minimization execution artifact
- [ ] minimized seed replay-retention verification
- [ ] family rediscovery reduction measurement after reseed action
