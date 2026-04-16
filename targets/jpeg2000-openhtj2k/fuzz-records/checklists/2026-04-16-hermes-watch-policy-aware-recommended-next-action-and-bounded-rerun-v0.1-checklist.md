# Hermes Watch Policy-Aware Recommended Next Action + Bounded Rerun v0.1 Checklist

- 날짜: 2026-04-16 20:09:26 KST
- 상태: completed

## 목표
report 말미 `Recommended Next Action`를 policy/objective-aware로 정렬하고, 실제 bounded rerun에서 fresh run도 같은 contract를 자연 생성하는지 확인한다.

## 체크리스트
- [x] report 말미 action summary가 outcome-only hardcode라는 root cause 확인
- [x] failing tests 먼저 추가
- [x] `recommended_action(...)`가 `policy_action` 우선 사용하도록 최소 구현
- [x] `write_report(...)`가 policy-aware action summary를 쓰도록 반영
- [x] `rewrite_rehydrated_report(...)`가 same section도 다시 쓰도록 반영
- [x] targeted regression tests 통과
- [x] full `pytest -q` 통과
- [x] bounded rerun 실제 실행
- [x] fresh report가 policy-aware action summary를 자연 생성하는지 확인
- [x] fresh run이 새 crash family / coverage growth를 남겼는지 확인
- [x] LLM evidence packet 재생성
- [x] canonical docs + note/checklist 업데이트

## 실행/검증 명령
- `pytest -q tests/test_hermes_watch.py -k 'write_report_uses_policy_recommended_action_in_recommended_next_action_section or rehydrate_run_artifacts_reclassifies_stale_leak_metadata_without_duplicating_history'`
- `pytest -q`
- `python scripts/hermes_watch.py --repo /home/hermes/work/fuzzing-jpeg2000 --max-total-time 5 --no-progress-seconds 30`
- `python scripts/hermes_watch.py --repo /home/hermes/work/fuzzing-jpeg2000 --write-llm-evidence-packet`

## 확인 포인트
- latest report `Recommended Next Action`가 `policy_recommended_action`와 같은 방향인지
- `fuzz-artifacts/runs/20260416_200858_1d5b676/FUZZING_REPORT.md`에
  - `policy_action_code: continue_and_prioritize_triage`
  - `policy_matched_triggers: ['deep_signal_emergence']`
  - `crash_stage: ht-block-decode`
  - `Recommended Next Action: Keep the run going but prioritize this new deep-stage crash family in triage.`
- `current_status.json` / LLM evidence가 same fresh run을 기준으로 갱신됐는지

## 남은 것
- [ ] `crash-964206...` 새 family triage/replay 및 toxic-seed 여부 판단
- [ ] parser/marker-length 쪽 specialized triage slice 연결 여부 점검
- [ ] 필요하면 deep-signal-emergence 이후 자동 triage closure/queueing을 더 직접적으로 강화
