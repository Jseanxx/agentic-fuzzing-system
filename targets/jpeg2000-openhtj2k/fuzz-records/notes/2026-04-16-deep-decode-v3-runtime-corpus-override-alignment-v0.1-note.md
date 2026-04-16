# Deep-decode-v3 runtime corpus override alignment v0.1

- Date: 2026-04-16 22:19:23 KST
- Scope: active deep-decode-v3 fuzz rerun contract, `run-fuzz-mode.sh` wrapper realism, corpus override propagation

## 왜 이 단계가 필요했나
fresh inspection에서 `run-fuzz-mode.sh coverage`는 `corpus_dir=/home/hermes/work/fuzzing-jpeg2000/fuzz/corpus/coverage`를 출력했지만, 실제 libFuzzer는 `INFO: 8 files found in fuzz/corpus-afl/deep-decode-v3`를 로드했다.

즉 문제는 wrapper가 아니라 active profile contract였다. `openhtj2k-target-profile-v1.yaml`의 adapter `fuzz_command`가 `CORPUS_DIR=fuzz/corpus-afl/deep-decode-v3`를 literal로 박고 있어서, triage/coverage/regression wrapper가 corpus를 바꿔도 실제 fuzzer 호출에서 덮어써졌다.

이건 문서상의 불일치가 아니라 실제 loop bug다. `minimize_and_reseed`로 bucket을 잘 만들어도 rerun이 그 corpus를 보지 않으면 `revision/reseed -> rerun`이 끊긴다.

## 이번에 바꾼 것
1. `tests/test_aflpp_setup.py`
   - deep-decode-v3 target profile contract가 env-override friendly shell form을 유지하는지 regression test로 고정
   - 기대 contract:
     - `FUZZER_BIN=${FUZZER_BIN:-build-fuzz-libfuzzer/bin/open_htj2k_deep_decode_focus_v3_fuzzer}`
     - `CORPUS_DIR=${CORPUS_DIR:-fuzz/corpus-afl/deep-decode-v3}`
2. `fuzz-records/profiles/openhtj2k-target-profile-v1.yaml`
   - adapter `fuzz_command`를 hard-pinned literal에서 env-default shell expansion으로 변경
   - `meta.updated_at` 갱신

## 검증
### RED
- `pytest -q tests/test_aflpp_setup.py -k deep_decode_v3_adapter_contract`
- 초기 결과: 1 fail
- 실패 이유: target profile이 여전히 literal `CORPUS_DIR=fuzz/corpus-afl/deep-decode-v3`를 사용

### GREEN
- 같은 명령 재실행: 1 pass
- `pytest -q tests/test_aflpp_setup.py`: 7 pass
- `pytest -q`: 331 pass

### Live verification
1. fix 전 bounded rerun
   - `MAX_TOTAL_TIME=8 bash scripts/run-fuzz-mode.sh coverage`
   - 실제 output: `INFO: 8 files found in fuzz/corpus-afl/deep-decode-v3`
   - 결론: wrapper override 무효
2. fix 후 bounded rerun
   - 같은 명령 재실행
   - 실제 output: `INFO: 7 files found in /home/hermes/work/fuzzing-jpeg2000/fuzz/corpus/coverage`
   - 생성 보고서: `fuzz-artifacts/modes/coverage/20260416_221832_coverage/FUZZING_REPORT.md`
   - 확인값:
     - command가 env-default contract로 기록됨
     - `cov=53`, `ft=153`, `corpus_units=7`
     - duplicate `asan|j2kmarkers.cpp:52|heap-buffer-overflow ...` family 재현

## 의미
- `run-fuzz-mode.sh`가 active deep-decode-v3 profile에서도 이제 실제 corpus를 바꾸는 wrapper가 됐다.
- 기존 `triage/coverage/regression` split, `minimize_and_reseed`, quarantine rail이 이제 진짜 rerun input에 연결될 수 있다.
- reseed effectiveness measurement를 해도 되는 기반이 생겼다. 전에는 rerun 자체가 잘못된 corpus를 보고 있었으니 측정값이 의미 없었다.

## 아직 남은 것
- 이번 bounded rerun도 `j2kmarkers.cpp:52` duplicate family가 강하게 재발견됐다.
- 즉 contract mismatch는 고쳤지만 finding quality 문제는 그대로다.
- 다음은 active coverage corpus에서 shallow duplicate dominance를 일으키는 toxic seed를 식별/격리하고, 그 전후 novelty/coverage 변화를 계측해야 한다.

## 냉정한 판단
이번 단계는 작은 수정이지만 가치가 크다. control-plane ornament가 아니라, 실제 실행 wrapper가 거짓말하던 상태를 고쳤다. 다만 이걸 finding efficiency 개선으로 과장하면 안 된다. 지금은 rerun contract를 현실과 맞춘 것뿐이고, 다음 단계에서야 제대로 된 reseed/quarantine 실험이 가능하다.
