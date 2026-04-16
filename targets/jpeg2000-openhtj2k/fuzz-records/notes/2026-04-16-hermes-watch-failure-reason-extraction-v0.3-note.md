# 2026-04-16 — failure reason extraction v0.3 note

## 왜 이 단계를 바로 넣었나
v0.2까지는 history-aware reason extraction이 들어갔지만,
아직 packet은 주로 structured artifact field만 읽고 있었다.

그런데 실제 진짜 단서는 종종:
- `smoke.log`
- `build.log`
- `fuzz.log`
본문에 먼저 나타난다.

또 하나의 실사용 blocker는,
`python scripts/hermes_watch.py ...` direct entrypoint가 import-path 문제로 깨진다는 점이었다.

그래서 이번 slice는:
- raw log/body-level signal을 packet에 넣고
- direct script entrypoint 실행성도 같이 복구하는
작은 safe slice로 갔다.

## 이번에 추가한 것
### 1. raw log signal summary
`current_status.report`를 기준으로 sibling log를 읽는다.
- `smoke.log`
- `build.log`
- `fuzz.log`

그리고 sanitizer/runtime-error 스타일 라인을 추출해
`raw_signal_summary`로 packet에 넣는다.

현재 포함 필드:
- `smoke_log_path`
- `build_log_path`
- `fuzz_log_path`
- `smoke_log_signals`
- `build_log_signals`
- `fuzz_log_signals`
- `*_signal_count`

### 2. 새 reason code
- `smoke-log-memory-safety-signal`

즉 smoke-failed가 단순 baseline failure처럼 보여도,
본문에 ASan/UBSan/runtime error가 있으면
이제 packet이 그걸 **명시적 failure reason**으로 올린다.

### 3. direct script entrypoint 실행성 복구
`hermes_watch.py` 상단에 import-path bootstrap을 넣어서
이제 다음도 동작한다.
- `python scripts/hermes_watch.py --repo ... --write-llm-evidence-packet`

이전엔 `ModuleNotFoundError: scripts`로 깨졌다.

## 실제 확인
실제 repo에서 direct entrypoint로 packet 재생성 확인했고,
기존 smoke log 본문에 있던 UBSan/runtime error 라인이
`smoke-log-memory-safety-signal` reason으로 실제 들어왔다.

즉 이번 단계는 테스트용이 아니라
실제 현재 repo 상태에서도 바로 의미가 생겼다.

## 냉정한 평가
좋아진 점:
- 이제 packet이 구조화된 snapshot만 보지 않고 log body도 조금 보기 시작했다.
- smoke-failed를 그냥 generic하게 보지 않고, 그 안의 memory-safety clue를 직접 올린다.
- 실행 경로 usability bug 하나를 실제로 제거했다.

한계:
- 아직 build/fuzz log signal은 packet에 담기기만 하고 reason code로 거의 승격되지 않는다.
- 아직 probe/apply artifact 본문까지 semantic하게 읽는 건 아니다.
- 아직 raw log extraction은 keyword pattern 수준이다.

한 줄 평가:
**v0.3는 packet을 snapshot-aware에서 log-aware 쪽으로 한 걸음 밀었지만, 아직 deep semantic parser는 아니다.**

## 다음 단계
1. delegate verification / apply policy가 evidence 핵심 필드를 다시 lineage에 남기게 연결
2. failure reason extraction v0.4
   - build/fuzz log signal
   - probe/apply artifact body signal
