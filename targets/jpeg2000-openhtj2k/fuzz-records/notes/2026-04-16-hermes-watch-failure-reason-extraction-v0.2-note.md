# 2026-04-16 — failure reason extraction v0.2 note

## 왜 이 단계를 바로 이었나
`LLM evidence packet v0.1`은 latest artifact를 모으는 입구는 만들었지만,
실제 failure reason은 아직 얕았다.

특히 다음이 부족했다.
- no-progress를 그냥 `no-crash-yet` 수준으로만 읽는 문제
- run history에 이미 있는 coverage/corpus 정체 신호를 packet이 아직 못 읽는 문제
- shallow crash가 반복되는 상황을 stage-reach 문제로 직접 승격하지 못하는 문제

그래서 이번 단계는 큰 구조 변경 없이,
**이미 있는 `run_history.json`을 읽어 failure reason을 더 직접 구조화**하는 작은 slice로 갔다.

## 이번에 추가한 것
`llm_evidence.py`가 이제 latest run history를 읽는다.

새로 추출하는 reason codes:
- `no-progress-stall`
- `coverage-plateau`
- `corpus-bloat-low-gain`
- `shallow-crash-recurrence`
- `stage-reach-blocked`

## 구체적 동작
### 1. no-progress stall
- `outcome == no-progress`
- 또는 `artifact_reason == stalled-coverage-or-corpus`
이면 바로 stall reason으로 올린다.

### 2. coverage plateau
최근 4개 history window에서:
- coverage 값이 그대로이고
- exec/s가 충분히 높고
- 시간이 충분히 흘렀으면
`coverage-plateau`로 본다.

### 3. corpus bloat low gain
최근 4개 history window에서:
- corpus는 많이 늘었는데
- coverage gain이 거의 없으면
`corpus-bloat-low-gain`으로 본다.

### 4. shallow crash recurrence
최근 crash history에서 shallow stage 비율이 높으면
`shallow-crash-recurrence`로 본다.

### 5. stage reach blocked
primary mode가 deep 계열인데,
- no-progress stall
- coverage plateau
- corpus low-gain
- shallow crash recurrence
- no-crash-yet
중 하나가 있으면
`stage-reach-blocked`를 추가한다.

즉 단순 “안 됨”이 아니라,
**깊은 stage로 못 들어가고 있다**는 해석을 packet이 직접 시작한 것이다.

## packet 변화
이제 evidence packet에 추가로 들어간다.
- `run_history_path`
- `run_history`

markdown에도 recent history summary를 넣기 시작했다.

## 냉정한 평가
좋아진 점:
- 이제 packet이 current_status 단일 snapshot만 보지 않는다.
- 반복 정체/plateau/shallow recurrence를 더 직접 reason으로 올린다.
- `llm_objective`가 deep mode stall 상황에서 `deeper-stage-reach`로 더 자연스럽게 압축된다.

한계:
- 아직 최근 4개 history window 기반의 단순 규칙이다.
- raw fuzz log 본문, stack body, corpus 내용 자체를 읽는 단계는 아니다.
- stage depth 분류도 현재는 lightweight heuristic이다.

한 줄 평가:
**v0.2는 history-aware reasoning을 시작했지만, 아직 진짜 semantic failure analysis engine은 아니다.**

## 다음 단계
1. `LLM handoff prompt simplification`
2. `failure reason extraction v0.3`
   - import-path 실행성 문제까지 정리
   - raw log/body-level signals 더 읽기
