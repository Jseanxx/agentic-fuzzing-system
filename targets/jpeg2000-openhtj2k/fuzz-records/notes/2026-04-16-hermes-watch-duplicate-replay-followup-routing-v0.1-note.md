# Duplicate replay follow-up routing v0.1

- Date: 2026-04-16 21:28:15 KST
- Scope: `scripts/hermes_watch.py`, `scripts/hermes_watch_support/llm_evidence.py`, `tests/test_hermes_watch.py`

## 왜 이 slice를 골랐나
`review_duplicate_crash_replay`는 이제 first/latest replay evidence를 남긴다.
그런데 그 evidence가 다음 safe action으로 자동 연결되지 않으면, 시스템은 여전히 compare 문서 생산기다.
이번 slice의 목적은 stable duplicate replay를 실제 `minimize_and_reseed` queue 입력으로 승격해 true north의 마지막 한 칸을 메우는 것이었다.

## root cause
- duplicate replay review entry는 replay markdown/json/log/signature까지 남겼다.
- 하지만 replay 결과를 읽고 다음 revision queue를 만들지는 않았다.
- 그래서 `j2kmarkers.cpp:52`처럼 first/latest가 같은 signature로 안정 재현되는 family도 사람이 다시 골라야 했다.

## 이번에 바꾼 것
### 1. duplicate replay -> corpus refinement follow-up builder 추가
- `build_duplicate_replay_followup_entry(...)`
- 조건:
  - `replay_execution_status == completed`
  - first/latest replay exit code 둘 다 nonzero
  - first/latest replay signature가 같은 family/location
  - artifact bytes는 다름
- 출력:
  - `action_code = minimize_and_reseed`
  - `candidate_route = reseed-before-retry`
  - replay markdown/json path, first/latest exit/signature, source duplicate review key 포함

### 2. duplicate replay executor가 follow-up queue를 실제 기록
- `record_duplicate_replay_followup(...)`
- `execute_next_refiner_action(...)`가 duplicate replay execution 직후 `corpus_refinements.json`에 follow-up entry를 기록
- source duplicate review entry에도 `replay_followup_action_code`, `replay_followup_registry`, `replay_followup_entry_key` lineage를 남김

### 3. LLM evidence routing override 추가
- `_duplicate_replay_routing_override(...)`
- current status가 duplicate replay review이고 stable replay evidence가 있으면
  - `suggested_action_code = minimize_and_reseed`
  - `suggested_candidate_route = reseed-before-retry`
  로 override
- 즉 duplicate replay packet이 이제 review-only가 아니라 reseed/minimize 방향으로 직접 읽히기 시작함

## 검증
### RED
- `pytest -q tests/test_hermes_watch.py -k 'duplicate_crash_replay_followup or duplicate_crash_review_context or records_duplicate_replay_followup_corpus_refinement'`
- 초기 2 fail
  - llm evidence suggested action이 여전히 `halt_and_review_harness`
  - duplicate replay executor가 `corpus_refinements.json`에 아무 것도 안 남김

### GREEN
- 같은 명령 재실행 -> 3 pass
- `pytest -q tests/test_hermes_watch.py -k 'duplicate_crash or llm_evidence or minimize_and_reseed'` -> 36 pass
- `pytest -q` -> 324 pass

### live artifact update
- existing `duplicate_crash_reviews.json` entry에서 follow-up 생성 실행
- 결과:
  - `fuzz-artifacts/automation/corpus_refinements.json`
  - key: `minimize_and_reseed:duplicate-replay:asan|j2kmarkers.cpp:52|...`
- entry에 replay execution markdown/json path, source key, first/latest exit/signature가 같이 남음

## 왜 의미가 있나
이제 duplicate replay는 compare evidence에서 끝나지 않는다.
stable duplicate family면 다음 safe step이 `corpus refinement queue`로 남는다.
즉 `artifact preservation -> trigger/review -> rerun evidence -> revision routing`이 처음으로 실제 queue artifact까지 닫혔다.

## 남은 한계
- minimization 실행 자체는 아직 없다.
- latest current status는 `coding_units.cpp:3076` medium duplicate라 이번 override가 현재 top packet에는 직접 반영되지 않는다.
- medium duplicate를 replay review rail로 올릴지 규칙은 아직 없다.

## 다음 추천
1. 새 `minimize_and_reseed` entry를 실제 refiner plan/orchestration으로 소비
2. bounded minimization artifact 산출물에 대한 replay/sha/size 검증 추가
3. `coding_units.cpp:3076` duplicate family escalation 규칙 검토
