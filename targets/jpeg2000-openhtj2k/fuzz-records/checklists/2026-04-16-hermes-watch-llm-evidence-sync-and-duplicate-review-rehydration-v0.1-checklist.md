# Hermes Watch LLM evidence sync and duplicate review rehydration v0.1 checklist

- [x] stale `llm-evidence` packet가 latest `current_status`를 못 따라가는 문제 재현
- [x] duplicate review registry가 existing entry refresh를 못 하는 root cause 확인
- [x] failing test 추가: duplicate review context packet surface
- [x] failing test 추가: build failure 종료 후 llm evidence auto-write
- [x] failing test 추가: existing duplicate review entry refresh
- [x] watcher 종료 경로에 best-effort evidence packet auto refresh 추가
- [x] `record_refiner_entry(..., merge_existing=True)` 도입
- [x] `review_duplicate_crash_replay` path를 merge/update 동작으로 전환
- [x] packet에 `duplicate_crash_review` section 추가
- [x] targeted test: `pytest -q tests/test_hermes_watch.py -k 'duplicate_crash_review_context or writes_llm_evidence_packet_automatically or refreshes_existing_duplicate_crash_review_entry'`
- [x] broader regression: `pytest -q tests/test_hermes_watch.py -k 'duplicate_crash or llm_evidence'`
- [x] full regression: `pytest -q`
- [x] live bounded rerun으로 packet auto-refresh 확인
- [x] canonical docs update

## cold check
- solved: latest run 후 LLM packet stale 문제
- solved: duplicate review registry create-only 문제
- not solved: duplicate replay/minimization actual execution closure
