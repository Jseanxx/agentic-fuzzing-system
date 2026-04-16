# Hermes Watch Duplicate Crash Compare Plan Enrichment v0.1

## 왜 이 단계가 필요했나
직전 단계에서 `review_duplicate_crash_replay` rail 자체는 생겼지만,
실제 생성되는 refiner plan은 거의 빈 껍데기였다.

즉 control-plane은 duplicate deep crash family를 review lane으로 보내도,
그 다음 LLM/operator가 바로 쓸 수 있는 정보는 부족했다.
특히 빠져 있던 것은:
- first seen vs latest run/report/artifact 비교축
- duplicate family 누적 횟수
- artifact-preserving 비교 명령

이 상태는 rail은 있지만 triage closure 입력 품질이 약한 상태였다.

## 이번에 고친 것
- `scripts/hermes_watch.py`
  - crash index repair/update 결과가 이제 duplicate family의
    - `first_seen_report`
    - `last_seen_report`
    - `first_artifact_path`
    - `artifacts`
    를 같이 반환한다.
  - `apply_policy_action(...)`의 `review_duplicate_crash_replay` registry entry가 이제
    - `first_seen_report_path`
    - `last_seen_run`
    - `first_artifact_path`
    - `artifact_paths`
    를 함께 저장한다.
  - `write_refiner_plan(...)`가 duplicate replay review action에서는
    - `## Duplicate Crash Comparison`
    - `## Suggested Low-Risk Commands`
    섹션을 자동 생성한다.
  - subagent/cron prompt도 duplicate review context를 더 직접 받도록 보강했다.
- `tests/test_hermes_watch.py`
  - duplicate review registry가 first report/artifact lineage를 유지하는지 검증 추가
  - duplicate review refiner plan이 실제로 compare section + bounded command를 쓰는지 regression test 추가

## 검증
- RED
  - `pytest -q tests/test_hermes_watch.py -k 'duplicate_crash_compare_and_replay_plan or routes_duplicate_crash_replay_review_into_refiner_queue'`
  - 초기 1 fail 확인 (`## Duplicate Crash Comparison` 부재)
- GREEN
  - 같은 명령 재실행 -> 2 pass
- 추가 회귀 확인
  - `pytest -q tests/test_hermes_watch.py -k 'duplicate_crash or review_duplicate_crash_replay or execute_next_refiner_action_processes_review_duplicate_crash_replay'`
  - 6 pass
- 전체 회귀 확인
  - `pytest -q`
  - 312 pass
- live artifact refresh
  - 기존 `duplicate_crash_reviews.json` entry를 crash index lineage로 보강하고
  - `fuzz-records/refiner-plans/review_duplicate_crash_replay-home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_202702_1d5b676.md`
    를 재생성해
    - first/latest run/report/artifact 비교
    - `sha1sum ...`
    - `cmp -l ... || true`
    - report skim command
    가 실제로 들어간 것 확인

## 의미
이번 단계는 새 기능이라기보다,
이미 만든 duplicate review rail을 실제 triage 입력 품질이 있는 plan rail로 올린 것이다.

즉 이제 duplicate deep crash review는
- 단순 "검토하라" 수준이 아니라
- 무엇을 비교해야 하는지
- 어떤 artifact를 우선 봐야 하는지
- 어떤 bounded command로 시작할지
까지 바로 주는 쪽으로 한 칸 더 닫혔다.

이건 true north 기준에서 `artifact preservation -> trigger/review input`의 입력 품질 개선이다.
아직 actual replay/minimization execution closure는 아니지만,
그 전 단계에서 가장 싸고 안전하게 큰 병목 하나를 줄인 셈이다.

## 한계
- 아직 실제 `triage` mode replay/minimization 실행 결과를 자동 수집하지 않는다.
- compare section은 metadata 중심이며 semantic diff summary까지는 아니다.
- remote/proxmox 쪽 duplicate family closure에는 아직 직접 연결되지 않았다.

## 다음 단계
- duplicate review plan을 실제 replay/minimization execution artifact와 다시 연결하기
- first/latest artifact의 hash/byte diff뿐 아니라 report/body signal 차이를 자동 요약할지 검토하기
- triage execution 결과가 evidence packet / revision objective / rerun 추천까지 닫히는지 연결하기
