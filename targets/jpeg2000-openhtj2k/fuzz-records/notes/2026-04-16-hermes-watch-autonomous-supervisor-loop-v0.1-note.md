# Hermes Watch Autonomous Supervisor Loop v0.1

- Updated: 2026-04-16 19:18:10 KST
- Project: `fuzzing-jpeg2000`
- Scope: **periodic cron 근사치를 넘어서, self-prompt 기반 long-running autonomous supervisor loop를 실제로 띄운 단계**

---

## 왜 이 단계가 필요했나
사용자 목표는 단순 주기 배치가 아니라:
- 내가 중간에 계속 지시하지 않아도
- 시스템이 스스로 다음 작업을 고르고
- LLM 개입을 자주 넣고
- 피드백/기록/수정/재실행을 반복하는 것
이다.

기존 cron 방식은:
- 새 세션이 일정 간격마다 한 번만 도는 형태였고
- 사용자가 원하는 “계속 개발”과는 거리가 있었다.

그래서 이번 단계에서는:
**self-contained prompt를 먹고 계속 도는 local autonomous supervisor daemon**을 실제로 만들고 띄웠다.

---

## 이번에 만든 것
### 1. autonomous supervisor prompt/bundle writer
`hermes_watch.py`에 추가:
- `build_autonomous_supervisor_prompt(...)`
- `write_autonomous_supervisor_bundle(...)`

이 helper는 다음을 만든다:
- `fuzz-records/autonomous-supervisor/autonomous-dev-loop-prompt.txt`
- `fuzz-records/autonomous-supervisor/autonomous-dev-loop.sh`
- `fuzz-records/autonomous-supervisor/autonomous-dev-loop.log`
- `fuzz-records/autonomous-supervisor/autonomous-dev-loop-status.json`
- `fuzz-records/autonomous-supervisor/STOP`

### 2. CLI entrypoint
새 flag:
- `--prepare-autonomous-supervisor`
- `--autonomous-supervisor-sleep-seconds`
- `--autonomous-supervisor-channel-id`

즉 watcher가 이제 단순 one-shot 실행기만이 아니라,
**continuous autonomous dev loop bundle generator** 역할도 하게 됐다.

### 3. 실제 long-running daemon 기동
실제로 background process를 띄웠다.
- process session: `proc_8cd836afc789`
- status file에서 iteration 1 running 확인

### 4. Discord 진행 로그 채널 연결
자동 진행 상황 요약용 채널:
- `jpeg2000-openhtj2k`
- channel id: `1493631285027934419`

supervisor prompt는 MCP Discord logging이 가능하면
그 채널에 concise progress update를 남기도록 설계했다.

### 5. cron fallback 정지
기존 10분 cron job은 겹침 방지를 위해 pause했다.
- cron job id: `ead5c4e8a024`

이유:
- cron과 daemon이 동시에 돌면
- 같은 repo/state/doc를 중복 수정하면서 control-plane이 더러워질 수 있다.

---

## 검증
### RED
- `python -m pytest tests/test_hermes_watch.py::HermesWatchAutonomousSupervisorTests -q`
- 초기 결과: **2 failed**
  - missing helper
  - missing CLI args

### GREEN
- 같은 테스트 재실행: **2 passed**

### full regression
- `python -m pytest tests -q`
- 결과: **294 passed**

### runtime verification
- `python scripts/hermes_watch.py --prepare-autonomous-supervisor --autonomous-supervisor-sleep-seconds 60 --autonomous-supervisor-channel-id 1493631285027934419`
- bundle 생성 성공
- background daemon 시작 성공
- status file에서 running 상태 확인

---

## 냉정한 평가
좋아진 점:
- 더 이상 “10분마다 한번” 같은 배치 근사치에만 의존하지 않게 됐다.
- 사용자가 원한 방향인 **continuous self-prompt autonomous development loop**에 실제로 한 발 들어갔다.
- 이제는 목표를 담은 self-contained prompt 하나로 same process family가 계속 일을 이어갈 수 있다.

한계:
- 아직 local daemon이다.
- proxmox remote closure는 아직 아니다.
- prompt 안에서 매 iteration 무엇을 고를지는 여전히 LLM 판단 품질에 의존한다.
- hard safety stop / overlap lock / supervisor self-healing은 아직 얇다.

즉 이번 단계는:
**완전 자율 완성**이 아니라,
**periodic cron에서 continuous supervisor로 실행 모델을 승격한 단계**다.

---

## 한 줄 결론
**이번 단계는 자가발전형 퍼징 에이전트 시스템의 실행 모델을 “가끔 깨는 배치”에서 “계속 도는 self-prompt daemon” 쪽으로 바꾼 전환점이다.**
