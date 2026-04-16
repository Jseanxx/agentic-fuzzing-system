# Hermes Watch Rehydrated Report Sync v0.1 Checklist

- 날짜: 2026-04-16 20:00:40 KST
- 상태: completed

## 목표
rehydrate 이후 canonical state만 맞는 상태를 끝내고, 같은 run의 `FUZZING_REPORT.md`도 leak-aware state로 동기화한다.

## 체크리스트
- [x] stale leak report mismatch를 실제 latest artifact에서 확인
- [x] report rewrite를 위한 failing test를 먼저 추가
- [x] rehydrate path가 report section들을 다시 쓰도록 최소 구현
- [x] targeted rehydrate regression test 통과
- [x] leak-related targeted test 묶음 통과
- [x] full `pytest -q` 통과
- [x] 실제 latest run에 rehydrate 재실행
- [x] `FUZZING_REPORT.md`가 leak classification/policy/fingerprint/excerpt로 갱신됐는지 확인
- [x] LLM evidence packet 재생성
- [x] canonical docs와 note/checklist 업데이트

## 실행/검증 명령
- `pytest -q tests/test_hermes_watch.py -k rehydrate_run_artifacts_reclassifies_stale_leak_metadata_without_duplicating_history`
- `pytest -q tests/test_hermes_watch.py -k 'rehydrate_run_artifacts or leak or LeakSanitizer or classify_artifact_event_prefers_leak_over_generic_crash or decide_policy_action_handles_leak or build_crash_signature'`
- `pytest -q`
- `python scripts/hermes_watch.py --repo /home/hermes/work/fuzzing-jpeg2000 --rehydrate-run-artifacts --rehydrate-run-dir /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_183444_1d5b676`
- `python scripts/hermes_watch.py --repo /home/hermes/work/fuzzing-jpeg2000 --write-llm-evidence-packet`

## 확인 포인트
- `report_rewritten: true`
- latest report의 `artifact_category: leak`
- latest report의 `policy_action_code: triage-leak-and-consider-coverage-policy`
- latest report의 `crash_fingerprint: leak|coding_units.cpp:3927|12312 byte(s) leaked in 1 allocation(s).`
- excerpt에 `LeakSanitizer`/artifact path/project frame 보존

## 남은 것
- [ ] bounded rerun으로 새 run이 처음부터 same leak-aware report/state를 생성하는지 확인
- [ ] `coding_units.cpp:3927` leak cleanup closure 자체를 실제로 점검
- [ ] 필요 시 `Recommended Next Action`를 policy/objective-aware로 교체
