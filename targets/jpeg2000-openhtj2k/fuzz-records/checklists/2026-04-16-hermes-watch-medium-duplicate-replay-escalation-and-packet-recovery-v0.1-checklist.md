# Checklist — medium duplicate replay escalation and packet recovery v0.1

- Date: 2026-04-16 22:00:53 KST
- Goal: repeated medium duplicate family가 replay review rail과 latest LLM packet에서 다시 보이게 만들기

## TDD / implementation
- [x] medium duplicate가 `review_duplicate_crash_replay`로 승격되는 regression test 추가
- [x] repeated duplicate status에서도 duplicate review context를 packet이 복구하는 regression test 추가
- [x] RED 확인
- [x] 최소 구현으로 policy 조건 확장
- [x] 최소 구현으로 duplicate review registry recovery 완화

## Verification
- [x] `pytest -q tests/test_hermes_watch.py -k 'escalates_repeated_medium_duplicate_to_replay_review or recovers_duplicate_review_context_for_repeated_duplicate_status'`
- [x] `pytest -q tests/test_hermes_watch.py -k 'duplicate_crash or corpus_refinement or llm_evidence or decide_policy_action'`
- [x] `pytest -q`

## Live closure
- [x] latest `coding_units.cpp:3076` family에 대해 duplicate replay review entry 실제 기록
- [x] first/latest artifact bounded replay actual 실행
- [x] replay markdown / plan artifact 생성 확인
- [x] refreshed LLM packet이 `minimize_and_reseed`를 제안하는지 확인

## Remaining
- [ ] `coding_units.cpp:3076` replay-derived `minimize_and_reseed` execution
- [ ] bounded rerun으로 reseed 효과 측정
- [ ] remote/proxmox loop 연결
