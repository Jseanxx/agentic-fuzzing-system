# Hermes Watch LLM evidence sync and duplicate review rehydration v0.1

- Date: 2026-04-16
- Scope: `scripts/hermes_watch.py`, `scripts/hermes_watch_support/llm_evidence.py`, `tests/test_hermes_watch.py`

## 왜 이 단계를 골랐나
현재 true north에서 가장 아픈 끊김은 `latest state -> LLM handoff`였다.

실제 상태 점검 결과:
- `fuzz-artifacts/current_status.json`는 이미 최신 duplicate crash를 가리키고 있었는데,
- `fuzz-records/llm-evidence/openhtj2k-llm-evidence.json`는 예전 smoke-failed 상태를 그대로 들고 있었다.

즉 control-plane은 최신 crash를 기록했지만, LLM에게 건네는 canonical packet이 stale이라
`artifact preservation -> trigger -> LLM-guided revision` 연결이 느슨했다.

추가로 live rerun을 해보니 또 다른 구멍이 보였다.
- `review_duplicate_crash_replay` registry entry는 최초 생성 후에는 새 recurrence를 반영하지 못했다.
- 이유는 `duplicate_crash_reviews.json`가 unique key 중복 시 append만 막고 기존 entry를 refresh하지 않았기 때문이다.
- 그래서 duplicate review plan/packet이 있어도 first/latest lineage가 실제 최신 recurrence를 못 따라갈 수 있었다.

## root cause
1. watcher 종료 경로(build-failed / smoke-failed / final crash/ok)에서 `write_llm_evidence_packet(...)`가 자동 호출되지 않았다.
2. `duplicate_crash_reviews.json`는 create-only 동작이라 existing duplicate family recurrence를 merge/update하지 못했다.
3. LLM evidence packet도 duplicate review registry/plan context를 직접 surface하지 않았다.

## 이번에 바꾼 것
### 1) watcher 종료 시 LLM evidence packet 자동 refresh
- `refresh_llm_evidence_packet_best_effort(repo_root)` 추가
- build failure, smoke failure, final run 종료 경로에서 report/status write 뒤 자동 호출
- 결과: latest `current_status`와 packet이 자동 동기화됨

### 2) duplicate review registry merge/update 지원
- `record_refiner_entry(..., merge_existing=True)` 추가
- `_merge_refiner_entry(...)`로 non-empty field만 보수적으로 갱신
- `review_duplicate_crash_replay` path는 create-only 대신 merge_existing 사용
- 기존 plan/status 같은 field는 유지하면서
  - `run_dir`
  - `report_path`
  - `last_seen_run`
  - `occurrence_count`
  - `latest_artifact_path`
  - `artifact_paths`
  를 최신 recurrence로 refresh 가능하게 만듦

### 3) LLM evidence packet에 duplicate review context 노출
- `llm_evidence.py`에서 `duplicate_crash_reviews.json` lookup 추가
- `duplicate_crash_review` payload를 packet에 포함
- markdown에도 `## Duplicate Crash Review` section 추가
- `suggested_next_inputs`에 `duplicate crash review plan and lineage`를 조건부 추가

## TDD / verification
### RED
- `pytest -q tests/test_hermes_watch.py -k 'duplicate_crash_review_context or writes_llm_evidence_packet_automatically'`
  - initial 2 fail
- `pytest -q tests/test_hermes_watch.py -k 'refreshes_existing_duplicate_crash_review_entry'`
  - initial 1 fail

### GREEN
- `pytest -q tests/test_hermes_watch.py -k 'duplicate_crash_review_context or writes_llm_evidence_packet_automatically or refreshes_existing_duplicate_crash_review_entry'`
  - pass
- `pytest -q tests/test_hermes_watch.py -k 'duplicate_crash or llm_evidence'`
  - 31 pass
- `pytest -q`
  - 317 pass

### live verification
1. bounded rerun:
   - `python scripts/hermes_watch.py --repo /home/hermes/work/fuzzing-jpeg2000 --max-total-time 5 --no-progress-seconds 30`
2. 확인한 것:
   - `openhtj2k-llm-evidence.json`의 `current_status.updated_at`가 latest run과 자동 동기화됨
   - packet이 더 이상 stale smoke-failed snapshot을 들고 있지 않음
   - duplicate review action일 때 packet이 `duplicate_crash_review` context를 포함함
3. bounded rerun에서 관측된 신호:
   - `20260416_205116_1d5b676`: repeated deep duplicate `j2kmarkers.cpp:52` family recurrence
   - `20260416_205450_1d5b676`: separate duplicate SEGV family `coding_units.cpp:3076`

## 왜 의미 있었나
이 단계는 control-plane ornament가 아니라 실제 LLM handoff 품질 복구다.

이제:
- 최신 run이 끝나면 packet이 자동 갱신되고,
- duplicate review rail이 있을 때 LLM이 compare plan/lineage를 같은 packet에서 볼 수 있고,
- 같은 duplicate family가 다시 나와도 registry가 stale completed entry로 고정되지 않는다.

즉 `latest evidence -> LLM-readable packet`과 `duplicate review recurrence memory` 두 군데의 실제 loop 끊김을 메웠다.

## 아직 남은 한계
- `review_duplicate_crash_replay`는 여전히 plan/lineage 중심이다. 실제 replay/minimization 실행 결과를 자동 수집하지는 않는다.
- duplicate review packet은 registry/plan을 surface하지만, replay 결과를 다시 objective로 닫는 closure는 아직 없다.
- remote/proxmox closure는 아직 별도 축이다.

## 다음 best move
1. `duplicate replay execution closure`
   - duplicate review plan을 실제 bounded replay/minimization 실행 artifact로 연결
2. `triage result -> llm revision closure`
   - replay 결과가 evidence packet/objective/action routing으로 다시 닫히게 만들기
3. `remote/proxmox parity on refreshed packet`
   - local packet freshness가 remote loop에서도 유지되는지 검증
