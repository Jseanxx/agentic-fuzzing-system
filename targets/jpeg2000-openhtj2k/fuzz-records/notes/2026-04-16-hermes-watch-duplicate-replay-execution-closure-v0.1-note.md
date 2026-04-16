# Hermes Watch duplicate replay execution closure v0.1

- Date: 2026-04-16
- Scope: `scripts/hermes_watch.py`, `scripts/hermes_watch_support/llm_evidence.py`, `tests/test_hermes_watch.py`

## 왜 이 단계를 골랐나
fresh 상태를 다시 보니 `review_duplicate_crash_replay` rail은 이미 plan/lineage는 만들고 있었지만 실제 bounded replay 결과는 비어 있었다.

즉 현재 상태는:
- `duplicate_crash_reviews.json`에 duplicate family review entry는 있음
- compare plan도 있음
- 하지만 실제 first/latest artifact를 다시 실행한 결과, 어떤 harness로 돌렸는지, exit code가 어땠는지, 재생 시 signature가 유지되는지는 registry에 없었음

이 상태는 true north 관점에서 `artifact preservation -> trigger -> rerun`이 아직 compare-only 문서 단계에 머문다는 뜻이다.

## root cause
1. `execute_next_refiner_action(...)`가 `review_duplicate_crash_replay`를 만나도 plan만 쓰고 끝났다.
2. duplicate review entry에는 replay execution artifact/log/signature 필드가 없었다.
3. LLM markdown surface도 duplicate review의 executor plan까지만 보여주고 replay execution 상태는 노출하지 않았다.
4. live replay를 해보니 offline triage helper가 `symbolize=0`를 유지해 file:line 없는 `unknown-location` signature로 흐려졌다.

## 이번에 바꾼 것
### 1) bounded duplicate replay executor 추가
- `execute_duplicate_crash_replay_probe(...)` 추가
- first/latest artifact를 같은 harness로 직접 replay
- 결과로 다음을 artifact-first로 저장:
  - JSON report
  - Markdown summary
  - first/latest raw replay log
  - sha1 equality / byte equality
  - first/latest exit code
  - first/latest replay signature
  - signal line summary

### 2) duplicate review plan에 replay execution section 추가
- 기존 `## Duplicate Crash Comparison` 아래에
- `## Replay Execution` section이 붙도록 확장
- 이제 plan만 열어도
  - 어떤 harness로 replay했는지
  - 두 artifact가 같은 crash로 다시 닫히는지
  - exit code와 signature가 무엇인지
  바로 보인다.

### 3) refiner executor가 duplicate replay 실행 결과를 실제 registry/result에 반영
- `execute_next_refiner_action(...)`가 `review_duplicate_crash_replay`일 때
  - replay execution helper 실행
  - registry entry에 execution status/path/signature 저장
  - 그 상태를 포함한 최신 plan 재생성
- 즉 duplicate review rail이 plan-only가 아니라 bounded execution artifact를 남기는 rail로 올라갔다.

### 4) LLM evidence markdown에 replay execution 상태 노출
- duplicate review section에 추가:
  - `replay_execution_status`
  - `replay_execution_markdown_path`
  - `first_replay_exit_code`
  - `latest_replay_exit_code`

### 5) offline replay symbolization 복구
- `run_duplicate_crash_replay_command(...)`에서 replay용 `ASAN_OPTIONS`를 `symbolize=1`로 강제
- `llvm-symbolizer`가 있으면 `ASAN_SYMBOLIZER_PATH`도 같이 넣음
- live rerun 결과 `unknown-location`이 아니라 `j2kmarkers.cpp:52` file:line signature로 복구됨

## TDD / verification
### RED
- `pytest -q tests/test_hermes_watch.py -k 'duplicate_crash_replay_probe_writes_execution_artifacts or duplicate_crash_replay_execution_summary'`
  - initial 2 fail
- `pytest -q tests/test_hermes_watch.py -k 'run_duplicate_crash_replay_command_enables_symbolized_replay'`
  - initial 1 fail (`symbolize=0` 유지)

### GREEN
- `pytest -q tests/test_hermes_watch.py -k 'duplicate_crash_review_context or duplicate_crash_replay_probe_writes_execution_artifacts or duplicate_crash_replay_execution_summary or run_duplicate_crash_replay_command_enables_symbolized_replay'`
  - pass
- `pytest -q tests/test_hermes_watch.py -k 'duplicate_crash or llm_evidence'`
  - 34 pass
- `pytest -q`
  - 322 pass

### live verification
1. existing duplicate review entry 대상으로 실제 replay execution 수행
2. 생성 artifact:
   - `fuzz-records/duplicate-crash-replays/home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_202702_1d5b676.json`
   - `fuzz-records/duplicate-crash-replays/home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_202702_1d5b676.md`
   - updated plan: `fuzz-records/refiner-plans/review_duplicate_crash_replay-home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_202702_1d5b676.md`
3. 확인한 것:
   - first/latest replay exit code 둘 다 `-6`
   - first/latest replay signature 둘 다 `asan|j2kmarkers.cpp:52|heap-buffer-overflow ...`
   - initial live run의 `unknown-location` 문제가 symbolized replay 재실행 후 `j2kmarkers.cpp:52`로 복구됨

## 왜 의미 있었나
이 단계는 문서 미화가 아니다.

이제 duplicate family review는:
- compare 계획만 세우는 단계가 아니라
- 실제 bounded replay 증거를 남기고
- 그 결과를 registry/plan/LLM surface에 다시 올리는 단계가 됐다.

즉 `artifact preservation -> trigger/review -> bounded rerun evidence`까지는 실제로 한 칸 닫혔다.

## 아직 남은 한계
- 아직 minimization 자체는 하지 않았다. 지금은 replay execution closure v0.1이다.
- current latest `current_status`가 다른 duplicate family(`coding_units.cpp:3076`)를 가리키고 있어서, 이번 replay artifact가 latest packet의 중심에는 아직 안 올라온다.
- replay 결과를 자동으로 `seed/harness/strategy revision` objective로 바꾸는 정책은 아직 없다.
- remote/proxmox closure는 여전히 별도다.

## 다음 best move
1. `duplicate replay result -> revision routing`
   - replay signature/stability를 보고 shallow duplicate면 quarantine or deprioritize, deeper family면 review/triage 가중치로 바로 연결
2. `bounded minimization closure`
   - replay가 안정적인 duplicate family에 대해서만 비파괴 minimization artifact를 추가
3. `coding_units.cpp:3076 duplicate family review 승격 조건 재검토`
   - 지금 latest family는 medium-stage duplicate라 review rail에 못 올라오는데, 실제 가치가 더 큰지 규칙을 다시 봐야 한다.
