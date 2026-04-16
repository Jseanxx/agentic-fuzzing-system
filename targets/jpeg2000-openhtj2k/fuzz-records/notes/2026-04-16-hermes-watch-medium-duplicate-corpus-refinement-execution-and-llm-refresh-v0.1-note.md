# Hermes Watch — medium duplicate corpus refinement execution + LLM refresh v0.1

- Date: 2026-04-16 22:10:12 KST
- Scope: `coding_units.cpp:3076` repeated medium duplicate family, refiner executor packet freshness

## 왜 이 단계가 필요했나
`coding_units.cpp:3076` medium duplicate family는 replay review와 `minimize_and_reseed` queue까진 올라왔지만, 실제 corpus refinement execution은 아직 안 닫혀 있었다. 그래서 true north 기준으로 `replay evidence -> actual preservation/replay-retention` 고리가 medium duplicate rail에서 비어 있었다.

추가로 `execute_next_refiner_action(...)`는 refiner action을 실제로 닫아도 `openhtj2k-llm-evidence.json`을 다시 쓰지 않았다. 이 상태에서는 operator가 refiner rail을 실제 소비한 뒤에도 다음 LLM handoff packet이 stale queue/execution 상태를 보여줄 수 있었다.

## 이번에 바꾼 것
1. `scripts/hermes_watch.py`
   - `execute_next_refiner_action(...)`가 registry 저장 직후 `refresh_llm_evidence_packet_best_effort(repo_root)`를 호출하도록 보강
   - result payload에 최신 `llm_evidence_json_path`, `llm_evidence_markdown_path`를 포함
2. `tests/test_hermes_watch.py`
   - corpus refinement 실행 뒤 evidence refresh가 실제로 호출되는지 regression test 추가
3. live action
   - pending `minimize_and_reseed:duplicate-replay:asan|coding_units.cpp:3076|...` entry를 실제 consume
   - medium duplicate artifact를 `triage/regression/known-bad` bucket에 copy
   - regression bucket copy를 standalone harness로 replay해 same crash family retention 확인

## 검증
### RED
- `pytest -q tests/test_hermes_watch.py -k 'refreshes_llm_evidence_after_corpus_refinement or records_corpus_refinement_execution_lineage'`
- 초기 결과: 1 fail
- 실패 이유: refiner executor가 `refresh_llm_evidence_packet_best_effort(...)`를 호출하지 않음

### GREEN
- 같은 명령 재실행: 2 pass
- `pytest -q tests/test_hermes_watch.py -k 'duplicate_crash or corpus_refinement or llm_evidence or execute_next_refiner_action'`: 49 pass
- `pytest -q`: 331 pass

### Live verification
- 실행 결과:
  - `fuzz-records/corpus-refinement-executions/home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_205450_1d5b676.md`
  - `fuzz-records/refiner-plans/minimize_and_reseed-home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_205450_1d5b676.md`
  - `fuzz-records/llm-evidence/openhtj2k-llm-evidence.json`
- `corpus_refinements.json` entry 상태:
  - `status=completed`
  - `corpus_refinement_execution_status=completed`
- bucket sync 확인:
  - `fuzz/corpus/triage/crash-a54fa005c53939e5b74e7ab86fe5d5df98eb2f9a`
  - `fuzz/corpus/regression/crash-a54fa005c53939e5b74e7ab86fe5d5df98eb2f9a`
  - `fuzz/corpus/known-bad/crash-a54fa005c53939e5b74e7ab86fe5d5df98eb2f9a`
- retention replay 확인:
  - exit code `-6`
  - fingerprint `asan|coding_units.cpp:3076|SEGV ...`
- refreshed packet 확인:
  - `suggested_action_code = minimize_and_reseed`
  - `suggested_candidate_route = reseed-before-retry`
  - duplicate replay / corpus refinement context가 latest packet에 반영됨

## 의미
- medium duplicate family도 이제 실제 `artifact preservation -> replay evidence -> reseed execution -> retention verification`까지 닫혔다.
- refiner executor가 끝난 뒤 packet이 stale 상태로 남는 문제를 줄여, 다음 LLM step이 실제 최신 queue/execution 현실을 더 잘 보게 됐다.
- 이건 control-plane ornament가 아니라, repeated crash family를 실제 preservation/replay rail로 내려주는 실루프 품질 보강이다.

## 아직 남은 것
- reseed 후 bounded rerun에서 coverage delta / duplicate recurrence / novelty가 실제로 좋아졌는지 계측 필요
- crash minimization 자체는 아직 없음
- remote/proxmox에서 같은 preservation/replay/packet loop 재현 필요

## 냉정한 판단
이번 단계는 과장이 아니다. medium duplicate family를 실제 bucket/replay evidence로 내렸고, packet freshness도 보강했다. 하지만 finding efficiency improvement는 아직 주장할 수 없다. 다음은 반드시 bounded rerun 계측이어야 한다.
