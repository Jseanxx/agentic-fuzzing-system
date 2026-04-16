# Runtime Hardening Focus — Timeout + Env Parsing

## Why this step first
R20 compile/smoke revision intelligence로 가기 전에, 운영면에서 가장 싼 취약점 두 개를 먼저 줄인다.

1. external subprocess hang
2. invalid integer environment defaults

## Intended effect
- bridge/probe subprocess가 영구 정지로 watcher/refiner 흐름을 막지 않게 함
- 잘못된 env 값 때문에 `main()`이 argparse 이전에 죽는 문제를 제거

## Scope boundary
이 단계는 intentionally small hardening이다.
- lifecycle canonicalization은 아직 안 함
- malformed nested registry 전체 hardening도 아직 안 함
- duplicate-processing/race도 아직 안 함

즉, 이번 단계는 R20 구현 전에 운영면 baseline을 조금 더 안전하게 만드는 준비 작업이다.

## What was actually added
- `launch_bridge_script(...)`에 기본 timeout 추가
- `run_probe_command(...)`에 기본 timeout 추가
- timeout 시 `exit_code=124`와 명시적 timeout output 반환
- `env_int_default(...)` helper 추가
- `main()`의 `MAX_TOTAL_TIME`, `NO_PROGRESS_SECONDS`, `PROGRESS_INTERVAL_SECONDS` default parsing을 safe fallback 방식으로 교체

## Verification
- `python -m pytest tests/test_hermes_watch.py::HermesWatchRuntimeHardeningTests -q` → 3 passed
- `python -m pytest tests/test_hermes_watch.py -q` → 155 passed
- `python -m pytest tests -q` → 174 passed
- `python -m py_compile scripts/hermes_watch.py tests/test_hermes_watch.py` → OK

## Cold take
이번 단계는 작지만 가치 있다.
- external subprocess hang에 대한 가장 싼 방어막이 생겼고
- 잘못된 env 값 하나로 main이 바로 죽는 경로를 제거했다

하지만 여전히:
- lifecycle drift
- malformed nested registry hardening
- duplicate-processing/race
는 다음 보강 대상으로 남는다.
