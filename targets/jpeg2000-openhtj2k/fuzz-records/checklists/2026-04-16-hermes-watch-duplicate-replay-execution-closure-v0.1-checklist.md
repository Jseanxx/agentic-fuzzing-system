# Hermes Watch duplicate replay execution closure v0.1 checklist

- [x] fresh state에서 duplicate review rail이 compare-only 상태임을 확인
- [x] failing test 추가: duplicate replay execution artifact write
- [x] failing test 추가: refiner executor result에 duplicate replay execution summary 반영
- [x] failing test 추가: replay command가 symbolized offline replay env를 강제
- [x] `execute_duplicate_crash_replay_probe(...)` 추가
- [x] duplicate review entry에 replay execution status/log/signature/path 저장
- [x] duplicate review plan에 `## Replay Execution` section 추가
- [x] llm evidence markdown duplicate review section에 replay execution fields 노출
- [x] targeted regression: `pytest -q tests/test_hermes_watch.py -k 'duplicate_crash_review_context or duplicate_crash_replay_probe_writes_execution_artifacts or duplicate_crash_replay_execution_summary or run_duplicate_crash_replay_command_enables_symbolized_replay'`
- [x] broader regression: `pytest -q tests/test_hermes_watch.py -k 'duplicate_crash or llm_evidence'`
- [x] full regression: `pytest -q`
- [x] live duplicate review entry 대상으로 bounded replay execution artifact 생성
- [x] canonical docs update

## cold check
- solved: duplicate review rail이 plan-only 상태로 멈추는 문제
- solved: offline replay가 `symbolize=0` 때문에 `unknown-location`으로 흐려지던 문제
- not solved: minimization closure
- not solved: replay result를 자동 revision routing으로 닫는 정책
