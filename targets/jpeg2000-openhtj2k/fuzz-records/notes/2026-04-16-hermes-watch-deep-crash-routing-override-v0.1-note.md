# Hermes Watch Deep Crash Routing Override v0.1

## 왜 이 단계가 필요했나
latest autonomous run에서 이미 deep stage(`ht-block-decode`)의 critical ASan crash가 나왔는데,
LLM evidence packet은 여전히:
- `llm_objective = deeper-stage-reach`
- `suggested_action_code = shift_weight_to_deeper_harness`
- `suggested_candidate_route = promote-next-depth`
를 내고 있었다.

이건 냉정하게 stale routing이다.
이미 deeper path에 들어갔고, 새 deep crash family도 잡혔는데 더 깊게 밀라는 건 잘못된 즉시 행동이다.

## 이번에 고친 것
- `scripts/hermes_watch_support/llm_evidence.py`
  - `_link_objective_to_routing(...)`가 이제 `current_status`도 본다.
  - 다음 조건이면 deeper push를 review route로 override한다:
    - `outcome = crash`
    - `crash_detected = true`
    - 그리고 아래 중 하나
      - `policy_profile_severity in {high, critical}`
      - `crash_stage_class = deep`
      - `crash_stage_depth_rank >= 3`
  - override reason을 linkage summary에 남긴다:
    - `deep-stage-crash-already-reached`
- `tests/test_hermes_watch.py`
  - deep critical crash가 이미 있는 packet에서는 더 깊게 밀지 않고
    - `halt_and_review_harness`
    - `review-current-candidate`
    로 꺾이는 regression test 추가

## 실제 결과
latest packet 재생성 결과:
- 기존:
  - `shift_weight_to_deeper_harness`
  - `promote-next-depth`
- 변경 후:
  - `halt_and_review_harness`
  - `review-current-candidate`
- linkage summary에는
  - `override=deep-stage-crash-already-reached`
  가 남는다.

## 의미
이제 evidence packet이 단순히 "더 깊게 가라"를 반복하지 않는다.
이미 deep crash를 잡은 상태에서는:
- current crash family review
- triage 우선
- harness/decoder boundary 검토
쪽으로 즉시 행동이 더 맞게 꺾인다.

즉 이 단계는 **LLM 개입을 더 많이 하는 것**이 아니라,
**LLM 개입이 이미 잡은 deep signal을 무시하지 않게 만드는 routing hygiene 단계**다.

## 한계
- 이건 still heuristic override다.
- 아직 crash novelty / repro quality / triage cost까지 같이 계산하는 건 아니다.
- 다음 단계는 deep crash review route가 실제 follow-up artifact/triage task로 더 직접 이어지는지 닫는 것이다.

## 검증
- `python -m pytest tests/test_hermes_watch.py::HermesWatchLLMEvidencePacketV09Tests -q`
- `python -m py_compile scripts/hermes_watch_support/llm_evidence.py tests/test_hermes_watch.py`
- `python -m pytest tests/test_hermes_watch.py -q`
- `python -m pytest tests -q`
- `python scripts/hermes_watch.py --repo /home/hermes/work/fuzzing-jpeg2000 --write-llm-evidence-packet`
