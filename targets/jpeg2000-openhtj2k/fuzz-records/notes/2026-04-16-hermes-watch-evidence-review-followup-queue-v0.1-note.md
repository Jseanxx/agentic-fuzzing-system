# Hermes Watch Evidence Review Follow-up Queue v0.1

## 왜 이 단계가 필요했나
Deep crash routing override로 evidence packet은 더 이상 이미 깊게 들어간 critical crash family를 두고 `promote-next-depth`를 말하지 않게 됐다.

하지만 그 직후에도 남은 빈틈이 있었다:
- packet은 `review-current-candidate`를 말함
- 그런데 그 review route가 실제 follow-up artifact/action rail로 바로 연결되진 않았음
- 즉 packet은 똑똑해졌는데, control-plane은 아직 그 말을 실제 작업 큐로 바꾸지 못했다

## 이번에 한 일
- `scripts/hermes_watch.py`
  - `queue_latest_evidence_review_followup(repo_root)` 추가
  - latest `*-llm-evidence.json`를 읽어
    - `suggested_action_code = halt_and_review_harness`
    - `suggested_candidate_route = review-current-candidate`
    인 경우 `harness_review_queue.json`에 실제 follow-up entry를 기록
  - entry에는 다음 spine을 함께 실어 보냄:
    - `llm_evidence_json_path`
    - `llm_evidence_markdown_path`
    - `candidate_route`
    - `crash_fingerprint`
    - `selected_target_stage`
    - current/policy context
  - CLI 추가:
    - `--queue-latest-evidence-review-followup`
- 실제 repo에도 실행해서
  - `fuzz-artifacts/automation/harness_review_queue.json`
  - `fuzz-records/refiner-plans/...`
  - `fuzz-records/refiner-orchestration/...`
  artifact까지 생성 확인

## 실제 결과
latest deep crash evidence packet 기준:
- `review-current-candidate` packet이 이제 말로만 남지 않음
- 실제로 `harness_review_queue.json`에 `halt_and_review_harness` entry가 생김
- 이어서 `--prepare-refiner-orchestration`까지 태워
  - refiner plan
  - orchestration manifest
  - subagent prompt
  artifact가 생성됨

즉 이제 deep crash review route는
- packet
- queue
- orchestration artifact
까지 이어지는 실제 rail이 됐다.

## 의미
이 단계는 작지만 중요하다.

이전 상태:
- LLM packet이 review를 권고
- 하지만 operator/daemon이 그걸 따로 해석해야 했음

현재 상태:
- review packet이 바로 harness review queue entry가 됨
- 즉 packet의 next action이 실제 control-plane work item으로 바뀜

이건 **LLM routing이 실행 substrate와 더 직접 붙기 시작한 단계**다.

## 한계
- 아직 review queue가 준비된 뒤 실제 subagent launch/verification까지 자동으로 밀어붙이는 건 별도 단계다.
- 지금은 queue + orchestration preparation까지 닫았다.
- 다음 단계는 이 review rail이 실제 triage note/result artifact를 다시 current loop에 먹이는 쪽이다.

## 검증
- `python -m pytest tests/test_hermes_watch.py::HermesWatchLLMEvidencePacketV09Tests tests/test_hermes_watch.py::HermesWatchAutonomousSupervisorTests -q`
- `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/llm_evidence.py tests/test_hermes_watch.py`
- `python -m pytest tests/test_hermes_watch.py -q`
- `python -m pytest tests -q`
- `python scripts/hermes_watch.py --repo /home/hermes/work/fuzzing-jpeg2000 --queue-latest-evidence-review-followup`
- `python scripts/hermes_watch.py --repo /home/hermes/work/fuzzing-jpeg2000 --prepare-refiner-orchestration`
