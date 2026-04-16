# Current Fuzzing System Status

- Updated: 2026-04-16 22:19:23 KST
- Project: `fuzzing-jpeg2000`
- Current objective: **실제 active fuzz rerun이 wrapper가 의도한 corpus/mode를 정말 따르도록 runtime corpus contract를 맞추고, 그 위에서 reseed effectiveness를 계측하는 것**
- Current phase: **deep-decode-v3 runtime corpus override alignment v0.1 적용: target profile의 hard-pinned corpus contract를 env-override friendly로 바꿔 `run-fuzz-mode.sh`가 말뿐인 wrapper가 아니라 실제 triage/coverage/regression corpus를 전달하는 단계**

---

## 한 줄 결론
**지금 시스템은 `minimize_and_reseed`로 보존한 corpus bucket과 실제 rerun wrapper 사이에 있던 끊긴 고리 하나를 메웠다. deep-decode-v3 profile이 더 이상 `fuzz/corpus-afl/deep-decode-v3`를 강제로 박아두지 않아서, `run-fuzz-mode.sh`가 지정한 corpus가 실제 fuzzer까지 전달된다. 즉 control-plane 문서가 아니라 real rerun contract를 바로잡은 단계다.**

## 지금 어디까지 왔나

### 이미 붙어 있는 핵심 축
1. **watcher / policy / artifact substrate**
   - build/smoke/fuzz 상태 기록
   - crash fingerprint / dedup
   - policy action / automation registry
   - regression trigger / 실행 기록

2. **refiner control-plane**
   - queue
   - orchestration
   - dispatch
   - bridge
   - launcher
   - verification
   - retry/escalation policy

3. **target-side intelligence 초입**
   - target profile draft
   - target reconnaissance
   - harness candidate draft
   - harness evaluation draft
   - short harness probe
   - probe feedback bridge
   - ranked candidate registry
   - evidence-aware candidate weighting

4. **R19 skeleton generation layer**
   - selected candidate 기준 harness skeleton source draft 생성
   - manifest / markdown / source artifact 저장
   - review/reseed feedback를 다음 revision draft로 연결

---

## 최근 핵심 완료 단계

### Deep-decode-v3 runtime corpus override alignment v0.1
- root cause:
  - fresh inspection에서 `run-fuzz-mode.sh coverage`는 겉으로는 `fuzz/corpus/coverage`를 출력했지만, 실제 fuzzer는 target profile adapter의 hard-coded `CORPUS_DIR=fuzz/corpus-afl/deep-decode-v3`를 따라가고 있었다.
  - 즉 `triage/coverage/regression` wrapper가 있어도 active deep-decode-v3 campaign에서는 corpus override가 무시됐고, `minimize_and_reseed`로 보존한 bucket과 real rerun contract가 분리돼 있었다.
  - 이 상태는 true north 기준으로 `revision/reseed -> rerun` 고리를 약화시키는 실제 loop bug였다.
- 이번에 고친 것:
  - `tests/test_aflpp_setup.py`
    - target profile fuzz command가 env override friendly contract(`FUZZER_BIN=${FUZZER_BIN:-...}`, `CORPUS_DIR=${CORPUS_DIR:-...}`)를 유지하는지 regression test로 고정
  - `fuzz-records/profiles/openhtj2k-target-profile-v1.yaml`
    - adapter `fuzz_command`를 hard-pinned literal에서 env-default shell expansion 형태로 변경
    - `meta.updated_at` 갱신
- 검증:
  - RED:
    - `pytest -q tests/test_aflpp_setup.py -k deep_decode_v3_adapter_contract` → 1 fail
    - 실패 이유: profile이 여전히 `FUZZER_BIN=... CORPUS_DIR=fuzz/corpus-afl/deep-decode-v3 ...`를 literal로 박고 있었음
  - GREEN:
    - 같은 명령 재실행 → 1 pass
    - `pytest -q tests/test_aflpp_setup.py` → 7 pass
    - `pytest -q` → 331 pass
  - live verification:
    - fix 전 bounded coverage rerun은 `INFO: 8 files found in fuzz/corpus-afl/deep-decode-v3`로 wrapper corpus override가 무시되는 것 확인
    - fix 후 `MAX_TOTAL_TIME=8 bash scripts/run-fuzz-mode.sh coverage` 재실행
    - `fuzz-artifacts/modes/coverage/20260416_221832_coverage/FUZZING_REPORT.md`에서
      - command가 env-default contract로 바뀐 것
      - 실제 seed corpus가 `7 files found in /home/hermes/work/fuzzing-jpeg2000/fuzz/corpus/coverage`로 로드된 것
      - bounded rerun이 `cov=53`, `ft=153`, duplicate `j2kmarkers.cpp:52` family를 다시 잡은 것
      확인
- 의미:
  - 이제 `run-fuzz-mode.sh`가 active profile에서도 실제 corpus/mode를 바꾸는 wrapper가 됐다.
  - `minimize_and_reseed`, quarantine, regression/coverage split 같은 기존 rail이 문서상 존재만 하는 상태에서 한 단계 내려와 real rerun input에 영향 줄 수 있게 됐다.
  - 다음 reseed effectiveness measurement가 비로소 의미 있는 실험이 됐다.
- 한계:
  - 지금 rerun 결과는 여전히 `j2kmarkers.cpp:52` duplicate family가 강하게 남아 있어 finding quality가 좋아졌다고는 못 한다.
  - active corpus quarantine/minimization은 아직 자동화되지 않았다.
  - remote/proxmox closure는 여전히 남아 있다.
- 관련 문서:
  - `notes/2026-04-16-deep-decode-v3-runtime-corpus-override-alignment-v0.1-note.md`
  - `checklists/2026-04-16-deep-decode-v3-runtime-corpus-override-alignment-v0.1-checklist.md`

### Medium duplicate corpus refinement execution + refiner-triggered LLM evidence refresh v0.1
- root cause:
  - `coding_units.cpp:3076` family는 replay review와 `minimize_and_reseed` queue까진 복구됐지만, 실제 corpus refinement execution은 아직 안 돌아서 medium duplicate가 여전히 문서/queue 단계에서 멈춰 있었다.
  - 추가로 `execute_next_refiner_action(...)`는 refiner rail을 실제 실행해도 `openhtj2k-llm-evidence.json`을 다시 쓰지 않아, operator가 refiner action을 수동/반자동으로 닫은 뒤 packet이 이전 stale state를 계속 보여줄 수 있었다.
  - 즉 true north 관점에서 `artifact preservation -> replay evidence -> reseed execution`과 `refiner execution -> fresh LLM handoff` 두 고리가 모두 medium duplicate rail에서 완전히 닫히지 않았다.
- 이번에 고친 것:
  - `scripts/hermes_watch.py`
    - `execute_next_refiner_action(...)`가 refiner action 저장 직후 `refresh_llm_evidence_packet_best_effort(repo_root)`를 호출하고, result에도 최신 evidence artifact path를 노출하도록 보강
  - `tests/test_hermes_watch.py`
    - refiner-driven corpus refinement 실행 뒤 evidence refresh가 실제 호출되는지 regression test 추가
  - live execution:
    - pending `minimize_and_reseed:duplicate-replay:asan|coding_units.cpp:3076|...` entry를 실제 consume
    - `fuzz-records/corpus-refinement-executions/home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_205450_1d5b676.md`
    - `fuzz-records/refiner-plans/minimize_and_reseed-home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_205450_1d5b676.md`
    - `fuzz-records/llm-evidence/openhtj2k-llm-evidence.json`
    - 위 artifact들이 medium duplicate family에 대한 bucket sync / retention replay / fresh packet sync를 실제로 남김
- 검증:
  - RED:
    - `pytest -q tests/test_hermes_watch.py -k 'refreshes_llm_evidence_after_corpus_refinement or records_corpus_refinement_execution_lineage'` → 초기 1 fail (`refresh_llm_evidence_packet_best_effort` 미호출)
  - GREEN:
    - 같은 명령 재실행 → 2 pass
    - `pytest -q tests/test_hermes_watch.py -k 'duplicate_crash or corpus_refinement or llm_evidence or execute_next_refiner_action'` → 49 pass
    - `pytest -q` → 331 pass
  - live verification:
    - `corpus_refinements.json`의 `coding_units.cpp:3076` entry가 `status=completed`, `corpus_refinement_execution_status=completed`로 올라간 것 확인
    - `fuzz/corpus/triage`, `fuzz/corpus/regression`, `fuzz/corpus/known-bad`에 `crash-a54fa005c53939e5b74e7ab86fe5d5df98eb2f9a` copy 생성 확인
    - retention replay exit code `-6`, fingerprint `asan|coding_units.cpp:3076|SEGV ...` 유지 확인
    - refresh 뒤 `openhtj2k-llm-evidence.json`이 latest duplicate context를 읽고 `suggested_action_code = minimize_and_reseed`, `suggested_candidate_route = reseed-before-retry`를 다시 노출하는 것 확인
- 의미:
  - medium duplicate family도 이제 진짜로 `artifact preservation -> replay evidence -> reseed execution -> retention verification`까지 내려간다.
  - refiner executor가 action을 닫은 뒤 packet이 stale 상태로 남는 문제를 줄여, 다음 LLM handoff가 실제 최신 queue/execution 현실을 더 잘 반영하게 됐다.
  - true north 기준으로 `repeated crash -> bounded preservation/replay -> fresh LLM-guided next move`가 한 단계 더 현실에 가까워졌다.
- 한계:
  - 아직 reseed 후 bounded rerun을 돌려 novelty/coverage가 실제로 좋아졌는지 측정하지 않았다.
  - crash minimization 자체는 아직 없다.
  - remote/proxmox closure는 여전히 별도 과제다.
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-medium-duplicate-corpus-refinement-execution-and-llm-refresh-v0.1-note.md`
  - `checklists/2026-04-16-hermes-watch-medium-duplicate-corpus-refinement-execution-and-llm-refresh-v0.1-checklist.md`

### Medium duplicate replay escalation + packet recovery v0.1
- root cause:
  - 최신 `coding_units.cpp:3076` family는 `occurrence_count=2`, `stage_class=medium`, `stage_depth_rank=2`였지만 policy는 deep duplicate만 `review_duplicate_crash_replay`로 승격했다.
  - 그래서 실제 latest repeated crash는 `record-duplicate-crash`로 끝났고, 이미 실행 가능한 replay review rail이 있어도 medium duplicate는 거기에 진입하지 못했다.
  - 추가 live verification에서 medium duplicate용 replay review entry를 수동 생성/실행해도 `llm_evidence`는 `policy_action_code == review_duplicate_crash_replay`일 때만 duplicate review context를 읽어서, 최신 packet이 여전히 `halt_and_review_harness` 쪽으로 보수적으로 기울었다.
  - 즉 `repeated duplicate -> replay evidence -> LLM routing override -> minimize/reseed next step` 고리가 medium duplicate family에서 끊겨 있었다.
- 이번에 고친 것:
  - `scripts/hermes_watch.py`
    - repeated duplicate가 `stage_class in {medium, deep}` 또는 `stage_depth_rank >= 2`면 `review_duplicate_crash_replay`로 승격되도록 policy 결정 조건 확장
  - `scripts/hermes_watch_support/llm_evidence.py`
    - `policy_action_code`가 이미 `record-duplicate-crash`여도 `crash_is_duplicate=true` + `crash_occurrence_count>=2`인 latest status면 fingerprint/run/report 기준으로 duplicate review registry를 다시 찾도록 완화
  - live execution:
    - latest `coding_units.cpp:3076` duplicate family에 대해 replay review entry를 실제 기록/실행
    - `fuzz-records/refiner-plans/review_duplicate_crash_replay-home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_205450_1d5b676.md`
    - `fuzz-records/duplicate-crash-replays/home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_205450_1d5b676.md`
    - 위 artifact가 first/latest seed 둘 다 `coding_units.cpp:3076` SEGV family를 유지하는 replay evidence를 남김
- 검증:
  - RED:
    - `pytest -q tests/test_hermes_watch.py -k 'escalates_repeated_medium_duplicate_to_replay_review or recovers_duplicate_review_context_for_repeated_duplicate_status'` → 초기 fail 2건
  - GREEN:
    - 같은 흐름 포함 targeted rerun → pass
    - `pytest -q tests/test_hermes_watch.py -k 'duplicate_crash or corpus_refinement or llm_evidence or decide_policy_action'` → 50 pass
    - `pytest -q` → 330 pass
  - live verification:
    - medium duplicate replay markdown에서 first/latest replay exit code 둘 다 `-6` 확인
    - first/latest signature가 둘 다 `asan|coding_units.cpp:3076|SEGV ...`로 일치함을 확인
    - `refresh_llm_evidence_packet_best_effort(...)` 후 latest packet이
      - `suggested_action_code = minimize_and_reseed`
      - `suggested_candidate_route = reseed-before-retry`
      - `duplicate_crash_review` populated
      로 바뀐 것 확인
- 의미:
  - medium duplicate family도 이제 deep duplicate와 같은 low-risk replay evidence rail로 올라간다.
  - 최신 repeated crash가 그냥 known-bad sink로 묻히지 않고, LLM packet이 실제 replay evidence를 읽은 상태로 다음 reseed/minimization slice를 제안한다.
  - true north 관점에서 `duplicate recurrence -> replay evidence -> LLM-guided next action` 고리가 medium 단계까지 확장됐다.
- 한계:
  - 아직 `coding_units.cpp:3076` family에 대한 실제 `minimize_and_reseed` execution은 없다.
  - replay evidence는 생겼지만 reseed 후 novelty/coverage 효율이 정말 좋아지는지 측정은 아직 안 했다.
  - remote/proxmox closure는 여전히 별도 과제다.
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-medium-duplicate-replay-escalation-and-packet-recovery-v0.1-note.md`
  - `checklists/2026-04-16-hermes-watch-medium-duplicate-replay-escalation-and-packet-recovery-v0.1-checklist.md`

### Replay-derived corpus refinement execution closure v0.1
- root cause:
  - `minimize_and_reseed`는 직전 slice에서 plan/orchestration/dispatch artifact까지는 닫혔지만, 실제 loop는 여전히 "좋은 문서"에서 멈췄다.
  - duplicate replay evidence로 latest crash artifact를 triage/regression/known-bad로 보존하고, 그 copy가 같은 crash family를 유지하는지 재생산 확인하는 bounded execution artifact가 없었다.
  - 그래서 true north 관점에서 `artifact preservation -> trigger/replay -> reseed planning`은 있었지만, `reseed planning -> 실제 corpus sync -> replay-retention evidence` closure가 비어 있었다.
- 이번에 고친 것:
  - `scripts/hermes_watch.py`
    - `execute_corpus_refinement_probe(...)` 추가
    - `minimize_and_reseed` entry가 latest artifact를 `fuzz/corpus/triage`, `fuzz/corpus/regression`, `fuzz/corpus/known-bad`에 안전하게 copy하고 SHA1 lineage를 남기도록 확장
    - regression bucket copy를 standalone harness로 bounded replay해서 retention signature/exit/log를 남기도록 추가
    - 결과를 `fuzz-records/corpus-refinement-executions/*.json|md|log`로 기록하고 entry/plan에도 execution section을 노출
    - empty artifact path가 `Path('.')`로 오해되는 latent bug를 막기 위해 optional path handling 보강
    - `execute_next_refiner_action(...)`가 `minimize_and_reseed`에서 위 execution helper를 실제 호출하도록 연결
  - `tests/test_hermes_watch.py`
    - corpus refinement execution regression test 추가
    - execute-next-refiner lineage/plan section regression test 추가
- 검증:
  - RED:
    - `pytest -q tests/test_hermes_watch.py -k 'execute_corpus_refinement_probe_copies_seed_and_verifies_replay_retention or execute_next_refiner_action_records_corpus_refinement_execution_lineage'` → 초기 2 fail (`execute_corpus_refinement_probe` 부재)
  - GREEN:
    - 같은 명령 재실행 → 2 pass
    - `pytest -q tests/test_hermes_watch.py -k 'minimize_and_reseed or corpus_refinement or duplicate_replay'` → 9 pass
    - `pytest -q` → 328 pass
  - live verification:
    - existing `corpus_refinements.json` entry에 대해 `execute_corpus_refinement_probe(...)` 실제 실행
    - 생성 산출물:
      - `fuzz-records/corpus-refinement-executions/home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_202702_1d5b676.json`
      - `fuzz-records/corpus-refinement-executions/home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_202702_1d5b676.md`
      - `fuzz-records/corpus-refinement-executions/home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_202702_1d5b676-retention-replay.log`
    - corpus sync 확인:
      - `fuzz/corpus/triage/crash-5e1dbfc1e1257014678913af52217fa8eb380818`
      - `fuzz/corpus/regression/crash-5e1dbfc1e1257014678913af52217fa8eb380818`
      - `fuzz/corpus/known-bad/crash-5e1dbfc1e1257014678913af52217fa8eb380818`
    - retention replay 결과:
      - exit code `-6`
      - fingerprint `asan|j2kmarkers.cpp:52|heap-buffer-overflow ...`
      - copied regression seed에서도 same crash family 유지 확인
- 의미:
  - duplicate replay evidence가 이제 그냥 "다음에 할 일 문서"가 아니라 실제 corpus buckets와 replay evidence로 내려간다.
  - `artifact preservation -> trigger/replay -> reseed execution -> retention verification` 고리가 처음으로 bounded하게 닫혔다.
  - duplicate family를 coverage/growth loop에서 계속 맹목 재발견하는 문제를 줄이는 실제 입력이 생겼다.
- 한계:
  - 아직 crash minimization 자체는 없다.
  - reseed 뒤 coverage 효율이 실제로 올라가는지는 아직 측정 안 했다.
  - medium duplicate family(`coding_units.cpp:3076`)를 같은 rail로 올릴지 규칙은 아직 별도다.
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-replay-derived-corpus-refinement-execution-closure-v0.1-note.md`
  - `checklists/2026-04-16-hermes-watch-replay-derived-corpus-refinement-execution-closure-v0.1-checklist.md`

### Replay-derived corpus refinement plan closure v0.1
- root cause:
  - `corpus_refinements.json`에는 stable duplicate replay(`j2kmarkers.cpp:52`)에서 파생된 `minimize_and_reseed` entry가 이미 recorded 상태로 쌓여 있었지만, 실제 refiner executor/plan surface는 거의 generic placeholder 수준이었다.
  - 그래서 duplicate replay review rail에서 rich하게 모은 first/latest artifact, replay markdown, stable signature 정보가 reseed 단계로 내려오면서 다시 얇아졌고, fresh session runner가 왜 이 reseed를 해야 하는지 이해하기 어려웠다.
  - 즉 `artifact preservation -> trigger/replay -> revision queue`는 있었지만, `revision queue -> self-contained execution artifact` closure가 corpus refinement rail에서는 약했다.
- 이번에 고친 것:
  - `scripts/hermes_watch.py`
    - `_refiner_corpus_refinement_plan_sections(repo_root, entry)` 추가
    - `minimize_and_reseed` plan이 duplicate replay source key, crash fingerprint/location/summary, occurrence count, first/latest artifact, replay markdown/harness path를 자동 노출하도록 확장
    - low-risk command draft(`mkdir -p`, latest artifact `cp -n`, first/latest `sha1sum` / `cmp -l`, replay markdown preview) 자동 생성 추가
    - `_refiner_extra_context_lines(...)`도 `minimize_and_reseed`를 이해하도록 확장해 cron/subagent prompt에 같은 duplicate replay context가 실리도록 변경
    - `_refiner_extra_plan_sections(...)`가 `repo_root`를 받아 실제 corpus bucket 경로를 기준으로 command draft를 쓰도록 변경
  - `tests/test_hermes_watch.py`
    - duplicate replay-derived corpus refinement plan section regression test 추가
    - corpus refinement orchestration prompt가 duplicate replay context를 포함하는지 regression test 추가
- 검증:
  - RED:
    - `pytest -q tests/test_hermes_watch.py -k 'duplicate_replay_derived_corpus_refinement_plan or includes_duplicate_replay_context_for_corpus_refinement'` → 초기 2 fail
  - GREEN:
    - 같은 명령 재실행 → 2 pass
    - `pytest -q tests/test_hermes_watch.py -k 'minimize_and_reseed or corpus_refinement or prepare_next_refiner_orchestration or execute_next_refiner_action'` → 18 pass
    - `pytest -q` → 326 pass
  - live verification:
    - `prepare_next_refiner_orchestration(...)`로 pending `minimize_and_reseed` entry 실제 consume
    - `dispatch_next_refiner_orchestration(...)`로 cron request draft 생성
    - 생성 산출물 확인:
      - `fuzz-records/refiner-plans/minimize_and_reseed-home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_202702_1d5b676.md`
      - `fuzz-records/refiner-orchestration/minimize_and_reseed-home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_202702_1d5b676-cron.txt`
      - `fuzz-records/refiner-dispatch/minimize_and_reseed-home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_202702_1d5b676-cronjob-request.json`
    - `corpus_refinements.json` entry가 `status=completed`, `orchestration_status=prepared`, `dispatch_status=ready`, `lifecycle=dispatch_ready`로 올라간 것 확인
- 의미:
  - duplicate replay evidence가 이제 review 단계에서만 rich하고 reseed 단계에서 다시 얇아지는 문제가 줄었다.
  - true north 기준으로 `artifact preservation -> trigger/replay -> reseed planning artifact` 고리가 corpus refinement rail에서도 실제로 닫히기 시작했다.
  - 아직 minimization을 자동 실행하지는 않지만, 적어도 fresh session이 바로 읽을 수 있는 self-contained plan/prompt/request가 생겼다.
- 한계:
  - minimization 자체 실행과 replay-retention 검증은 아직 없다.
  - `cp -n` command는 draft일 뿐이며, 실제 실행/rollback policy는 다음 단계다.
  - current latest medium duplicate family(`coding_units.cpp:3076`)는 별도 문제로 남아 있다.
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-replay-derived-corpus-refinement-plan-closure-v0.1-note.md`
  - `checklists/2026-04-16-hermes-watch-replay-derived-corpus-refinement-plan-closure-v0.1-checklist.md`

### Duplicate replay follow-up routing v0.1
- root cause:
  - `review_duplicate_crash_replay` rail은 이제 bounded replay evidence까지는 남기지만, replay 결과가 다음 revision routing으로 직접 이어지지 않았다.
  - 그래서 stable duplicate family라도 compare markdown만 늘고 실제 next safe slice는 다시 사람이 골라야 했다.
  - 특히 `j2kmarkers.cpp:52` family는 first/latest replay가 같은 signature로 안정 재현됐는데도 minimize/reseed queue로 승격되지 않아 동일 family 재발견을 줄이는 closure가 비어 있었다.
- 이번에 고친 것:
  - `scripts/hermes_watch.py`
    - `build_duplicate_replay_followup_entry(...)` 추가
    - stable duplicate replay(`completed`, nonzero exit, distinct artifact bytes, same replay signature/location)면 `minimize_and_reseed` follow-up entry를 만들도록 추가
    - `record_duplicate_replay_followup(...)` 추가
    - `execute_next_refiner_action(...)`가 duplicate replay execution 직후 corpus refinement queue에 follow-up을 실제 기록하고 source entry에 `replay_followup_*` lineage를 남기도록 확장
  - `scripts/hermes_watch_support/llm_evidence.py`
    - `_duplicate_replay_routing_override(...)` 추가
    - current status가 duplicate replay review일 때 stable replay evidence가 있으면 `suggested_action_code = minimize_and_reseed`, `suggested_candidate_route = reseed-before-retry`로 override
  - live registry update:
    - existing `j2kmarkers.cpp:52` duplicate replay review entry에서
    - `fuzz-artifacts/automation/corpus_refinements.json`에 replay-derived `minimize_and_reseed` entry 실제 기록
- 검증:
  - RED:
    - `pytest -q tests/test_hermes_watch.py -k 'duplicate_crash_replay_followup or duplicate_crash_review_context or records_duplicate_replay_followup_corpus_refinement'` → 초기 2 fail
  - GREEN:
    - 같은 명령 재실행 → 3 pass
    - `pytest -q tests/test_hermes_watch.py -k 'duplicate_crash or llm_evidence or minimize_and_reseed'` → 36 pass
    - `pytest -q` → 324 pass
  - live verification:
    - `corpus_refinements.json`에 `minimize_and_reseed:duplicate-replay:asan|j2kmarkers.cpp:52|...` entry 생성 확인
    - entry에 replay markdown/json path, first/latest exit/signature, source duplicate review key가 같이 남는 것 확인
- 의미:
  - duplicate replay rail이 이제 compare/replay evidence에서 멈추지 않고 실제 revision queue로 한 칸 더 내려간다.
  - true north 기준으로 `artifact preservation -> trigger/review -> rerun evidence -> next revision routing` 고리의 마지막 빈칸을 안전한 queue artifact 수준에서 메웠다.
  - 동일 crash family 재발견을 줄이기 위한 low-risk minimize/reseed planning 입력이 처음으로 자동 생성되기 시작했다.
- 한계:
  - 아직 minimization 자체를 실행하지는 않는다.
  - latest `current_status`는 `coding_units.cpp:3076` medium duplicate라 이번 routing override가 곧바로 현재 packet top-level action을 바꾸지는 않는다.
  - medium duplicate family를 replay review rail로 올릴지 여부는 아직 별도 slice다.
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-duplicate-replay-followup-routing-v0.1-note.md`
  - `checklists/2026-04-16-hermes-watch-duplicate-replay-followup-routing-v0.1-checklist.md`

### Duplicate replay execution closure v0.1
- root cause:
  - `review_duplicate_crash_replay` rail은 registry/plan/lineage는 있었지만 actual bounded replay execution evidence는 없었다.
  - 그래서 duplicate family review가 compare-only 문서 단계에 머물렀고, first/latest artifact를 실제 같은 harness로 돌렸을 때의 exit/signature/stability가 canonical artifact로 남지 않았다.
  - 추가 live replay에서 offline helper가 `symbolize=0`를 유지해 `unknown-location` signature가 나오는 것도 확인됐다.
- 이번에 고친 것:
  - `scripts/hermes_watch.py`
    - `execute_duplicate_crash_replay_probe(...)` 추가
    - duplicate review first/latest artifact replay JSON/Markdown/log artifact 생성
    - registry entry에 `replay_execution_status`, `first/latest_replay_exit_code`, `first/latest_replay_signature`, log/path/equality 필드 저장
    - `execute_next_refiner_action(...)`가 duplicate review action이면 replay execution을 실제 수행하고 최신 plan에 반영
    - `run_duplicate_crash_replay_command(...)`에서 offline replay를 `symbolize=1` + `ASAN_SYMBOLIZER_PATH`로 실행하도록 수정
    - duplicate review plan에 `## Replay Execution` section 추가
  - `scripts/hermes_watch_support/llm_evidence.py`
    - duplicate review markdown section에 replay execution status/path/exit code 노출
  - `tests/test_hermes_watch.py`
    - replay execution artifact write regression test 추가
    - executor summary/plan 반영 regression test 추가
    - symbolized replay env regression test 추가
- 검증:
  - RED:
    - `pytest -q tests/test_hermes_watch.py -k 'duplicate_crash_replay_probe_writes_execution_artifacts or duplicate_crash_replay_execution_summary'` → 초기 2 fail
    - `pytest -q tests/test_hermes_watch.py -k 'run_duplicate_crash_replay_command_enables_symbolized_replay'` → 초기 1 fail (`symbolize=0` 유지)
  - GREEN:
    - `pytest -q tests/test_hermes_watch.py -k 'duplicate_crash_review_context or duplicate_crash_replay_probe_writes_execution_artifacts or duplicate_crash_replay_execution_summary or run_duplicate_crash_replay_command_enables_symbolized_replay'` → 4 pass
    - `pytest -q tests/test_hermes_watch.py -k 'duplicate_crash or llm_evidence'` → 34 pass
    - `pytest -q` → 322 pass
  - live verification:
    - existing duplicate review entry 재실행으로
      - `fuzz-records/duplicate-crash-replays/home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_202702_1d5b676.{json,md}` 생성
      - updated plan에 replay execution section 반영
      - first/latest replay exit code `-6` 확인
      - first/latest replay signature가 둘 다 `asan|j2kmarkers.cpp:52|heap-buffer-overflow ...`로 file:line 포함 상태로 복구된 것 확인
- 의미:
  - duplicate review rail이 이제 compare-only planning이 아니라 bounded rerun evidence를 남기는 실제 triage closure 초입이 됐다.
  - symbolized offline replay까지 복구해 duplicate family의 canonical signature 품질도 같이 올렸다.
  - true north 기준으로 `artifact preservation -> trigger/review -> rerun evidence` 고리를 한 칸 더 실제로 닫은 단계다.
- 한계:
  - minimization은 아직 없다.
  - replay 결과를 자동으로 seed/harness/strategy revision objective로 바꾸는 정책은 아직 없다.
  - latest current status는 여전히 별도 duplicate family(`coding_units.cpp:3076`)를 가리킨다.
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-duplicate-replay-execution-closure-v0.1-note.md`
  - `checklists/2026-04-16-hermes-watch-duplicate-replay-execution-closure-v0.1-checklist.md`

### LLM evidence sync and duplicate review rehydration v0.1
- root cause:
  - 최신 `current_status.json`는 이미 duplicate crash를 가리키는데 `fuzz-records/llm-evidence/openhtj2k-llm-evidence.json`는 예전 smoke-failed snapshot에 멈춰 있었다.
  - 즉 watcher는 최신 crash를 기록하지만 LLM handoff packet은 stale해서 `artifact preservation -> trigger -> LLM-guided revision` 연결이 끊겨 있었다.
  - 추가 live rerun에서 `duplicate_crash_reviews.json`도 create-only라 existing duplicate family recurrence를 최신 `run_dir/report/artifact/occurrence_count`로 갱신하지 못한다는 점이 드러났다.
- 이번에 고친 것:
  - `scripts/hermes_watch.py`
    - `refresh_llm_evidence_packet_best_effort(repo_root)` 추가
    - build-failed / smoke-failed / final run 종료 경로에서 report/status write 뒤 LLM evidence packet 자동 refresh
    - `record_refiner_entry(..., merge_existing=True)` + `_merge_refiner_entry(...)` 추가
    - `review_duplicate_crash_replay` registry 경로가 existing entry를 refresh할 수 있게 변경
  - `scripts/hermes_watch_support/llm_evidence.py`
    - latest `duplicate_crash_reviews.json`에서 matching entry lookup 추가
    - packet에 `duplicate_crash_review` payload 포함
    - markdown에 `## Duplicate Crash Review` section 추가
    - `suggested_next_inputs`에 `duplicate crash review plan and lineage`를 조건부 추가
  - `tests/test_hermes_watch.py`
    - duplicate review context packet surface regression test 추가
    - build failure 종료 후 llm evidence auto-write regression test 추가
    - existing duplicate review entry refresh regression test 추가
- 검증:
  - RED:
    - `pytest -q tests/test_hermes_watch.py -k 'duplicate_crash_review_context or writes_llm_evidence_packet_automatically'` → 초기 2 fail
    - `pytest -q tests/test_hermes_watch.py -k 'refreshes_existing_duplicate_crash_review_entry'` → 초기 1 fail
  - GREEN:
    - `pytest -q tests/test_hermes_watch.py -k 'duplicate_crash_review_context or writes_llm_evidence_packet_automatically or refreshes_existing_duplicate_crash_review_entry'` → 3 pass
    - `pytest -q tests/test_hermes_watch.py -k 'duplicate_crash or llm_evidence'` → 31 pass
    - `pytest -q` → 317 pass
  - live verification:
    - `python scripts/hermes_watch.py --repo /home/hermes/work/fuzzing-jpeg2000 --max-total-time 5 --no-progress-seconds 30`
    - latest rerun 뒤 `openhtj2k-llm-evidence.json`의 `current_status.updated_at`가 최신 run과 자동 동기화되는 것 확인
    - duplicate review action일 때 packet에 `duplicate_crash_review` context가 자동 포함되는 것 확인
- 의미:
  - 이제 latest run이 끝나면 LLM이 stale packet을 읽는 문제를 기본적으로 줄였다.
  - duplicate review rail도 한 번 만들어진 뒤 낡아지는 create-only registry가 아니라 recurrence를 따라가는 evidence memory가 되기 시작했다.
  - true north 기준으로 `artifact preservation -> trigger/review -> LLM-guided next step` 사이의 canonical handoff 품질을 직접 올린 단계다.
- 한계:
  - duplicate review는 아직 plan/lineage surface까지만 닫혔고 실제 replay/minimization 실행 결과 수집은 아니다.
  - 새로운 recurrence가 old completed plan path를 그대로 가리킬 수 있어, 다음 slice에서는 replay 실행 artifact와 plan refresh를 더 직접 연결해야 한다.
  - remote/proxmox closure는 아직 별도다.
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-llm-evidence-sync-and-duplicate-review-rehydration-v0.1-note.md`
  - `checklists/2026-04-16-hermes-watch-llm-evidence-sync-and-duplicate-review-rehydration-v0.1-checklist.md`

### Duplicate crash compare plan enrichment v0.1
- root cause:
  - `review_duplicate_crash_replay` policy와 registry는 이미 있었지만, 실제 refiner plan은 run/report/recommended action 몇 줄만 있는 얇은 문서였다.
  - 그래서 duplicate deep crash family를 review rail로 보낸 뒤에도 first-seen vs latest 비교축, artifact lineage, bounded compare command가 비어 있어 triage 착수 입력 품질이 약했다.
  - 즉 rail은 있었지만 operator/LLM이 바로 쓸 수 있는 evidence-aware compare surface가 부족했다.
- 이번에 고친 것:
  - `scripts/hermes_watch.py`
    - crash index update/repair 반환 payload에 `first_seen_report`, `last_seen_report`, `first_artifact_path`, `artifacts` 추가
    - `apply_policy_action(...)`의 duplicate review registry entry에 `first_seen_report_path`, `last_seen_run`, `first_artifact_path`, `artifact_paths` 추가
    - `write_refiner_plan(...)`가 duplicate review action에서 `## Duplicate Crash Comparison` + `## Suggested Low-Risk Commands`를 자동 생성
    - subagent/cron prompt도 duplicate review context를 더 풍부하게 받도록 보강
  - `tests/test_hermes_watch.py`
    - duplicate review registry lineage 보강 regression test 추가
    - duplicate review refiner plan이 compare section과 bounded command를 실제로 쓰는지 검증 추가
- 검증:
  - RED: `pytest -q tests/test_hermes_watch.py -k 'duplicate_crash_compare_and_replay_plan or routes_duplicate_crash_replay_review_into_refiner_queue'` → 초기 1 fail (`## Duplicate Crash Comparison` 부재)
  - GREEN: 같은 명령 재실행 → 2 pass
  - 추가 회귀: `pytest -q tests/test_hermes_watch.py -k 'duplicate_crash or review_duplicate_crash_replay or execute_next_refiner_action_processes_review_duplicate_crash_replay'` → 6 pass
  - `pytest -q` → 312 pass
  - live artifact refresh:
    - `duplicate_crash_reviews.json` existing entry를 crash index lineage로 보강
    - `fuzz-records/refiner-plans/review_duplicate_crash_replay-home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_202702_1d5b676.md` 재생성
    - first/latest run/report/artifact와 `sha1sum` / `cmp -l ... || true` compare command가 실제로 plan에 들어간 것 확인
- 의미:
  - duplicate deep crash review rail이 이제 빈 plan stub이 아니라 실제 triage 착수 입력으로 조금 더 쓸 만해졌다.
  - true north 기준으로 `artifact preservation -> review trigger` 사이에서 빠져 있던 compare/lineage surface를 메웠다.
  - 아직 actual replay/minimization 실행 자동화는 아니지만, 그 전 단계의 입력 품질 병목을 안전하게 줄였다.
- 한계:
  - 실제 triage mode replay/minimization 실행 결과를 아직 자동 수집하지 않는다.
  - compare summary는 metadata/command 중심이며 semantic diff 해설까지는 아니다.
  - remote/proxmox closure와는 아직 직접 연결되지 않았다.
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-duplicate-crash-compare-plan-enrichment-v0.1-note.md`
  - `checklists/2026-04-16-hermes-watch-duplicate-crash-compare-plan-enrichment-v0.1-checklist.md`

### Duplicate deep crash replay review routing v0.1
- root cause:
  - `continue_and_prioritize_triage`까지는 새 deep critical crash family를 triage rail로 보낼 수 있었지만, 같은 family가 다시 나오면 곧바로 `record-duplicate-crash`로 내려가 버렸다.
  - 그래서 repeated deep duplicate는 artifact는 쌓여도 `first_seen vs latest` 비교, replay/minimization triage, LLM review rail로 이어지는 입력이 없었다.
  - 지금 같은 `j2kmarkers.cpp:52` family recurrence는 "이미 본 크래시"이기도 하지만 동시에 "반복 재현되는 deep critical family"이기도 하다.
- 이번에 고친 것:
  - `scripts/hermes_watch.py`
    - duplicate crash policy에서 `occurrence_count >= 2` + `crash_stage_class = deep`면 `review_duplicate_crash_replay`로 승격
    - action contract:
      - `priority = high`
      - `next_mode = triage`
      - `bucket = triage`
    - duplicate replay review action도 `known_bad.json`을 계속 갱신하도록 유지
    - `known_bad.json` entry에 `first_seen_run`, `last_seen_run`, `occurrence_count` 추가
    - 새 registry `duplicate_crash_reviews.json` 추가
    - refiner queue/orchestration spec에 `review_duplicate_crash_replay` 추가
  - `tests/test_hermes_watch.py`
    - repeated deep duplicate crash policy escalation regression test 추가
    - duplicate replay review action이 `known_bad` + `duplicate_crash_reviews`를 같이 갱신하는지 검증 추가
    - 새 registry가 refiner executor에서 실제 plan으로 소비되는지 검증 추가
- 검증:
  - RED: `pytest -q tests/test_hermes_watch.py -k 'replay_review or duplicate_crash_replay_review'` → 초기 3 fail
  - GREEN: 같은 명령 재실행 → 3 pass
  - `pytest -q tests/test_hermes_watch.py -k 'duplicate_crash or known_bad or execute_next_refiner_action'`
  - `pytest -q`
  - bounded rerun:
    - `python scripts/hermes_watch.py --repo /home/hermes/work/fuzzing-jpeg2000 --max-total-time 5 --no-progress-seconds 30`
    - latest run `20260416_202702_1d5b676`
    - `crash_occurrence_count = 3`
    - `policy_action_code = review_duplicate_crash_replay`
    - `duplicate_crash_reviews.json` entry 생성 확인
  - live refiner plan 생성:
    - `python - <<'PY' ... hermes_watch.execute_next_refiner_action(...) ... PY`
    - `fuzz-records/refiner-plans/review_duplicate_crash_replay-home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_202702_1d5b676.md`
- 의미:
  - duplicate deep critical family가 이제 단순 known-bad sink로 끝나지 않는다.
  - artifact preservation 뒤에 replay/minimization review용 별도 입력 rail이 생겨 LLM-guided triage closure 쪽으로 한 칸 더 전진했다.
  - true north 기준으로 `artifact -> trigger/review input -> LLM-guided next step` 중 duplicate family blind spot을 메웠다.
- 한계:
  - 아직 실제 triage mode replay/minimization 실행까지 자동으로 닫히지는 않았다.
  - first artifact와 latest artifact의 차이를 자동 비교하는 요약은 아직 없다.
  - remote/proxmox closure와는 아직 직접 연결되지 않았다.
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-duplicate-deep-crash-replay-review-routing-v0.1-note.md`
  - `checklists/2026-04-16-hermes-watch-duplicate-deep-crash-replay-review-routing-v0.1-checklist.md`

### Critical crash follow-up triage trigger v0.1
- root cause:
  - `continue_and_prioritize_triage` 같은 deep-stage critical crash policy는 계산됐지만, 실제 후속 trigger 대상은 build/smoke regression 계열만 포함돼 있었다.
  - 그래서 report에는 triage 우선이라고 적히는데, 실제 control-plane은 `run-fuzz-mode.sh triage`를 자동 호출하지 못했다.
  - trigger executor도 `regression` mode만 중복 실행 방지라 triage command를 넣어도 same-mode skip이 일반화되지 않았다.
- 이번에 고친 것:
  - `scripts/hermes_watch.py`
    - `should_trigger_regression(...)`에 `continue_and_prioritize_triage`, `high_priority_alert` 포함
    - `followup_trigger_command(...)` 추가: deep critical crash는 `triage`, build/smoke 계열은 기존 `regression`
    - follow-up priority에 crash triage lane 반영
    - trigger executor가 command target mode를 읽어 `skipped-already-in-<mode>`로 일반화
  - `tests/test_hermes_watch.py`
    - `continue_and_prioritize_triage` trigger 여부 regression test
    - triage command same-mode skip regression test
    - critical crash policy action이 triage trigger 기록 + auto-run까지 호출하는지 검증
- 검증:
  - RED: `pytest -q tests/test_hermes_watch.py -k 'continue_and_prioritize_triage or already_in_triage_mode_for_triage_command or critical_crash_triage_trigger'` → 초기 3 fail
  - GREEN: 같은 명령 재실행 → 3 pass
  - `pytest -q tests/test_hermes_watch.py`
  - `pytest -q`
  - temp sandbox에서 `apply_policy_action(...)` 호출 결과
    - `updated = [policy_log, regression_trigger, regression_auto_run]`
    - trigger command = `bash scripts/run-fuzz-mode.sh triage`
    - registry status = `completed`
  - bounded rerun: `python scripts/hermes_watch.py --repo /home/hermes/work/fuzzing-jpeg2000 --max-total-time 5 --no-progress-seconds 30`
    - latest run `20260416_201732_1d5b676`에서 `j2kmarkers.cpp:52` family 재재현
    - 이번 run은 duplicate라 `record-duplicate-crash`로 분기되어 triage trigger는 발생하지 않음
- 의미:
  - true north 기준으로 `artifact -> trigger -> rerun` 고리에서 빠져 있던 critical crash triage rail을 메웠다.
  - 이제 새 deep-stage family를 잡으면 policy summary에서 끝나지 않고 실제 triage mode follow-up까지 내려갈 수 있다.
- 한계:
  - live repo state에서는 이번 bounded rerun이 duplicate라 새 triage trigger artifact까지는 아직 직접 못 봤다.
  - duplicate crash에도 별도 replay/minimization lane이 필요한지는 아직 미결이다.
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-critical-crash-followup-triage-trigger-v0.1-note.md`
  - `checklists/2026-04-16-hermes-watch-critical-crash-followup-triage-trigger-v0.1-checklist.md`

### Policy-aware Recommended Next Action + bounded rerun v0.1
- root cause:
  - `Policy Action` section은 최신 policy/objective를 쓰는데 `## Recommended Next Action`만 outcome-only 하드코딩이라 report를 다 읽고 나면 다시 stale generic 행동으로 끝났다.
  - 그래서 rehydrate path를 고쳐도 fresh run path가 같은 행동 contract를 자연 생성하지 못하고 있었다.
- 이번에 고친 것:
  - `scripts/hermes_watch.py`
    - `recommended_action(...)`가 optional `policy_action`을 받아 `policy_recommended_action`를 우선 사용하도록 변경
    - `write_report(...)`와 `rewrite_rehydrated_report(...)`가 둘 다 같은 policy-aware action summary를 쓰도록 정렬
  - `tests/test_hermes_watch.py`
    - rehydrate stale report fixture에 old `Recommended Next Action` section을 넣고 교체되는지 검증
    - fresh `write_report(...)` 경로가 policy text를 말미 action summary로 쓰는 regression test 추가
- bounded rerun 검증:
  - `python scripts/hermes_watch.py --repo /home/hermes/work/fuzzing-jpeg2000 --max-total-time 5 --no-progress-seconds 30`
  - 새 run `20260416_200858_1d5b676`에서
    - `cov 42 -> 45`
    - `ft 121 -> 137`
    - corpus `3 -> 5`, `672b -> 1066b`
    - 새 crash family `asan|j2kmarkers.cpp:52|heap-buffer-overflow ... j2k_marker_io_base::get_byte()` 포착
    - `crash_stage = ht-block-decode`, `crash_stage_class = deep`, `depth_rank = 4`
    - `policy_action_code = continue_and_prioritize_triage`
    - `policy_matched_triggers = ['deep_signal_emergence']`
    - report 말미 action summary도 `Keep the run going but prioritize this new deep-stage crash family in triage.`로 자연 생성
- 의미:
  - report surface 전체가 policy spine으로 닫혔다.
  - stale leak repair이 fresh run contract 검증으로 이어졌고, 그 과정에서 실제 새 deep-stage crash family를 하나 더 얻었다.
  - 즉 이번 단계는 문구 수정이 아니라 real loop verification + new signal 확보다.
- 한계:
  - 새 `j2kmarkers.cpp:52` family 자체의 triage/closure는 아직 안 했다.
  - `llm_objective`는 `stage-reach-or-new-signal`로 갔지만, 다음 작업은 더 직접적으로 triage/replay/seed isolation 쪽이어야 한다.
- 검증:
  - `pytest -q tests/test_hermes_watch.py -k 'write_report_uses_policy_recommended_action_in_recommended_next_action_section or rehydrate_run_artifacts_reclassifies_stale_leak_metadata_without_duplicating_history'`
  - `pytest -q`
  - `python scripts/hermes_watch.py --repo /home/hermes/work/fuzzing-jpeg2000 --max-total-time 5 --no-progress-seconds 30`
  - `python scripts/hermes_watch.py --repo /home/hermes/work/fuzzing-jpeg2000 --write-llm-evidence-packet`
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-policy-aware-recommended-next-action-and-bounded-rerun-v0.1-note.md`
  - `checklists/2026-04-16-hermes-watch-policy-aware-recommended-next-action-and-bounded-rerun-v0.1-checklist.md`

### Rehydrated report sync v0.1
- root cause:
  - leak state rehydration v0.1 이후 `current_status.json` / `run_history.json` / `crash_index.json`는 leak-aware로 복구됐지만, operator가 가장 먼저 읽는 `FUZZING_REPORT.md`는 여전히 stale `artifact_category=crash`, `policy_action_code=triage-new-crash`, `crash_fingerprint=asan|unknown-location|...`를 유지했다.
  - 즉 canonical state와 report surface가 다른 이야기를 해서 artifact-first evidence spine이 다시 갈라졌다.
- 이번에 고친 것:
  - `scripts/hermes_watch.py`
    - `_replace_report_section(...)`, `rewrite_rehydrated_report(...)` 추가
    - `rehydrate_run_artifacts(...)`가 registry/state repair 뒤 report section까지 rewrite하도록 확장
    - 결과 JSON에 `report_rewritten` 추가
  - `tests/test_hermes_watch.py`
    - stale `FUZZING_REPORT.md` fixture를 포함한 regression test로 leak classification/policy/fingerprint/excerpt가 실제 report에서도 갱신되는지 검증
- 실제 latest run 적용 결과:
  - `fuzz-artifacts/runs/20260416_183444_1d5b676/FUZZING_REPORT.md`
    - `artifact_category = leak`
    - `policy_action_code = triage-leak-and-consider-coverage-policy`
    - `crash_kind = leak`
    - `crash_location = coding_units.cpp:3927`
    - `crash_stage = tile-part-load`
    - excerpt에 `LeakSanitizer` / artifact path / project frame 유지
  - CLI repair 결과:
    - `report_rewritten = true`
- 의미:
  - 이제 same run artifact를 어느 surface에서 열어도 leak cleanup 방향이 뒤틀리지 않는다.
  - canonical state만 맞고 report는 stale한 어정쩡한 상태를 정리했다.
- 한계:
  - leak 자체를 닫은 것은 아니다.
  - `Recommended Next Action`는 아직 generic crash 문구다.
  - 진짜 다음 검증은 bounded rerun으로 새 run이 처음부터 같은 leak-aware report/state를 자연 생성하는지 확인하는 것이다.
- 검증:
  - `pytest -q tests/test_hermes_watch.py -k rehydrate_run_artifacts_reclassifies_stale_leak_metadata_without_duplicating_history`
  - `pytest -q tests/test_hermes_watch.py -k 'rehydrate_run_artifacts or leak or LeakSanitizer or classify_artifact_event_prefers_leak_over_generic_crash or decide_policy_action_handles_leak or build_crash_signature'`
  - `pytest -q`
  - `python scripts/hermes_watch.py --repo /home/hermes/work/fuzzing-jpeg2000 --rehydrate-run-artifacts --rehydrate-run-dir /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_183444_1d5b676`
  - `python scripts/hermes_watch.py --repo /home/hermes/work/fuzzing-jpeg2000 --write-llm-evidence-packet`
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-rehydrated-report-sync-v0.1-note.md`
  - `checklists/2026-04-16-hermes-watch-rehydrated-report-sync-v0.1-checklist.md`

### Leak state rehydration v0.1
- 방금 적용한 `rehydrate_run_artifacts(...)` / `--rehydrate-run-artifacts` 경로는 이미 stale하게 써진 latest run의 canonical state를 `fuzz.log`에서 다시 읽어 복구한다.
- root cause:
  - leak signature capture hardening은 다음 run부터는 맞게 동작하지만, 이미 써진 `current_status.json`, `run_history.json`, `crash_index.json`는 여전히 `asan|unknown-location|...` stale 상태였다.
  - 그래서 evidence packet은 leak objective를 복구해도 control-plane canonical state와 history/index spine은 generic crash를 가리키는 불일치가 남아 있었다.
- 이번에 고친 것:
  - `scripts/hermes_watch.py`
    - `collect_metrics_from_log(...)`, `upsert_run_history_entry(...)`, `rehydrate_run_artifacts(...)` 추가
    - 기존 run의 `fuzz.log`를 다시 읽어 crash signature를 재구성하고 stale fingerprint record를 제거한 뒤 crash index를 재등록
    - matching `run_history.json` entry를 append가 아니라 replace로 수선
    - `current_status.json` / run `status.json` / policy classification을 leak 기준으로 다시 동기화
    - CLI entrypoint `--rehydrate-run-artifacts --rehydrate-run-dir <run_dir>` 추가
    - 기존 `--repair-latest-crash-state`도 깨지지 않게 유지
  - `tests/test_hermes_watch.py`
    - stale leak metadata가 history duplication 없이 leak fingerprint/category/policy로 복구되는 regression test 추가
- 실제 latest run repair 결과:
  - `current_status.json`:
    - `artifact_category = leak`
    - `crash_kind = leak`
    - `crash_location = coding_units.cpp:3927`
    - `policy_action_code = triage-leak-and-consider-coverage-policy`
  - `run_history.json` latest entry:
    - `leak|coding_units.cpp:3927|12312 byte(s) leaked in 1 allocation(s).`
  - `crash_index.json`:
    - stale `asan|unknown-location|...` 제거
    - canonical leak fingerprint record로 교체
  - `openhtj2k-llm-evidence.json`:
    - `llm_objective = cleanup-leak-closure`
    - `failure_reason_codes = [leak-sanitizer-signal, fuzz-log-memory-safety-signal]`
- 의미:
  - 이제 latest leak가 evidence packet에서만 leak로 보이는 게 아니라, 실제 control-plane canonical spine 전체가 leak-aware 상태로 정렬됐다.
  - 다음 rerun/triage/review routing이 stale generic crash history를 밟지 않게 됐다.
- 한계:
  - `FUZZING_REPORT.md` excerpt는 아직 예전 stale crash fingerprint를 그대로 들고 있다.
  - 이번 단계는 existing artifact registry rehydrate까지이며, 실제 next run에서 report/state가 모두 새 signature로 자연 생성되는지까지는 아직 확인하지 않았다.
- 검증:
  - `pytest -q tests/test_hermes_watch.py -k 'rehydrate_run_artifacts_reclassifies_stale_leak_metadata_without_duplicating_history or update_crash_index_marks_first_and_duplicate_occurrences'`
  - `pytest -q tests/test_hermes_watch.py -k 'leak or LeakSanitizer or classify_artifact_event_prefers_leak_over_generic_crash or decide_policy_action_handles_leak or rehydrate_run_artifacts or repair_latest_crash_state or build_crash_signature'`
  - `pytest -q`
  - `python scripts/hermes_watch.py --repo /home/hermes/work/fuzzing-jpeg2000 --rehydrate-run-artifacts --rehydrate-run-dir /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_183444_1d5b676`
  - `python scripts/hermes_watch.py --repo /home/hermes/work/fuzzing-jpeg2000 --write-llm-evidence-packet`
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-leak-state-rehydration-v0.1-note.md`
  - `checklists/2026-04-16-hermes-watch-leak-state-rehydration-v0.1-checklist.md`

### Leak signature capture hardening v0.1
- 최신 `fuzz-artifacts/runs/20260416_183444_1d5b676` leak를 다시 보면, evidence packet은 leak objective를 복구했지만 watcher 원본 signature는 여전히 `asan|unknown-location|...` 계열 stale 상태였다.
- root cause:
  - long leak stack에서 `SUMMARY` / `Test unit written to ...` line이 crash context cap에 밀릴 수 있었고
  - leak primary location 선택이 allocator/common helper frame(`utils.hpp:252`) 쪽으로 먼저 끌려갔다.
- 이번에 고친 것:
  - `hermes_watch.py`
    - crash context cap을 `CRASH_CONTEXT_LINE_LIMIT = 20`로 명시
    - `Direct leak of ...` line도 context에 유지
    - context가 가득 차도 아직 없는 `SUMMARY` / artifact line은 강제로 보존
    - leak primary location 선택 시 `posix_memalign`, `AlignedLargePool::alloc`, `source/core/common/` 같은 allocator/common frame을 건너뛰고 의미 있는 project frame을 우선 선택
  - `tests/test_hermes_watch.py`
    - long leak stack에서도 `coding_units.cpp:3927` + leak summary + artifact path가 같이 남아야 하는 regression test 추가
- 실제 최신 `fuzz.log` 재파싱 결과:
  - `kind = leak`
  - `location = coding_units.cpp:3927`
  - `summary = 12312 byte(s) leaked in 1 allocation(s).`
  - `artifact_path = .../crashes/leak-272a1b...`
  - `fingerprint = leak|coding_units.cpp:3927|12312 byte(s) leaked in 1 allocation(s).`
- 의미:
  - 이제 다음 watcher run부터 leak가 generic crash/unknown-location으로 흐려지지 않고, dedup/stage/policy가 deep-decode-side cleanup leak로 더 정확히 반응할 기반이 생겼다.
- 한계:
  - 이미 써진 `current_status.json`, `run_history.json`, `crash_index.json`는 자동 backfill되지 않았다.
  - 이번 단계는 **원본 signature 품질 복구**이고, 다음 단계는 stale registry repair 또는 bounded rerun 확인이다.
- 검증:
  - `pytest -q tests/test_hermes_watch.py -k 'preserve_leak_summary_artifact_and_deep_project_frame_when_allocator_frames_are_first'`
  - `pytest -q tests/test_hermes_watch.py -k 'leak or LeakSanitizer or classify_artifact_event_prefers_leak_over_generic_crash or decide_policy_action_handles_leak or build_llm_evidence_packet_v9_routes_leak_signal_to_reviewable_cleanup_objective'`
  - `pytest -q`
  - 최신 `fuzz.log` 재파싱으로 새 signature 확인
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-leak-signature-capture-hardening-v0.1-note.md`
  - `checklists/2026-04-16-hermes-watch-leak-signature-capture-hardening-v0.1-checklist.md`

### Leak closure evidence slice v0.1
- fresh deep-decode-v3 artifact가 실제로 LeakSanitizer leak였는데, watcher의 crash excerpt 수집이 `LeakSanitizer`/stack frame을 충분히 붙잡지 못해 `asan|unknown-location|...` 형태로 뭉개지고 있었다.
- 이번에 고친 것:
  - `hermes_watch.py`
    - crash excerpt regex에 `ERROR: LeakSanitizer` / `SUMMARY: LeakSanitizer` 추가
    - crash 시작 뒤 stack/location line도 excerpt에 붙여 leak signature가 source line을 잃지 않게 보강
  - `llm_evidence.py`
    - `LeakSanitizer`를 raw signal summary에 별도 라벨로 유지
    - stale `current_status`가 아직 `asan`으로 남아 있어도 `fuzz.log` body와 leak summary에서 leak reason을 복구
    - 새 reason/objective:
      - `leak-sanitizer-signal`
      - `cleanup-leak-closure`
- 결과:
  - 다음 실제 watcher run부터 leak가 generic crash가 아니라 leak로 더 정확히 잡힐 기반이 생겼다.
  - 이미 남아 있는 stale `current_status.json` 상태에서도 새 LLM evidence packet은 latest leak를 `cleanup-leak-closure` objective로 읽고 `halt_and_review_harness` / `review-current-candidate`로 route한다.
- 검증:
  - `pytest -q tests/test_hermes_watch.py`
  - `pytest -q`
  - `python scripts/hermes_watch.py --repo /home/hermes/work/fuzzing-jpeg2000 --write-llm-evidence-packet`
- 즉 이번 단계는 **fresh leak signal이 control-plane에서 crash noise로 사라지지 않고, cleanup/closure 중심 revision loop로 전달되게 만든 evidence repair 단계**다.
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-leak-closure-evidence-slice-v0.1-note.md`
  - `checklists/2026-04-16-hermes-watch-leak-closure-evidence-slice-v0.1-checklist.md`

### Autonomous supervisor loop v0.1
- periodic cron 근사치를 넘어서, self-contained prompt를 먹고 계속 도는 local long-running autonomous supervisor daemon을 실제로 만들고 띄웠다.
- `hermes_watch.py`에 추가:
  - `build_autonomous_supervisor_prompt(...)`
  - `write_autonomous_supervisor_bundle(...)`
  - CLI flags:
    - `--prepare-autonomous-supervisor`
    - `--autonomous-supervisor-sleep-seconds`
    - `--autonomous-supervisor-channel-id`
- 생성 artifact:
  - `fuzz-records/autonomous-supervisor/autonomous-dev-loop-prompt.txt`
  - `fuzz-records/autonomous-supervisor/autonomous-dev-loop.sh`
  - `fuzz-records/autonomous-supervisor/autonomous-dev-loop.log`
  - `fuzz-records/autonomous-supervisor/autonomous-dev-loop-status.json`
  - `fuzz-records/autonomous-supervisor/STOP`
- 실제 background process도 기동했다.
- 기존 cron fallback은 겹침 방지를 위해 pause했다.
- 즉 이번 단계는 **가끔 도는 배치에서, 계속 도는 self-prompt 실행 모델로 승격한 단계**다.
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-autonomous-supervisor-loop-v0.1-note.md`
  - `checklists/2026-04-16-hermes-watch-autonomous-supervisor-loop-v0.1-checklist.md`

### Smoke/profile alignment v0.1
- current target profile의 active deep-decode-v3 campaign과 watcher의 실제 smoke/fuzz runtime contract를 최소 정렬했다.
- `run-smoke.sh`가 이제 direct harness path를 받고, 기본 smoke baseline은 stable-valid seed인
  - `ds0_ht_12_b11.j2k`
  - `p0_11.j2k`
  로만 구성된다.
- 기본 smoke baseline에서 `p0_12.j2k`를 제거해 regression/triage seed가 smoke gate를 반복 오염시키는 문제를 줄였다.
- `openhtj2k-target-profile-v1.yaml`에 `target.adapter`를 추가해 watcher runtime이
  - build: `scripts/build-libfuzzer.sh`
  - smoke: `build-fuzz-libfuzzer/bin/open_htj2k_deep_decode_focus_v3_harness`
  - fuzz: `open_htj2k_deep_decode_focus_v3_fuzzer` + `fuzz/corpus-afl/deep-decode-v3`
  쪽으로 더 정렬되기 시작했다.
- 그 결과 fresh run이 더 이상 stale smoke-failed 반복에 갇히지 않고, deep-decode-v3 fuzzer 경로에서 `coding_units.cpp:3076` / `j2k_tile::add_tile_part` crash evidence를 다시 생산했다.
- 즉 이번 단계는 **LLM reasoning 개선이 아니라, watcher가 현재 intended campaign 경로로 실제 들어가게 만든 runtime alignment 단계**다.
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-smoke-profile-alignment-v0.1-note.md`
  - `checklists/2026-04-16-hermes-watch-smoke-profile-alignment-v0.1-checklist.md`

### Failure reason extraction v0.9
- evidence packet이 이제 top reason narrative와 finding-efficiency recommendation을 next action 방향까지 직접 연결한다.
- 새 packet 필드:
  - `suggested_action_code`
  - `suggested_candidate_route`
  - `objective_routing_linkage_summary`
- 현재 v0.9 linkage 예:
  - `deeper-stage-reach` + finding-efficiency weak signal → `shift_weight_to_deeper_harness` / `promote-next-depth`
  - `build-fix` → `halt_and_review_harness` / `review-current-candidate`
- markdown 상단도 이제 objective/routing linkage를 같이 노출한다.
- 즉 이번 단계는 **reason narrative를 읽는 데서 끝나지 않고, LLM이 다음 수정 방향을 action/route 수준으로 더 직접 받게 만든 단계**다.
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-failure-reason-extraction-v0.9-note.md`
  - `checklists/2026-04-16-hermes-watch-failure-reason-extraction-v0.9-checklist.md`

### Finding-efficiency-facing intelligence v0.1
- evidence packet이 이제 failure reason 목록만 보여주지 않고, finding quality 저하 신호를 별도 summary로 압축한다.
- 새 packet 필드:
  - `finding_efficiency_summary`
  - `finding_efficiency_recommendation`
- 현재 v0.1이 보는 신호:
  - coverage delta
  - corpus growth
  - shallow crash dominance / recurrence
  - repeated crash family
- markdown에도 `## Finding Efficiency` 블록이 추가됐다.
- 즉 이번 단계는 **run history를 단순 reason code 추출로만 끝내지 않고, 실제 finding quality 저하 신호를 LLM이 바로 읽기 쉬운 recommendation 형태로 올리기 시작한 단계**다.
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-finding-efficiency-facing-intelligence-v0.1-note.md`
  - `checklists/2026-04-16-hermes-watch-finding-efficiency-facing-intelligence-v0.1-checklist.md`

### Secondary-conflict severity/actionability v0.1
- recovery routing이 이제 secondary conflict를 `present` 하나로만 보지 않는다.
- 새 routing 필드:
  - `routing_secondary_conflict_severity`
  - `routing_secondary_conflict_actionability`
- 현재 보수 분기:
  - reviewable tension → `hold`
  - build-blocker류 severe tension 또는 conflict 다중화 → `abort`
- status도 이제 분리된다:
  - `override-from-secondary-conflict-hold`
  - `override-from-secondary-conflict-abort`
- 즉 이번 단계는 **secondary conflict를 보이거나 hold로만 꺾는 수준을 넘어, 최소한 reviewable conflict와 corrective-regeneration 급 conflict를 실제 routing에서 분리하기 시작한 단계**다.
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-secondary-conflict-severity-actionability-v0.1-note.md`
  - `checklists/2026-04-16-hermes-watch-secondary-conflict-severity-actionability-v0.1-checklist.md`

### Failure reason extraction v0.8
- top failure reason 3개를 이제 단순 code / explanation / causal chain 목록으로만 두지 않는다.
- 새 packet 필드:
  - `top_failure_reason_narrative_steps`
  - `top_failure_reason_narrative`
- narrative step은 현재 `primary` / `supporting` / `deferred` 역할로 압축된다.
- 각 step은
  - `role`
  - `code`
  - `narrative`
  - `explanation`
  - `causal_chain`
  를 가진다.
- markdown 상단도 이제 top failure reason narrative를 같이 노출한다.
- 즉 이번 단계는 **reason ordering과 causal chain을 넘어, 왜 이 reason들이 함께 보이는지 multi-reason narrative로 더 직접 읽히게 만든 단계**다.
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-failure-reason-extraction-v0.8-note.md`
  - `checklists/2026-04-16-hermes-watch-failure-reason-extraction-v0.8-checklist.md`

### Secondary-conflict-aware routing v0.1
- recovery routing이 이제 `failure_reason_hunk_secondary_conflict_*` lineage를 실제로 소비한다.
- 현재 보수 규칙:
  - base recovery decision이 `retry`
  - deferred secondary conflict status가 `present`
  - 그러면 retry를 그대로 밀지 않고 `hold`로 꺾는다.
- 새 routing lineage 필드:
  - `routing_secondary_conflict_status`
  - `routing_secondary_conflict_count`
  - `routing_secondary_conflict_reasons`
  - `routing_secondary_conflict_deferred_reason_codes`
- 위 필드는 recovery routing entry / route manifest / apply candidate manifest / apply result payload에 남는다.
- 즉 이번 단계는 **secondary tension을 보이게 하는 데서 끝나지 않고, retry recovery action을 더 보수적인 hold/risk 판단으로 실제 소비하기 시작한 단계**다.
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-secondary-conflict-aware-routing-v0.1-note.md`
  - `checklists/2026-04-16-hermes-watch-secondary-conflict-aware-routing-v0.1-checklist.md`

### Failure reason extraction v0.7
- `failure_reasons` 각 entry가 이제 `causal_chain`을 가진다.
- 새 packet 필드:
  - `top_failure_reason_chains`
- 현재 causal chain은 source/outcome/signal summary/reason code를 작은 화살표 체인으로 압축한다.
- markdown 상단도 이제 top failure reason chain을 같이 노출한다.
- 즉 이번 단계는 **top failure reason이 어떤 source/evidence/signal summary chain을 따라 올라왔는지 더 직접 읽히게 만든 단계**다.
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-failure-reason-extraction-v0.7-note.md`
  - `checklists/2026-04-16-hermes-watch-failure-reason-extraction-v0.7-checklist.md`

### Secondary-reason conflict surfacing v0.1
- primary/top reason 기준 hunk alignment는 유지하되, 뒤에 밀린 mapped secondary reason도 다시 본다.
- primary reason과는 aligned여도 deferred secondary reason이 현재 hunk intent와 충돌하면 그 tension을 artifact에 남긴다.
- 새 lineage 필드:
  - `failure_reason_hunk_secondary_conflict_status`
  - `failure_reason_hunk_secondary_conflict_count`
  - `failure_reason_hunk_secondary_conflict_reasons`
  - `failure_reason_hunk_deferred_reason_codes`
- 즉 이번 단계는 **multi-reason conflict를 푼 게 아니라, primary reason에 가려지던 secondary tension을 artifact에 보이게 만든 단계**다.
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-secondary-reason-conflict-surfacing-v0.1-note.md`
  - `checklists/2026-04-16-hermes-watch-secondary-reason-conflict-surfacing-v0.1-checklist.md`

### Failure reason extraction v0.6
- `failure_reasons` 각 entry가 이제 `explanation`을 가진다.
- 새 packet 필드:
  - `top_failure_reason_explanations`
- 현재 explanation은 body plane summary를 근거로 삼는 작은 template 기반이다.
  - `build_log_signal_summary`
  - `smoke_log_signal_summary`
  - `fuzz_log_signal_summary`
  - `probe_signal_summary`
  - `apply_signal_summary`
- markdown 상단도 이제 top reason explanation을 같이 노출한다.
- 즉 이번 단계는 **top failure reason code가 왜 올라왔는지, 어떤 body signal summary를 근거로 했는지 더 직접 읽히게 만든 단계**다.
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-failure-reason-extraction-v0.6-note.md`
  - `checklists/2026-04-16-hermes-watch-failure-reason-extraction-v0.6-checklist.md`

### Multi-reason hunk prioritization v0.1
- apply 단계의 failure reason hunk alignment가 이제 `failure_reason_codes`만 평평하게 보지 않고 `top_failure_reason_codes`를 함께 본다.
- mapped top reason이 있으면 그 첫 번째 reason을 primary basis로 사용한다.
- 새 lineage 필드:
  - `failure_reason_hunk_primary_reason_code`
  - `failure_reason_hunk_priority_basis`
- alignment reason 문구도 이제 `priority winner`를 드러낸다.
- 즉 이번 단계는 **packet 쪽 top reason ordering과 apply 쪽 hunk alignment priority를 최소한 같은 spine으로 맞추는 단계**다.
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-multi-reason-hunk-prioritization-v0.1-note.md`
  - `checklists/2026-04-16-hermes-watch-multi-reason-hunk-prioritization-v0.1-checklist.md`

### Failure reason extraction v0.5
- signal pickup 범위를 더 넓히기보다, 이미 읽는 body signal을 덜 noisy하게 압축하기 시작했다.
- raw signal collector가 이제 repeated line / repeated sanitizer class를 더 줄인다.
- `raw_signal_summary`에 plane별 압축 필드 추가:
  - `smoke_log_signal_summary`
  - `build_log_signal_summary`
  - `fuzz_log_signal_summary`
  - `probe_signal_summary`
  - `apply_signal_summary`
  - `body_signal_priority`
- failure reasons도 이제 더 operator-friendly한 우선순위로 재정렬된다.
- 새 packet 필드:
  - `top_failure_reason_codes`
- 즉 이번 단계는 **signal collector를 더 넓힌 게 아니라, evidence packet을 덜 시끄럽고 더 우선순위 있게 정리하도록 만든 단계**다.
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-failure-reason-extraction-v0.5-note.md`
  - `checklists/2026-04-16-hermes-watch-failure-reason-extraction-v0.5-checklist.md`

### Failure-reason-to-hunk mapping v0.1
- apply 단계가 이제 `changed_hunk_added_lines_preview`를 바탕으로 실제 hunk intent를 작게 분류한다.
  - `comment-only`
  - `guard-only`
  - `build-fix`
  - `no-change`
  - `unknown`
- 새 검증/lineage 필드:
  - `failure_reason_hunk_alignment_verified`
  - `failure_reason_hunk_alignment_summary`
  - `failure_reason_hunk_alignment_reasons`
  - `failure_reason_hunk_intent`
- 현재 최소 mapping 규칙:
  - `smoke-log-memory-safety-signal`
  - `smoke-invalid-or-harness-mismatch`
  - `harness-probe-memory-safety-signal`
  - `fuzz-log-memory-safety-signal`
    - `guard-only` hunk 기대
  - `build-blocker`
    - `build-fix` hunk 기대
- 즉 이번 단계는 summary와 hunk preview mismatch를 넘어서, **현재 failure reason이 기대하는 수정 방향과 실제 changed hunk intent가 맞는지**까지 보기 시작한 것이다.
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-failure-reason-to-hunk-mapping-v0.1-note.md`
  - `checklists/2026-04-16-hermes-watch-failure-reason-to-hunk-mapping-v0.1-checklist.md`

### Hunk-intent-aware diff validation v0.1
- apply 단계가 이제 실제 added hunk line preview를 남긴다.
  - `changed_hunk_added_lines_preview`
- 새 검증 필드:
  - `delegate_hunk_intent_alignment_verified`
- 현재 heuristic은 작지만, mutation shape보다 한 단계 더 실제 changed line에 가깝다.
  - comment-only apply면 added line preview에 Hermes comment line이 보여야 하고 summary도 comment/note류여야 함
  - guard-only apply면 added line preview에 `if (size ...)` / `return ...`류가 보여야 하고 summary도 guard/size/input류여야 함
- 즉 이번 단계는 mutation shape 수준을 넘어, **실제 추가된 hunk line preview와 Patch Summary가 맞는지**까지 보기 시작한 것이다.
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-hunk-intent-aware-diff-validation-v0.1-note.md`
  - `checklists/2026-04-16-hermes-watch-hunk-intent-aware-diff-validation-v0.1-checklist.md`

### Diff-aware evidence-to-patch validation v0.1
- apply 단계가 이제 `original_content` / `patched_content`를 기준으로 실제 mutation shape를 계산한다.
  - `comment-only`
  - `guard-only`
- 새 apply/result lineage 필드:
  - `delegate_diff_alignment_verified`
  - `actual_mutation_shape`
- 현재 heuristic은 작지만 실제 diff-aware하다.
  - comment-only apply였는데 delegate patch summary가 `size guard`류면 alignment false
  - guard-only apply였는데 summary가 `guard`/`size`/`input`류면 alignment true
- 즉 이번 단계는 artifact summary/evidence alignment에서 한 걸음 더 나아가, **실제 적용된 mutation shape와 summary가 맞는지**까지 보기 시작한 것이다.
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-diff-aware-evidence-to-patch-validation-v0.1-note.md`
  - `checklists/2026-04-16-hermes-watch-diff-aware-evidence-to-patch-validation-v0.1-checklist.md`

### Evidence-faithful patch validation v0.1
- `verify_delegate_entry(...)`가 이제 Evidence Response 존재 여부를 넘어서 `Patch Summary`와 `response_summary`의 정합성도 본다.
- 새 검증/lineage 필드:
  - `delegate_artifact_patch_alignment_verified`
  - `delegate_reported_patch_summary`
  - `delegate_reported_response_summary`
- 현재 heuristic은 작지만 명확하다.
  - `Patch Summary`와 `response_summary` 사이에 최소 token overlap이 있어야 함
  - objective와 정면으로 충돌하는 patch summary를 막기 시작함
    - 예: `deeper-stage-reach`인데 build script rewrite / persistent mode 제안
- verification/apply/result artifact도 이 필드를 다시 남겨서, 이제 output contract가 단순 형식 충족인지 아니면 patch intent까지 evidence와 맞물렸는지 더 직접 추적 가능하다.
- 즉 이번 단계는 **evidence-aware form enforcement**에서 한 걸음 더 나아가, 최소한의 **evidence-to-patch alignment check**를 넣은 것이다.
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-evidence-faithful-patch-validation-v0.1-note.md`
  - `checklists/2026-04-16-hermes-watch-evidence-faithful-patch-validation-v0.1-checklist.md`

### Evidence-aware output schema tightening v0.1
- guarded apply delegate request가 이제 artifact 안에 `## Evidence Response` section을 명시적으로 요구한다.
  - `llm_objective:`
  - `failure_reason_codes:`
- bridge arm 단계가 apply candidate manifest에 기본 expected/quality section으로 `## Evidence Response`를 함께 심는다.
- `verify_delegate_entry(...)`가 이제 delegate artifact의 evidence response를 따로 파싱/검증한다.
  - `delegate_artifact_evidence_response_verified`
  - `delegate_reported_llm_objective`
  - `delegate_reported_failure_reason_codes`
- verification/apply/result artifact도 위 필드를 다시 남겨서, 이제 output schema가 input evidence에 실제로 답했는지 artifact로 추적 가능하다.
- 즉 이번 단계는 **더 많은 signal 수집**이 아니라, 이미 모은 evidence에 delegate output이 직접 답하도록 contract를 조이는 단계였다.
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-evidence-aware-output-schema-tightening-v0.1-note.md`
  - `checklists/2026-04-16-hermes-watch-evidence-aware-output-schema-tightening-v0.1-checklist.md`

### Failure reason extraction v0.4
- `raw_signal_summary`가 이제 smoke-only를 넘어 다음 body-level signal까지 함께 요약한다.
  - `build.log`
  - `fuzz.log`
  - latest `harness-probe`의 build/smoke probe output
  - latest `harness-apply-result`의 semantics / verification summary 본문
- 새 reason codes:
  - `build-log-memory-safety-signal`
  - `fuzz-log-memory-safety-signal`
  - `harness-probe-memory-safety-signal`
  - `apply-comment-scope-mismatch-signal`
- probe/apply signal count도 packet과 markdown에 직접 남긴다.
  - `probe_signal_count`
  - `probe_signals`
  - `apply_signal_count`
  - `apply_signals`
- 실제 현재 repo에서는 아직 smoke log signal만 살아 있고 build/fuzz/probe/apply 쪽 실데이터는 비어 있어 새 reason이 추가로 발화되진 않았다.
- 즉 이번 단계는 **semantic analyzer 완성**이 아니라, packet이 다음 증거면을 더 넓게 주워오도록 만든 body-signal 확장이다.
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-failure-reason-extraction-v0.4-note.md`
  - `checklists/2026-04-16-hermes-watch-failure-reason-extraction-v0.4-checklist.md`

### Delegate verification / apply policy evidence-aware lineage v0.1
- `verify_harness_apply_candidate_result(...)`가 이제 manifest에 있던 evidence 핵심 필드를 verification 결과와 함께 다시 유지/반환
  - `llm_objective`
  - `failure_reason_codes`
  - `raw_signal_summary`
- `apply_verified_harness_patch_candidate(...)`도 blocked/applied result payload와 manifest/result artifact에 같은 evidence lineage를 함께 기록
- 즉 `LLM input evidence -> verification/apply/result lineage`가 처음으로 끊기지 않고 이어지기 시작
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-delegate-verification-apply-policy-evidence-aware-lineage-v0.1-note.md`
  - `checklists/2026-04-16-hermes-watch-delegate-verification-apply-policy-evidence-aware-lineage-v0.1-checklist.md`

### Failure reason extraction v0.3
- `current_status.report` 기준 sibling `smoke.log` / `build.log` / `fuzz.log`를 읽어 raw signal summary를 evidence packet에 포함
- 새 reason code:
  - `smoke-log-memory-safety-signal`
- evidence packet에 `raw_signal_summary` 추가
  - `smoke_log_path`
  - `smoke_log_signals`
  - `*_signal_count`
- 실제 repo smoke log에서 UBSan/runtime error body를 packet reason으로 끌어오는 것 확인
- `python scripts/hermes_watch.py ...` direct entrypoint가 `ModuleNotFoundError: scripts` 없이 실행되도록 import-path bootstrap 추가
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-failure-reason-extraction-v0.3-note.md`
  - `checklists/2026-04-16-hermes-watch-failure-reason-extraction-v0.3-checklist.md`

### LLM handoff prompt simplification v0.1
- `write_harness_apply_candidate(...)`가 delegate request를 만들기 전에 latest LLM evidence packet을 생성/주입
- delegate request context에 추가:
  - `llm_evidence_json_path`
  - `llm_evidence_markdown_path`
  - `llm_objective`
  - `failure_reason_codes`
- delegate request goal을 “latest LLM evidence packet을 primary input으로 사용”하도록 단순화
- bridge prompt도 request에 evidence packet 경로가 있으면 먼저 읽고 `failure_reasons` / `llm_objective`를 우선하라고 명시
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-llm-handoff-prompt-simplification-v0.1-note.md`
  - `checklists/2026-04-16-hermes-watch-llm-handoff-prompt-simplification-v0.1-checklist.md`

### Failure reason extraction v0.2
- `LLM evidence packet v0.1` 위에 `run_history.json` 기반 failure reason 추출을 추가
- 새 reason codes:
  - `no-progress-stall`
  - `coverage-plateau`
  - `corpus-bloat-low-gain`
  - `shallow-crash-recurrence`
  - `stage-reach-blocked`
- `run_history_path`, `run_history`를 evidence packet에 포함하고 markdown에도 recent history summary를 추가
- deep mode인데 progress가 막히거나 shallow recurrence가 강하면 `llm_objective=deeper-stage-reach`로 더 직접 압축
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-failure-reason-extraction-v0.2-note.md`
  - `checklists/2026-04-16-hermes-watch-failure-reason-extraction-v0.2-checklist.md`

### LLM evidence packet v0.1
- latest `current_status.json`, `probe-feedback`, `harness-probe`, `harness-apply-candidate`, `harness-apply-result` artifacts를 모아 LLM 전달용 packet 생성
- `failure_reason_codes` / `failure_reasons`를 규칙 기반으로 추출
  - `build-blocker`
  - `smoke-invalid-or-harness-mismatch`
  - `no-crash-yet`
  - `repeated-crash-family`
  - `shallow-crash-dominance`
  - `harness-build-probe-failed`
  - `harness-smoke-probe-failed`
  - `guarded-apply-blocked`
- `llm_objective`를 failure reason 우선순위에서 선택해 다음 LLM handoff의 중심 목표를 먼저 압축
- `fuzz-records/llm-evidence/*-llm-evidence.json|md` artifact를 생성하는 CLI path `--write-llm-evidence-packet` 추가
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-llm-evidence-packet-v0.1-note.md`
  - `checklists/2026-04-16-hermes-watch-llm-evidence-packet-v0.1-checklist.md`
  - `notes/2026-04-16-fuzzing-jpeg2000-code-audit-llm-pivot.md`

### R18 — measured execution quality loop
- probe/build/smoke/verification pass-fail evidence를 candidate registry에 반영
- `execution_evidence_score`를 effective score와 queue weighting에 연결
- heuristic-only candidate ranking에서 **evidence-aware scheduler**로 한 단계 진전
- 관련 문서:
  - `notes/2026-04-15-hermes-watch-measured-execution-quality-loop-note.md`
  - `checklists/2026-04-15-hermes-watch-measured-execution-quality-loop-checklist.md`

### R19 — harness skeleton generation + revision loop
- low-risk skeleton draft source 생성
- selected candidate 우선 선택
- 기존 skeleton + review/reseed feedback가 있으면 revision으로 승격
- 아직 compile/fix/verify 자율루프는 아니지만, **artifact-first revision substrate**는 생김
- 관련 문서:
  - `notes/2026-04-15-hermes-watch-harness-skeleton-generation-note.md`
  - `checklists/2026-04-15-hermes-watch-harness-skeleton-generation-checklist.md`

### Pre-R20 hardening slice — timeout + env parsing
- bridge/probe subprocess에 기본 timeout 추가
- invalid integer env default가 있어도 `main()`이 안전한 fallback으로 시작
- 작은 단계지만 운영면 baseline을 더 안전하게 만드는 보강
- 관련 문서:
  - `notes/2026-04-15-hermes-watch-runtime-hardening-timeout-env-note.md`
  - `checklists/2026-04-15-hermes-watch-runtime-hardening-timeout-env-checklist.md`

### R20 revision intelligence v0.1
- latest probe feedback의 build/smoke 결과를 skeleton layer가 읽음
- `revision_priority`, `next_revision_focus`, `revision_signals`, `revision_summary`를 skeleton draft/manifest에 기록
- markdown에 `Revision Intelligence` section 추가
- 아직 actual compile/fix/verify closed loop는 아니지만, **R19의 얕은 revision substrate를 evidence-aware advisory loop로 한 단계 끌어올림**
- 관련 문서:
  - `notes/2026-04-15-hermes-watch-r20-revision-intelligence-note.md`
  - `checklists/2026-04-15-hermes-watch-r20-revision-intelligence-checklist.md`

### R20 actual closure v0.1
- latest skeleton artifact 기준 build/smoke probe manifest와 markdown 생성
- skeleton revision intelligence가 latest closure evidence를 probe feedback보다 우선 사용
- `--run-harness-skeleton-closure` CLI 경로 추가
- 아직 patch-level autonomous correction은 아니지만, **skeleton loop가 advisory-only 단계에서 skeleton-specific execution evidence 단계로 진입**
- 관련 문서:
  - `notes/2026-04-15-hermes-watch-r20-actual-closure-note.md`
  - `checklists/2026-04-15-hermes-watch-r20-actual-closure-checklist.md`

### R20 patch-level autonomous correction v0.1
- revision focus에 따라 `correction_strategy` / `correction_suggestions` 생성
- `*-correction-draft.json`, `*-correction-draft.md` artifact 생성
- skeleton manifest/markdown에서 correction draft를 직접 추적 가능
- 아직 실제 자동 patch apply는 아니지만, **이제 system은 failed closure를 보고 “무엇을 고칠지”를 source-adjacent artifact로 남길 수 있다**
- 관련 문서:
  - `notes/2026-04-15-hermes-watch-r20-patch-correction-note.md`
  - `checklists/2026-04-15-hermes-watch-r20-patch-correction-checklist.md`

### R20 correction-consumption / apply policy v0.1
- latest correction draft와 latest skeleton closure evidence를 함께 읽어 `decision`, `disposition`, `apply_policy`를 결정
- `harness-correction-policies/` 아래에 correction-policy manifest/markdown 생성
- 실패 closure일 때만 reviewable correction을 승격하고, 성공 closure는 `hold-no-change`로 보수적으로 보류
- 아직 실제 patch apply는 아니지만, **이제 system은 “무엇을 고칠지”뿐 아니라 “그 제안을 지금 소비해도 되는지”까지 별도 artifact로 판단한다**
- 관련 문서:
  - `notes/2026-04-15-hermes-watch-r20-correction-consumption-note.md`
  - `checklists/2026-04-15-hermes-watch-r20-correction-consumption-checklist.md`

### R20 guarded apply candidate generation v0.1
- promoted correction policy를 읽어 `harness-apply-candidates/` 아래에 guarded apply candidate manifest/markdown 생성
- 실패 closure에서만 optional delegate request artifact를 함께 생성해 LLM patch-candidate 작업을 자동 트리거할 준비를 함
- 아직 실제 source auto-apply는 하지 않고, **reviewable patch candidate artifact와 delegate request까지만 자동화한다**
- 관련 문서:
  - `notes/2026-04-15-hermes-watch-r20-guarded-apply-candidate-note.md`
  - `checklists/2026-04-15-hermes-watch-r20-guarded-apply-candidate-checklist.md`

### R20 guarded apply delegate consumption v0.1
- latest guarded apply candidate에서 delegate request를 읽어 `harness-apply-bridge/` 아래에 bridge prompt/script를 생성
- bridge launch 후 delegate session/artifact metadata를 apply candidate manifest에 다시 기록
- 아직 patch candidate 결과 검증/반영은 안 하지만, **이제 child LLM patch-candidate 작업을 실제로 launch할 수 있다**
- 관련 문서:
  - `notes/2026-04-15-hermes-watch-r20-guarded-apply-delegate-consumption-note.md`
  - `checklists/2026-04-15-hermes-watch-r20-guarded-apply-delegate-consumption-checklist.md`

### R20 patch-candidate result verification / ingestion v0.1
- latest succeeded apply candidate에 대해 delegate session visibility와 artifact 존재를 검증
- `delegate_expected_sections`, `delegate_quality_sections`를 사용해 patch-candidate artifact의 shape/quality를 검증
- verification 결과를 apply candidate manifest에 다시 반영해 다음 closure loop가 읽을 수 있게 함
- 관련 문서:
  - `notes/2026-04-15-hermes-watch-r20-patch-candidate-verification-note.md`
  - `checklists/2026-04-15-hermes-watch-r20-patch-candidate-verification-checklist.md`

### R20 guarded patch apply + build/smoke rerun v0.1
- latest verified apply candidate를 읽어 `comment-only` / `guard-only` 범위에서 target file에 제한적으로 반영
- build/smoke probe를 다시 실행하고 결과를 `harness-apply-results/` manifest로 저장
- 아직 rollback/failure recovery는 없지만, **이제 first-pass 제한적 source apply와 rerun이 실제로 실행된다**
- 관련 문서:
  - `notes/2026-04-15-hermes-watch-r20-guarded-patch-apply-note.md`
  - `checklists/2026-04-15-hermes-watch-r20-guarded-patch-apply-checklist.md`

### R20 rollback / failure recovery v0.1
- limited patch apply 전에 backup artifact를 남기고, build/smoke failure 시 원본 target file을 복구
- `rollback_status`, `backup_path`를 apply candidate/result artifact에 기록
- 아직 diff-level semantic safety는 단순하지만, **이제 first-pass 실패에 대해 최소한의 원복 루프는 생겼다**
- 관련 문서:
  - `notes/2026-04-15-hermes-watch-r20-rollback-failure-recovery-note.md`
  - `checklists/2026-04-15-hermes-watch-r20-rollback-failure-recovery-checklist.md`

### R20 candidate semantics / diff safety v0.1
- apply candidate summary를 scope와 대조해 out-of-scope mutation 요청을 apply 전에 차단
- generated harness 디렉터리 밖 target file과 과도한 changed line count를 diff safety guardrail로 차단
- blocked apply도 `apply_status=blocked`와 semantics/diff safety metadata로 artifact lineage에 기록
- 아직 deep semantic verifier는 아니지만, **이제 rollback 이전에 preventive apply guardrail이 한 단계 생겼다**
- 관련 문서:
  - `notes/2026-04-15-hermes-watch-r20-candidate-semantics-diff-safety-note.md`
  - `checklists/2026-04-15-hermes-watch-r20-candidate-semantics-diff-safety-checklist.md`

### R20 multi-step recovery policy v0.1
- blocked/rolled_back/applied 결과를 `hold / retry / abort / resolved` decision으로 분기
- `recovery_failure_streak`, `recovery_attempt_count`, `recovery_status`를 apply candidate/result artifact에 기록
- repeated rollback failure가 같은 rail에서 무한 반복되지 않도록 최소 abort rule 추가
- 아직 queue consumption이나 auto-reroute까지는 아니지만, **이제 apply 결과가 다음 orchestration 의미를 가진다**
- 관련 문서:
  - `notes/2026-04-15-hermes-watch-r20-multi-step-recovery-policy-note.md`
  - `checklists/2026-04-15-hermes-watch-r20-multi-step-recovery-policy-checklist.md`

### R20 recovery policy consumption / routing v0.1
- recovery decision을 action code/registry/bridge channel로 번역하는 routing layer 추가
- `fuzz-artifacts/automation/` 아래 retry/hold/abort/resolved registry에 entry를 기록
- `fuzz-records/harness-apply-recovery/` routing artifact와 apply candidate/result 역반영 metadata 추가
- 아직 queue consumer나 auto-bridge rearming은 없지만, **이제 recovery decision이 실제 orchestration rail 입력으로 바뀌기 시작했다**
- 관련 문서:
  - `notes/2026-04-15-hermes-watch-r20-recovery-policy-consumption-routing-note.md`
  - `checklists/2026-04-15-hermes-watch-r20-recovery-policy-consumption-routing-checklist.md`

### R20 recovery queue consumption / bridge rearming v0.1
- retry/hold/abort/resolved registry를 소비하는 recovery queue consumer 추가
- retry는 apply bridge를 다시 `armed` 상태로 되돌리고, hold는 review parking metadata를 남김
- abort/resolved도 baseline consumer 상태를 기록해 dead queue를 줄임
- 아직 auto-launch/auto-review까지는 아니지만, **이제 recovery queue가 실제 다음 action 준비 단계까지 닫히기 시작했다**
- 관련 문서:
  - `notes/2026-04-15-hermes-watch-r20-recovery-queue-consumption-bridge-rearming-note.md`
  - `checklists/2026-04-15-hermes-watch-r20-recovery-queue-consumption-bridge-rearming-checklist.md`

### R20 recovery downstream automation v0.1
- retry recovery lane을 consume 후 bridge rearm → launch → verify까지 연속 실행하는 downstream automation 추가
- apply candidate manifest에 downstream launch/verification status를 기록
- 아직 verify 이후 next-route까지는 안 닫혔지만, **이제 retry lane은 실제로 다시 달리고 검증까지 도달한다**
- 관련 문서:
  - `notes/2026-04-15-hermes-watch-r20-recovery-downstream-automation-note.md`
  - `checklists/2026-04-15-hermes-watch-r20-recovery-downstream-automation-checklist.md`

### R20 recovery full closed-loop chaining v0.1
- retry lane에서 downstream verified 이후 guarded apply와 recovery reroute까지 다시 연결
- apply candidate manifest에 full-chain apply/reroute status를 기록
- 아직 reroute 이후 자동 재귀 반복은 없지만, **이제 retry rail은 consume→execute→reroute까지 거의 폐루프에 가깝게 연결된다**
- 관련 문서:
  - `notes/2026-04-15-hermes-watch-r20-recovery-full-closed-loop-chaining-note.md`
  - `checklists/2026-04-15-hermes-watch-r20-recovery-full-closed-loop-chaining-checklist.md`

### R20 retry recursive chaining / termination guard v0.1
- retry full-chain을 여러 cycle 반복하되 `retry`가 아닌 reroute나 `max_cycles`에서 멈추는 bounded recursion 추가
- recursive chain status/cycle count를 manifest에 기록
- 새로운 지능이라기보다 loop를 안전하게 끝내는 최소 termination guard를 제공
- 관련 문서:
  - `notes/2026-04-15-hermes-watch-r20-retry-recursive-chaining-termination-guard-note.md`
  - `checklists/2026-04-15-hermes-watch-r20-retry-recursive-chaining-termination-guard-checklist.md`

### R20 hold/abort downstream consumers v0.1
- hold recovery lane이 이제 `pending-review` 표식만 남기지 않고 `harness_review_queue.json`에 `halt_and_review_harness` follow-up entry를 실제 enqueue
- abort recovery lane이 이제 terminal 기록만 남기지 않고 `harness_correction_regeneration_queue.json`에 `regenerate_harness_correction` corrective follow-up entry를 enqueue
- apply candidate manifest에 `recovery_followup_*` lineage를 기록해 어떤 follow-up consumer로 연결됐는지 역추적 가능
- 기존 refiner executor/orchestration substrate가 새 corrective action을 그대로 소비할 수 있어 **hold/abort lane도 실제 다음 작업을 만드는 rail**로 진입
- 관련 문서:
  - `notes/2026-04-15-hermes-watch-r20-hold-abort-downstream-consumers-note.md`
  - `checklists/2026-04-15-hermes-watch-r20-hold-abort-downstream-consumers-checklist.md`

### R20 patch diff scope / touched-region safety v0.1
- generated harness 내부에서도 `LLVMFuzzerTestOneInput` region만 건드리도록 touched-region guardrail 추가
- comment-only는 append-only Hermes comment만, guard-only는 entrypoint guard whitelist line만 허용하도록 scope별 whitelist 강화
- multi-hunk diff baseline 차단과 `diff_hunk_count` / `diff_touched_region_*` metadata 추가
- blocked payload에도 diff safety reason을 직접 노출해 **왜 막혔는지 바로 읽히는 safety lineage** 확보
- 관련 문서:
  - `notes/2026-04-15-hermes-watch-r20-patch-diff-scope-touched-region-safety-note.md`
  - `checklists/2026-04-15-hermes-watch-r20-patch-diff-scope-touched-region-safety-checklist.md`

### R20 hold/abort follow-up auto-reingestion v0.1
- verified `halt_and_review_harness` follow-up 결과를 `write_harness_correction_policy(...)`로 다시 연결해 correction-policy loop 입력으로 재주입
- verified `regenerate_harness_correction` follow-up 결과를 `write_harness_apply_candidate(...)`로 다시 연결해 apply-candidate loop 입력으로 재주입
- follow-up registry와 original apply candidate manifest 양쪽에 `reingestion_*` lineage를 기록해 **어떤 verified follow-up이 어떤 loop로 돌아갔는지** 추적 가능
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-r20-hold-abort-followup-auto-reingestion-note.md`
  - `checklists/2026-04-16-hermes-watch-r20-hold-abort-followup-auto-reingestion-checklist.md`

### R20 reingested downstream chaining v0.1
- verified hold review reingestion 뒤 `write_harness_apply_candidate(...)`를 거쳐 apply-candidate를 다시 만들고 bridge/verify/apply/reroute rail로 이어붙임
- verified abort regeneration reingestion 뒤 apply-candidate를 arm → launch → verify → apply → reroute로 가능한 범위까지 연쇄 실행
- original apply candidate manifest에 `recovery_followup_chain_*` lineage를 기록해 **verified follow-up이 어떤 새 apply candidate와 reroute 결과로 이어졌는지** 역추적 가능
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-r20-reingested-downstream-chaining-note.md`
  - `checklists/2026-04-16-hermes-watch-r20-reingested-downstream-chaining-checklist.md`

### R20 follow-up failure policy reverse linkage v0.1
- follow-up verification failure policy가 `recovery_followup_reason`과 `apply_candidate_manifest_path`를 가진 entry를 처리할 때 original apply candidate manifest를 역갱신
- retry/escalate 양쪽 모두에 대해 `recovery_followup_failure_policy_*` lineage를 남겨 **성공한 follow-up뿐 아니라 실패한 follow-up policy 결과도 original apply candidate 쪽에서 보이게 함**
- return payload에도 `reverse_linked_apply_candidate_manifest_path`를 추가해 상위 orchestration이 reverse linkage 결과를 바로 읽을 수 있게 함
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-r20-followup-failure-policy-reverse-linkage-note.md`
  - `checklists/2026-04-16-hermes-watch-r20-followup-failure-policy-reverse-linkage-checklist.md`

### R20 retry and downstream budget/cooldown v0.1
- retry recursive chain이 `recovery_recursive_chain_checked_at` / cooldown window를 보고 너무 빠른 재실행을 `cooldown-active`로 멈추도록 보강
- reingested downstream chain이 `recovery_followup_chain_budget` / `recovery_followup_chain_attempt_count` / cooldown window를 보고 `budget-exhausted` 또는 `cooldown-active`로 멈추도록 보강
- CLI 성공 조건도 이 guard 상태를 정상 종료로 취급하도록 조정해 **한꺼번에 계속 돌릴 때도 최소 운영 안전장치**를 갖춤
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-r20-retry-downstream-budget-cooldown-note.md`
  - `checklists/2026-04-16-hermes-watch-r20-retry-downstream-budget-cooldown-checklist.md`

### R20 reverse-linked follow-up failure routing integration v0.1
- original apply candidate의 `recovery_followup_failure_policy_*` reverse linkage를 읽어, follow-up escalation이 남아 있으면 next recovery routing을 `retry`에서 더 보수적인 `hold` 또는 `abort`로 override
- hold 성격 escalation(`delegate-quality-gap`, `candidate-review-required`, `halt_and_review_harness`)은 `hold`로, corrective/regeneration 쪽 escalation은 `abort`로 보내 **실패 memory가 실제 route behavior를 바꾸기 시작함**
- recovery route entry / apply candidate manifest / apply result에 `routing_risk_level`, `routing_reverse_linkage_status`, `routing_reverse_linkage_reason` lineage를 추가해 왜 더 보수적인 route를 택했는지 artifact만 보고 읽을 수 있게 함
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-r20-reverse-linked-followup-failure-routing-integration-note.md`
  - `checklists/2026-04-16-hermes-watch-r20-reverse-linked-followup-failure-routing-integration-checklist.md`

### Adaptive retry / downstream budget-cooldown v0.1
- `recovery_route_risk_level` / `recovery_followup_failure_policy_reason`를 읽어 retry recursive chain cooldown을 300s 기본값에서 high-risk는 900s, critical-risk는 1800s까지 더 보수적으로 조정
- downstream chain도 같은 risk signal을 읽어 budget과 cooldown을 adaptively 조정하고, critical-risk / `retry-budget-exhausted` 상태에서는 더 빨리 `budget-exhausted`로 닫도록 보강
- `recovery_recursive_chain_adaptive_reason`, `recovery_followup_chain_adaptive_reason`, return payload의 `adaptive_reason`을 추가해 **왜 더 느리게/더 적게 시도했는지** lineage로 남김
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-adaptive-retry-downstream-budget-cooldown-note.md`
  - `checklists/2026-04-16-hermes-watch-adaptive-retry-downstream-budget-cooldown-checklist.md`

### Deeper semantic diff safety / corrective intent analysis v0.1
- guard-only diff whitelist를 substring 허용이 아니라 token-aware exact-match 쪽으로 강화해, canonical entrypoint signature / canonical size guard / `return 0;` / brace / Hermes comment만 허용
- extra parameter가 끼어든 `LLVMFuzzerTestOneInput(...)` signature mutation과 `if (size < 4) { helper(); ... }` 형태의 inline side-effect를 실제로 차단해 **guard-only patch가 정말 guard-intent에 맞는지 더 엄격하게 보기 시작함**
- overnight 작업을 위해 `.hermes/plans/2026-04-16_014200-overnight-safe-slices.md`와 recursion/generalization prep checklist를 추가해 다음 안전 slice를 바로 이어갈 수 있게 함
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-deeper-semantic-diff-safety-corrective-intent-analysis-note.md`
  - `checklists/2026-04-16-hermes-watch-deeper-semantic-diff-safety-corrective-intent-analysis-checklist.md`
  - `checklists/2026-04-16-full-recovery-ecosystem-recursion-prep-checklist.md`
  - `checklists/2026-04-16-multi-target-adapter-generalization-prep-checklist.md`

### Full recovery ecosystem recursion v0.1
- `run_harness_apply_recovery_ecosystem_recursion(...)`를 추가해 retry recursive lane과 reingested downstream lane을 같은 bounded recursion 관점에서 orchestration
- reverse-linked follow-up escalation / queued follow-up / reingested follow-up signal이 있으면 downstream lane을 우선 보도록 lane priority를 조정
- `recovery_ecosystem_status`, `recovery_ecosystem_stop_reason`, `recovery_ecosystem_round_count`, `recovery_ecosystem_last_lane`, `recovery_ecosystem_lane_sequence`를 apply candidate lineage에 기록
- 아직 unified budget/cooldown policy object나 autonomous re-trigger scheduling까지 닫힌 것은 아니지만, **이제 rail 간 전환과 정지 이유를 하나의 ecosystem-level artifact memory로 남기기 시작했다**
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-full-recovery-ecosystem-recursion-note.md`
  - `checklists/2026-04-16-hermes-watch-full-recovery-ecosystem-recursion-checklist.md`
  - `checklists/2026-04-16-multi-target-adapter-generalization-prep-checklist.md`

### Comment-only / broader corrective intent analysis v0.1
- `comment-only` scope에서 delegate summary가 실제 코드 mutation(`return` 변경, include 추가, helper call 삽입 등)을 요구하면 apply 전에 semantics 단계에서 선제 차단
- blocked return payload에도 `candidate_semantics_summary`, `candidate_semantics_reasons`를 직접 노출해 **왜 막혔는지 즉시 읽히는 broader corrective intent lineage**를 추가
- 아직 키워드 기반 보수 필터 수준이지만, **이제 comment-only rail도 단순 append-only diff 검사만 보지 않고 요청 의도 자체를 따지기 시작했다**
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-comment-only-broader-corrective-intent-analysis-note.md`
  - `checklists/2026-04-16-hermes-watch-comment-only-broader-corrective-intent-analysis-checklist.md`
  - `checklists/2026-04-16-multi-target-adapter-generalization-prep-checklist.md`

### Multi-target adapter generalization v0.1
- target profile의 `target.adapter` spec을 summary로 끌어올리고, `get_target_adapter(...)`가 그 spec을 실제 runtime adapter로 해석하도록 확장
- main smoke-success/final-summary path에서 custom build/smoke/fuzz command, notification label, report target이 실제로 적용되는 E2E test를 추가해 **adapter seam이 mock용이 아니라 runtime seam으로 작동함을 확인**
- 아직 broader command separation / editable-region policy seam / multi-target regression matrix는 남아 있지만, **이제 multi-target adapter narrative가 단순 abstraction이 아니라 실제 runtime behavior를 바꾸기 시작했다**
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-multi-target-adapter-generalization-v0.1-note.md`
  - `checklists/2026-04-16-hermes-watch-multi-target-adapter-generalization-v0.1-checklist.md`
  - `checklists/2026-04-16-multi-target-adapter-generalization-prep-checklist.md`

### Multi-target adapter generalization v0.2 command separation slice
- `harness_probe` 계층이 default target profile을 읽고 adapter를 resolve해, short harness probe와 harness skeleton closure의 build/smoke command도 profile-driven adapter command를 우선 사용하도록 확장
- custom profile adapter spec이 있을 때 `build_harness_probe_draft(...)`와 `run_harness_skeleton_closure(...)`가 실제로 custom build/smoke command를 쓰는 regression test를 추가해 **broader command separation이 main watcher 밖으로 확장됐는지** 검증
- 아직 editable-region policy seam / regression smoke matrix / 추가 leakage 제거는 남아 있지만, **이제 adapter seam이 main loop 전용이 아니라 probe/closure 하위 loop로도 전파되기 시작했다**
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-multi-target-adapter-generalization-v0.2-command-separation-note.md`
  - `checklists/2026-04-16-hermes-watch-multi-target-adapter-generalization-v0.2-command-separation-checklist.md`
  - `checklists/2026-04-16-multi-target-adapter-generalization-prep-checklist.md`

### Multi-target adapter generalization v0.2 editable-region policy seam slice
- target adapter에 `editable_harness_relpath`, `fuzz_entrypoint_names` policy field를 추가하고, profile summary가 이 값을 보존하도록 확장
- apply safety 계층이 이제 runtime target adapter를 읽어 editable harness root와 fuzz entrypoint 이름을 결정하므로, **mutation safety rail도 command seam처럼 profile-driven policy를 따르기 시작함**
- custom editable harness dir + custom fuzz entrypoint를 쓰는 guarded apply regression test를 추가해, adapter seam이 실제 diff safety/touched-region policy까지 퍼졌는지 검증
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-multi-target-adapter-generalization-v0.2-editable-region-policy-note.md`
  - `checklists/2026-04-16-hermes-watch-multi-target-adapter-generalization-v0.2-editable-region-policy-checklist.md`
  - `checklists/2026-04-16-multi-target-adapter-generalization-prep-checklist.md`

### Multi-target adapter generalization v0.2 regression smoke matrix slice
- target adapter 기준으로 main / harness-probe / skeleton-closure 경로의 build·smoke·fuzz expectation과 policy fields를 한 장으로 요약하는 regression smoke matrix artifact helper를 추가
- `write_runtime_target_adapter_regression_smoke_matrix(...)`가 default target profile을 읽어 matrix json/markdown을 생성하므로, **현재 adapter contract가 실제로 어디까지 퍼졌는지 점검 가능한 regression surface**가 생김
- 이 단계는 live smoke execution을 늘린 건 아니지만, 이후 multi-target regression smoke matrix를 실제 실행 checklist로 확장하기 전에 contract drift를 잡는 inspection layer를 먼저 만든 셈이다
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-multi-target-adapter-generalization-v0.2-regression-smoke-matrix-note.md`
  - `checklists/2026-04-16-hermes-watch-multi-target-adapter-generalization-v0.2-regression-smoke-matrix-checklist.md`
  - `checklists/2026-04-16-multi-target-adapter-generalization-prep-checklist.md`

### Multi-target adapter generalization v0.2 mutation generation seam slice
- `_build_guard_only_patch_plan(...)` helper를 추가해 guard-only patch generation을 apply path에서 분리하고, **mutation planning seam**을 작은 reviewable helper로 끊어냈다
- `_inject_guarded_patch(...)`가 `entrypoint_names`를 받아 custom fuzz entrypoint 이름과 custom C/C++ signature를 실제 처리하도록 확장됐다
- `apply_verified_harness_patch_candidate(...)`가 runtime target adapter의 `fuzz_entrypoint_names`를 실제 넘기므로, **adapter seam이 command/policy를 넘어 guarded mutation generation point selection까지 퍼지기 시작했다**
- 아직 guard condition 선택이나 patch synthesis 자체는 여전히 heuristic string-based 수준이지만, 이제 최소한 mutation insertion point가 single-target hardcoding에서 한 칸 벗어났다
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-multi-target-adapter-generalization-v0.2-mutation-generation-seam-note.md`
  - `checklists/2026-04-16-hermes-watch-multi-target-adapter-generalization-v0.2-mutation-generation-seam-checklist.md`
  - `checklists/2026-04-16-multi-target-adapter-generalization-prep-checklist.md`

### Multi-target adapter generalization v0.2 guard policy contract slice
- target adapter와 profile summary가 이제 `guard_condition`, `guard_return_statement`까지 보존하므로, **guard body 하드코딩이 adapter contract로 이동하기 시작했다**
- `_build_guard_only_patch_plan(...)`, `_inject_guarded_patch(...)`, `_guard_only_line_allowed(...)`, `_diff_safety_guardrails(...)`가 같은 guard policy를 소비해 generation과 whitelist의 계약을 맞췄다
- regression smoke matrix도 guard policy metadata를 기록하고, runtime guarded apply E2E path가 custom guard condition/return policy를 실제 적용하도록 검증했다
- 아직 guard contract는 string-based policy 수준이지만, 이제 entrypoint뿐 아니라 guard body 자체도 single-target 하드코딩에서 한 칸 더 벗어났다
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-multi-target-adapter-generalization-v0.2-guard-policy-contract-note.md`
  - `checklists/2026-04-16-hermes-watch-multi-target-adapter-generalization-v0.2-guard-policy-contract-checklist.md`
  - `checklists/2026-04-16-multi-target-adapter-generalization-prep-checklist.md`

### Multi-target adapter generalization v0.2 skeleton entrypoint de-hardcode slice
- `harness_skeleton.py`가 이제 runtime target adapter를 읽어 skeleton source draft의 entrypoint 이름을 결정하므로, **가장 눈에 띄는 skeleton artifact hardcoding 하나가 adapter seam 안으로 들어왔다**
- `build_harness_skeleton_draft(...)` payload와 markdown에도 `skeleton_entrypoint_name` metadata를 남겨 source draft contract를 artifact로 추적 가능하게 했다
- `write_harness_skeleton_draft(...)` regression test를 추가해 written source artifact가 custom entrypoint 이름을 실제 반영하는지 검증했다
- 아직 skeleton body/prepare logic/TODO wiring은 generic하지만, 이제 최소한 source draft의 visible ABI 이름은 single-target 하드코딩에서 한 칸 벗어났다
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-multi-target-adapter-generalization-v0.2-skeleton-entrypoint-dehardcode-note.md`
  - `checklists/2026-04-16-hermes-watch-multi-target-adapter-generalization-v0.2-skeleton-entrypoint-dehardcode-checklist.md`
  - `checklists/2026-04-16-multi-target-adapter-generalization-prep-checklist.md`

### Multi-target adapter generalization v0.2 skeleton body guard-policy alignment slice
- `harness_skeleton.py`가 이제 runtime adapter의 `guard_condition`, `guard_return_statement`를 읽어 source draft body의 초기 safety gate를 구성하므로, **source artifact body도 adapter contract를 일부 소비하기 시작했다**
- C / C++ skeleton source draft에서 generic `hermes_prepare_input(...)` helper를 제거하고, null check + adapter-driven guard condition + adapter-driven early return을 직접 배치했다
- draft payload/markdown에 `skeleton_guard_condition`, `skeleton_guard_return_statement` metadata를 남겨 source body contract drift를 artifact로 추적 가능하게 했다
- 아직 target ABI / actual parser contract를 이해한 body synthesis는 아니지만, 이제 최소한 skeleton body의 얕은 initial guard는 single-target hardcoding에서 한 칸 더 벗어났다
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-multi-target-adapter-generalization-v0.2-skeleton-body-guard-policy-alignment-note.md`
  - `checklists/2026-04-16-hermes-watch-multi-target-adapter-generalization-v0.2-skeleton-body-guard-policy-alignment-checklist.md`
  - `checklists/2026-04-16-multi-target-adapter-generalization-prep-checklist.md`

### Multi-target adapter generalization v0.2 skeleton call-contract generalization slice
- target adapter가 이제 `target_call_todo`, `resource_lifetime_hint`를 보존하고, `harness_skeleton.py`가 이를 source draft/markdown metadata에 실제 반영하므로 **generic wiring placeholder가 adapter-driven call contract comment로 치환되기 시작했다**
- source draft는 이제 `TODO: wire ...` 한 줄 대신 target call TODO, lifetime hint, binding hint를 분리해 남긴다
- draft payload/markdown에도 `skeleton_target_call_todo`, `skeleton_resource_lifetime_hint` metadata를 남겨 call-shape guidance drift를 artifact로 추적 가능하게 했다
- 아직 real ABI/ownership inference는 아니지만, 이제 skeleton artifact는 최소한 target call shape와 lifetime 가정을 generic placeholder보다 더 구체적으로 드러낸다
- 관련 문서:
  - `notes/2026-04-16-hermes-watch-multi-target-adapter-generalization-v0.2-skeleton-call-contract-generalization-note.md`
  - `checklists/2026-04-16-hermes-watch-multi-target-adapter-generalization-v0.2-skeleton-call-contract-generalization-checklist.md`
  - `checklists/2026-04-16-multi-target-adapter-generalization-prep-checklist.md`

---

## 현재 냉정한 평가

### 잘 된 점
- duplicate replay rail이 deep family 전용이 아니라 medium repeated family까지 확장됐다
- latest repeated crash가 실제 replay evidence와 plan artifact를 가진 상태로 LLM packet에 다시 연결된다
- replay evidence를 읽은 latest packet이 실제로 `minimize_and_reseed / reseed-before-retry`를 제안하도록 복구됐다
- targeted regression과 full pytest 모두 깨지지 않았다

### 아직 얕은 점
- `coding_units.cpp:3076` family에 대한 actual corpus refinement execution은 아직 없다
- replay review는 생겼지만 minimization/reseed 효과 측정은 없다
- duplicate replay에서 corpus refinement로 자동 follow-up entry를 만드는 규칙은 현재 deep family 기반 흐름에 비해 medium family 쪽 live closure가 덜 자동화돼 있다
- remote/proxmox 쪽 execution closure는 그대로 남아 있다

### 핵심 리스크
- 지금 단계는 latest packet이 더 똑똑해진 것이지, finding efficiency가 실제로 오른 것은 아니다
- repeated duplicate를 replay review로 더 자주 올리면 문서는 늘 수 있지만, reseed/minimization execution과 효과 측정이 뒤따르지 않으면 control-plane ornament로 되돌아갈 수 있다
- 그래서 다음 단계는 반드시 `coding_units.cpp:3076` family를 actual corpus refinement 실행과 bounded rerun 측정으로 내려야 한다

---

## 점수화
- control-plane 성숙도: **9.6 / 10**
- artifact / lineage 설계: **9.6 / 10**
- duplicate triage closure: **8.9 / 10**
- LLM handoff 현실성: **8.7 / 10**
- autonomous revision intelligence: **7.9 / 10**
- 실제 finding efficiency readiness: **7.5 / 10**

### 한 줄 총평
**지금 시스템은 repeated duplicate를 그냥 sink로 밀어 넣는 단계는 넘었고, medium duplicate family도 replay evidence와 LLM next-step override를 다시 받기 시작했다. 하지만 아직 핵심은 문서/route가 아니라 `coding_units.cpp:3076` family를 실제 `minimize_and_reseed` 실행과 rerun 측정까지 내려 finding efficiency 변화로 증명하는 것이다.**

---

## 바로 다음 우선순위
1. **coverage corpus 기준 reseed effectiveness measurement**
   - 이제 wrapper corpus override가 실제로 먹으므로 bounded rerun을 반복해 duplicate recurrence / novelty / coverage delta를 전후 비교
2. **active coverage corpus의 toxic seed quarantine 규칙화**
   - 이번 rerun에서 다시 `j2kmarkers.cpp:52` duplicate family가 강하게 남았으므로 어떤 seed가 shallow duplicate를 지배하는지 식별하고 active corpus에서 안전하게 격리
3. **remote/proxmox closure 연결**
   - local에서 실제 corpus/mode contract가 맞춰진 뒤 remote execution 루프에도 같은 override-friendly contract와 artifact spine을 복제

---

## 이 문서의 역할
이 문서는 “최신 한 장 요약”이다.
더 자세한 단계별 기록은 아래를 본다.

- 전체 진행표: `progress-index.md`
- 상위 장기 방향: `.hermes/plans/2026-04-15_133343-semi-autonomous-multi-target-fuzzing-roadmap.md`
- 개별 구현 근거: `notes/`, `checklists/`, `plans/`
