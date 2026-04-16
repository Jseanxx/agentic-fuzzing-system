# Hermes Watch Duplicate Deep Crash Replay Review Routing v0.1

## 왜 이 단계가 필요했나
방금까지 control-plane은 새 deep critical crash family를 처음 잡았을 때는 triage 쪽으로 꺾을 수 있었지만,
같은 family가 다시 나오면 바로:
- `record-duplicate-crash`
- `known-bad`
- `coverage`
로 내려버렸다.

이건 artifact는 남기지만, 실제 자가발전형 루프 관점에서는 너무 빨리 관성 상태로 복귀하는 동작이다.
특히 지금처럼 `j2kmarkers.cpp:52` 같은 deep-stage critical family가 반복 재현되는 경우에는,
단순 duplicate 취급보다:
- first seen vs latest artifact 비교
- replay / minimization triage 계획
- LLM이 읽을 수 있는 후속 review rail
이 더 가치 있다.

## 이번에 고친 것
- `scripts/hermes_watch.py`
  - duplicate crash policy에서
    - `occurrence_count >= 2`
    - `crash_stage_class = deep`
    이면 `record-duplicate-crash` 대신
    - `review_duplicate_crash_replay`
    - `priority = high`
    - `next_mode = triage`
    - `bucket = triage`
    로 승격하도록 변경
  - duplicate family는 이제 `record-duplicate-crash`뿐 아니라 `review_duplicate_crash_replay`에서도 `known_bad.json`을 계속 갱신한다.
  - `known_bad.json` entry에
    - `first_seen_run`
    - `last_seen_run`
    - `occurrence_count`
    를 남겨 duplicate family 누적 근거를 더 직접 보존한다.
  - 새 registry `duplicate_crash_reviews.json` 추가
    - fingerprint
    - first seen run
    - latest artifact path
    - occurrence count
    를 묶어 refiner follow-up 입력으로 남긴다.
  - refiner queue / orchestration spec에 `review_duplicate_crash_replay`를 추가해 low-risk replay/minimization triage plan 문서 생성 rail을 연결했다.
- `tests/test_hermes_watch.py`
  - repeated deep duplicate crash가 replay review action으로 승격되는 regression test 추가
  - 해당 action이 `known_bad` + `duplicate_crash_reviews` 둘 다 갱신하는지 검증 추가
  - 새 registry가 refiner executor에서 실제 plan으로 소비되는지 검증 추가

## 실제 결과
실 repo bounded rerun:
- command:
  - `python scripts/hermes_watch.py --repo /home/hermes/work/fuzzing-jpeg2000 --max-total-time 5 --no-progress-seconds 30`
- latest run:
  - `fuzz-artifacts/runs/20260416_202702_1d5b676`
- observed family:
  - `asan|j2kmarkers.cpp:52|heap-buffer-overflow ...`
- state:
  - `crash_is_duplicate = true`
  - `crash_occurrence_count = 3`
  - `crash_stage_class = deep`
  - `policy_action_code = review_duplicate_crash_replay`
  - `policy_execution_updated = ['policy_log', 'known_bad', 'duplicate_crash_reviews', 'regression']`
- generated registry:
  - `fuzz-artifacts/automation/duplicate_crash_reviews.json`
- generated plan:
  - `fuzz-records/refiner-plans/review_duplicate_crash_replay-home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_202702_1d5b676.md`

## 의미
이제 duplicate deep critical family가 나와도 control-plane이 그냥 "이미 본 크래시"로 눌러버리지 않는다.
즉시 exploit 쪽으로 가는 게 아니라,
- evidence 보존
- family recurrence 누적
- replay/minimization triage 준비
- LLM review rail 연결
쪽으로 한 단계 더 닫혔다.

이건 화려한 autonomy가 아니라,
**duplicate signal을 operator memory에서 끝내지 않고 artifact-first follow-up 입력으로 승격한 것**에 가깝다.

## 한계
- 아직 `review_duplicate_crash_replay`가 실제 triage mode 실행을 자동으로 돌리지는 않는다.
- 지금 단계는 low-risk review/plan rail까지다.
- first-seen artifact를 자동으로 찾아 diff/compare report까지 만드는 건 아직 아니다.
- proxmox/remote closure와 연결된 것은 아니다.

## 다음 단계
- `duplicate_crash_reviews.json` entry를 first/latest artifact 비교 요약으로 더 풍부하게 만들기
- replay/minimization 실제 실행 결과가 evidence packet / revision objective로 다시 닫히는지 연결하기
- remote/proxmox에서도 같은 duplicate-family triage rail을 재사용할 수 있게 입력 계약 정리하기

## 검증
- `pytest -q tests/test_hermes_watch.py -k 'replay_review or duplicate_crash_replay_review'`
- `pytest -q tests/test_hermes_watch.py -k 'duplicate_crash or known_bad or execute_next_refiner_action'`
- `pytest -q`
- `python scripts/hermes_watch.py --repo /home/hermes/work/fuzzing-jpeg2000 --max-total-time 5 --no-progress-seconds 30`
- `python - <<'PY' ... hermes_watch.execute_next_refiner_action(...) ... PY`
