# Hermes Watch Leak Signature Capture Hardening v0.1

- Date: 2026-04-16 19:33:43 KST
- Scope: `scripts/hermes_watch.py`, `tests/test_hermes_watch.py`

## 왜 이 slice를 골랐나
최신 fresh artifact(`fuzz-artifacts/runs/20260416_183444_1d5b676`)는 deep-decode-v3 경로에서 LeakSanitizer leak를 냈다.
그런데 실제 watcher signature는 여전히
- `asan|unknown-location|12312 byte(s) leaked...`
- `artifact_category=crash`
- `crash_location=null`
처럼 남아 있었다.

즉 evidence packet은 leak-aware로 복구되기 시작했지만, 정작 watcher의 원본 crash capture는
- allocator frame에 끌려가고
- summary / artifact line을 놓치고
- leak를 stage/profile/triage 품질이 낮은 generic crash처럼 기록하는 상태였다.

이건 진짜 autonomous loop 품질을 깎는다.
왜냐면 dedup, stage reasoning, artifact preservation, 다음 action routing이 모두 원본 signature 품질에 묶여 있기 때문이다.

## 확인한 root cause
실제 최신 `fuzz.log`를 현재 `Metrics` 경로로 다시 먹여 보니:
- crash context line cap 때문에 long leak stack에서 `SUMMARY` / `artifact` line이 잘릴 수 있었고
- `extract_primary_location(...)`가 leak stack의 첫 project source frame이 아니라 allocator helper인 `utils.hpp:252`를 먼저 집는 구조였다.

즉 leak가 실제로는 `coding_units.cpp:3927`에서 보이는데,
watcher는 long leak stack에서 allocator-heavy 앞부분만 보고 signature를 만들기 쉬운 상태였다.

## 이번에 바꾼 것
1. crash context capture hardening
   - `CRASH_CONTEXT_LINE_LIMIT = 20` 도입
   - leak path에서 `Direct leak of ...` 라인도 context에 보존
   - context가 꽉 찬 뒤에도 아직 없는 `SUMMARY` / `Test unit written to ...` line은 강제로 보존하도록 수정

2. leak primary location selection hardening
   - stack frame 파싱을 먼저 수행
   - `posix_memalign`, `AlignedLargePool::alloc`, `source/core/common/` 같은 allocator/common helper frame은 leak primary location 후보에서 건너뜀
   - 그 다음 first meaningful project frame을 primary location으로 선택

## 바뀐 실제 효과
같은 최신 `fuzz.log`를 새 코드로 다시 읽으면 signature가 이제:
- `kind = leak`
- `location = coding_units.cpp:3927`
- `summary = 12312 byte(s) leaked in 1 allocation(s).`
- `artifact_path = .../crashes/leak-272a1b...`
- `fingerprint = leak|coding_units.cpp:3927|12312 byte(s) leaked in 1 allocation(s).`
으로 나온다.

즉 이제 다음 watcher run부터는 leak가
- unknown-location generic crash가 아니라
- 실제 deep-decode-side location과 artifact를 가진 leak signature
로 기록될 수 있다.

## 검증
- RED:
  - `pytest -q tests/test_hermes_watch.py -k 'preserve_leak_summary_artifact_and_deep_project_frame_when_allocator_frames_are_first'`
  - 실패 확인: `utils.hpp:252` 선택 또는 `artifact_path=None`
- GREEN:
  - 동일 테스트 통과
- targeted regression:
  - `pytest -q tests/test_hermes_watch.py -k 'leak or LeakSanitizer or classify_artifact_event_prefers_leak_over_generic_crash or decide_policy_action_handles_leak or build_llm_evidence_packet_v9_routes_leak_signal_to_reviewable_cleanup_objective'`
- full regression:
  - `pytest -q`
- real-log replay:
  - 최신 `fuzz.log` 재파싱 결과 `leak|coding_units.cpp:3927|...` 및 artifact path 복구 확인

## 아직 남은 한계
- `fuzz-artifacts/current_status.json`, `run_history.json`, `crash_index.json`는 이미 예전 signature로 써진 상태라 자동 backfill되지 않는다.
- 즉 이번 slice는 **다음 run부터 원본 watcher 기록 품질을 올리는 단계**지, 과거 artifact registry를 일괄 수선한 단계는 아니다.
- 현재 evidence packet은 raw log body 덕분에 leak objective를 복구하지만, canonical current_status는 아직 stale하다.

## 다음 best move
1. backfill/rehydrate slice
   - latest report/fuzz.log를 읽어 stale `current_status.json` / `run_history.json` / `crash_index.json`를 안전하게 재생성하거나 repair하는 경로 추가
2. 그 다음 bounded rerun
   - 새 signature가 실제 current_status/report/index에 반영되는지 확인
3. 그 위에서 leak closure 쪽 revision/candidate routing을 더 직접 밀기
