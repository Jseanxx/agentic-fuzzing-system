# Hermes Watch Duplicate Deep Crash Replay Review Routing v0.1 Checklist

- [x] fresh artifacts/current-status에서 repeated deep duplicate crash family 필요성 재확인
- [x] failing regression tests added for duplicate deep crash replay review routing
- [x] repeated deep duplicate crash가 `review_duplicate_crash_replay`로 승격되도록 policy updated
- [x] duplicate replay review action도 `known_bad.json` evidence를 계속 갱신
- [x] `known_bad.json`에 `first_seen_run` / `last_seen_run` / `occurrence_count` 누적
- [x] `duplicate_crash_reviews.json` registry added
- [x] refiner executor가 duplicate replay review queue를 실제 plan으로 소비 가능
- [x] `pytest -q tests/test_hermes_watch.py -k 'replay_review or duplicate_crash_replay_review'`
- [x] `pytest -q tests/test_hermes_watch.py -k 'duplicate_crash or known_bad or execute_next_refiner_action'`
- [x] `pytest -q`
- [x] real repo bounded rerun에서 `policy_action_code = review_duplicate_crash_replay` 확인
- [x] live `duplicate_crash_reviews.json` + refiner plan artifact 생성 확인
- [ ] duplicate replay review 결과가 actual triage execution + LLM revision closure로 다시 연결됨
