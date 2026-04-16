# Hermes Watch — medium duplicate replay escalation and packet recovery v0.1

- Date: 2026-04-16 22:00:53 KST
- Scope: repeated medium duplicate family가 duplicate replay review rail과 LLM packet recovery를 다시 타게 만드는 안전한 loop-quality slice

## 왜 이 slice가 필요했나
최신 `coding_units.cpp:3076` crash family는 repeated duplicate였지만 `stage_class=medium`이라 기존 policy에서 `record-duplicate-crash`로만 남았다.
그 결과:
- replay review artifact를 새로 만들 수 있는 rail이 있어도 medium duplicate는 거기에 못 들어갔고
- 수동으로 replay review를 실행해도 latest `llm_evidence` packet은 그 context를 다시 못 읽었다
- 최신 repeated crash가 실제 next step(`minimize_and_reseed`) 대신 그냥 known-bad sink로 눌리는 모양새가 남았다

이건 true north 기준으로 좋지 않다.
`duplicate recurrence -> replay evidence -> LLM-guided next step` 고리가 medium duplicate에서 끊겨 있었기 때문이다.

## 이번에 바꾼 것
1. `scripts/hermes_watch.py`
   - repeated duplicate가 `stage_class in {medium, deep}` 또는 `stage_depth_rank >= 2`면 `review_duplicate_crash_replay`로 승격되게 policy 조건 확장
2. `scripts/hermes_watch_support/llm_evidence.py`
   - latest status가 여전히 `record-duplicate-crash`여도
   - `crash_is_duplicate=true` + `crash_occurrence_count>=2`면
   - fingerprint/run/report 기준으로 duplicate review registry를 재탐색하도록 완화
3. live recovery
   - latest `coding_units.cpp:3076` family에 대해 replay review entry를 실제 기록하고 bounded replay execution까지 수행

## 실제로 생긴 artifact
- plan:
  - `fuzz-records/refiner-plans/review_duplicate_crash_replay-home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_205450_1d5b676.md`
- replay evidence:
  - `fuzz-records/duplicate-crash-replays/home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_205450_1d5b676.md`
  - `...-first.log`
  - `...-latest.log`

## 검증 요약
- RED
  - medium duplicate policy 승격 test fail 확인
  - repeated duplicate status에서 duplicate review context recovery test fail 확인
- GREEN
  - targeted rerun pass
  - `pytest -q tests/test_hermes_watch.py -k 'duplicate_crash or corpus_refinement or llm_evidence or decide_policy_action'` → 50 pass
  - `pytest -q` → 330 pass
- live
  - first/latest replay exit code 둘 다 `-6`
  - first/latest replay signature 둘 다 `asan|coding_units.cpp:3076|SEGV ...`
  - refreshed packet:
    - `suggested_action_code = minimize_and_reseed`
    - `suggested_candidate_route = reseed-before-retry`
    - `duplicate_crash_review` present

## 왜 의미가 있나
이제 medium duplicate도 단순 sink가 아니라 replay evidence를 가진 review 대상으로 승격된다.
그래서 latest packet이 실제 replay evidence를 읽고 다음 행동을 더 현실적으로 제안한다.
이건 자율성 과장이 아니라, repeated duplicate를 실제 다음 safe action으로 연결하는 작은 closure다.

## 아직 남은 것
- `coding_units.cpp:3076` family에 대한 actual `minimize_and_reseed` 실행
- reseed 후 bounded rerun으로 novelty/coverage 변화 측정
- remote/proxmox loop에 같은 artifact spine 연결

## 냉정한 판단
좋아진 것은 route quality와 evidence continuity다.
아직 좋아졌다고 말할 수 없는 것은 finding efficiency다.
다음 step은 문서가 아니라 실제 corpus refinement 실행이어야 한다.
