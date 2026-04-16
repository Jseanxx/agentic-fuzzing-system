# Hermes Watch Leak State Rehydration v0.1

## 왜 이 단계가 필요했나
Leak signature capture hardening 이후에도 latest deep-decode-v3 run의 canonical state는 여전히 stale했다.

구체적으로는:
- `current_status.json`이 `asan|unknown-location|12312 byte(s) leaked...`로 남아 있었고
- `run_history.json` latest entry도 같은 stale fingerprint를 가리켰고
- `crash_index.json`도 leak family를 generic crash처럼 저장하고 있었다.

즉 evidence packet은 leak-aware objective를 복구했는데, control-plane의 canonical spine은 아직 generic crash를 가리키는 불일치가 있었다.

## 이번에 한 일
- `scripts/hermes_watch.py`
  - stale latest run을 `fuzz.log`에서 다시 읽어 crash signature를 재구성하는 repair path를 유지/보강
  - latest run용 repair helper `repair_latest_crash_state(...)` 추가
  - backward-compatible CLI alias `--repair-latest-crash-state` 추가
  - `rehydrate_run_artifacts(...)` / `--rehydrate-run-artifacts --rehydrate-run-dir <run_dir>` 경로로 기존 run artifact를 다시 읽어
    - run `status.json`
    - `fuzz-artifacts/current_status.json`
    - `fuzz-artifacts/automation/run_history.json`
    - `fuzz-artifacts/crash_index.json`
    을 canonical leak signature 기준으로 다시 맞춤
- `tests/test_hermes_watch.py`
  - stale leak metadata가 history duplication 없이 leak fingerprint/category/policy로 복구되는 regression test 추가
  - CLI entrypoint로 same repair path가 0 exit으로 끝나는 regression test 추가

## 실제 결과
latest run `20260416_183444_1d5b676` 기준:
- `artifact_category = leak`
- `artifact_reason = sanitizer-leak`
- `crash_kind = leak`
- `crash_location = coding_units.cpp:3927`
- `crash_fingerprint = leak|coding_units.cpp:3927|12312 byte(s) leaked in 1 allocation(s).`
- `policy_action_code = triage-leak-and-consider-coverage-policy`
- `policy_next_mode = coverage`

`crash_index.json`에서는 stale `asan|unknown-location|...` record가 빠지고 canonical leak fingerprint가 남았다.
`run_history.json` latest entry도 append가 아니라 replace로 수선되어 stale entry duplication이 생기지 않았다.

## 의미
이제 latest leak는 evidence packet에서만 leak처럼 보이는 상태가 아니라, control-plane canonical state 전체가 leak-aware 상태로 정렬됐다.

즉 다음 autonomous loop가:
- stale generic crash fingerprint
- stale crash bucket
- stale triage-new-crash policy
를 다시 먹지 않게 됐다.

## 아직 남은 한계
- `FUZZING_REPORT.md` 본문 excerpt는 예전 stale 표현을 여전히 들고 있을 수 있다.
- 이번 단계는 existing artifact repair까지다.
- 다음에는 bounded rerun으로 report/state가 새 signature를 자연 생성하는지 확인하는 단계가 남는다.

## 검증
- `python -m pytest tests/test_hermes_watch.py::HermesWatchFingerprintTests tests/test_hermes_watch.py::HermesWatchAutonomousSupervisorTests -q`
- `python -m py_compile scripts/hermes_watch.py tests/test_hermes_watch.py`
- `python -m pytest tests/test_hermes_watch.py -q`
- `python -m pytest tests -q`
- `python scripts/hermes_watch.py --repo /home/hermes/work/fuzzing-jpeg2000 --rehydrate-run-artifacts --rehydrate-run-dir /home/hermes/work/fuzzing-jpeg2000/fuzz-artifacts/runs/20260416_183444_1d5b676`
