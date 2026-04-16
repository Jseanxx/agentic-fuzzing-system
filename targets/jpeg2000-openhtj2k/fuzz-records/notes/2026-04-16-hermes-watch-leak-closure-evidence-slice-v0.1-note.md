# Hermes Watch Leak Closure Evidence Slice v0.1

- Date: 2026-04-16 19:24:44 KST
- Scope: `scripts/hermes_watch.py`, `scripts/hermes_watch_support/llm_evidence.py`, `tests/test_hermes_watch.py`

## 왜 이 slice를 골랐나
latest fresh artifact는 deep-decode-v3 경로에서 나온 LeakSanitizer leak였다.
그런데 실제 watcher 상태는 이를
- `asan|unknown-location|12312 byte(s) leaked...`
- `artifact_category=crash`
- `policy_action_code=triage-new-crash`
처럼 generic crash로 뭉개고 있었다.

즉 지금 control-plane은 fresh signal을 보고도
- leak인지,
- cleanup/closure 문제인지,
- deeper-stage novelty 문제인지
를 제대로 가르지 못했다.

이 상태로는 다음 LLM intervention이 실제 버그 성격과 어긋난다.

## 확인한 실제 root cause
1. `hermes_watch.py`
   - `CRASH_RE`가 `ERROR: LeakSanitizer`를 잡지 못했다.
   - `top_crash_lines`가 leak 시작 line/stack frame을 충분히 보존하지 못했다.
   - 그래서 `build_crash_signature(...)`가 leak run에서도 `AddressSanitizer` summary만 보고 `asan`으로 기울었다.
2. `llm_evidence.py`
   - raw signal summary가 `LeakSanitizer`를 별도 라벨로 유지하지 않았다.
   - evidence packet은 stale `current_status.json`을 그대로 믿어 leak-specific objective를 세우지 못했다.

## 이번에 바꾼 것
### 1) watcher leak excerpt 보강
- `CRASH_RE`에
  - `ERROR: LeakSanitizer`
  - `SUMMARY: LeakSanitizer`
  추가
- crash 시작 뒤 stack/location line도 `top_crash_lines`에 붙여
  source line이 `unknown-location`으로 날아가지 않게 보강

### 2) leak-aware evidence routing 추가
- `llm_evidence.py`에 `LeakSanitizer` raw signal label 추가
- 새 reason code 추가:
  - `leak-sanitizer-signal`
- 새 objective 추가:
  - `cleanup-leak-closure`
- stale `current_status`가 아직 `artifact_category=crash`, `crash_kind=asan`이어도
  - `fuzz.log`의 `LeakSanitizer` line
  - leak summary (`leaked in`)
  를 근거로 leak reason을 복구하도록 보강

## 결과
- 다음 실제 watcher run부터는 leak excerpt와 source line 보존이 더 정확해진다.
- 이미 stale current-status가 남아 있는 현재 상태에서도 새 evidence packet은 latest run을
  - `leak-sanitizer-signal`
  - `cleanup-leak-closure`
  - `halt_and_review_harness`
  - `review-current-candidate`
  로 읽는다.
- 즉 fresh signal이 crash noise로 사라지지 않고 cleanup/closure revision 방향으로 전달되기 시작했다.

## 검증
- `pytest -q tests/test_hermes_watch.py`
- `pytest -q`
- `python scripts/hermes_watch.py --repo /home/hermes/work/fuzzing-jpeg2000 --write-llm-evidence-packet`

## 아직 남은 한계
- 이미 저장된 `fuzz-artifacts/current_status.json`과 run-history entry는 과거 run 기준이라 leak로 재분류되어 있지 않다.
- 이번 slice는 future classification과 present evidence repair를 고친 것이지, 과거 artifact registry 전체를 backfill한 것은 아니다.
- next safe step은 latest leak artifact를 기준으로 실제 cleanup path/allocator free closure를 triage하는 것이다.
