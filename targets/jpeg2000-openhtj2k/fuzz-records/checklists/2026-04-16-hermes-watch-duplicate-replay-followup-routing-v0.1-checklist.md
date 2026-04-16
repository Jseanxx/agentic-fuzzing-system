# Duplicate replay follow-up routing v0.1 checklist

- Date: 2026-04-16 21:28:15 KST
- Status: completed

## 목표
stable duplicate replay evidence를 compare-only artifact에서 `minimize_and_reseed` revision queue 입력으로 승격한다.

## 체크리스트
- [x] duplicate replay follow-up builder test first 추가
- [x] duplicate replay executor가 follow-up queue를 기록하는 regression test 추가
- [x] duplicate-review llm evidence routing override regression test 추가
- [x] RED 확인
- [x] `scripts/hermes_watch.py`에 follow-up builder/recorder 구현
- [x] `execute_next_refiner_action(...)`에 replay follow-up lineage 추가
- [x] `llm_evidence.py`에 duplicate replay routing override 추가
- [x] targeted pytest 재실행
- [x] full `pytest -q` 통과
- [x] existing duplicate replay entry에서 live corpus refinement entry 생성
- [x] `current-status.md` / `progress-index.md` 갱신

## verification commands
- `pytest -q tests/test_hermes_watch.py -k 'duplicate_crash_replay_followup or duplicate_crash_review_context or records_duplicate_replay_followup_corpus_refinement'`
- `pytest -q tests/test_hermes_watch.py -k 'duplicate_crash or llm_evidence or minimize_and_reseed'`
- `pytest -q`

## live artifacts
- `fuzz-artifacts/automation/corpus_refinements.json`
- `fuzz-artifacts/automation/duplicate_crash_reviews.json`
- `fuzz-records/duplicate-crash-replays/home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_202702_1d5b676.md`

## cold note
이번 단계는 minimization 실행이 아니라 routing closure다.
즉 아직 자동 minimizer는 없지만, stable duplicate family를 다시 같은 방식으로 재발견하는 관성을 줄일 입력 artifact는 생겼다.
