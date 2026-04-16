# Hermes Watch Autonomous Supervisor Loop v0.1 Checklist

- Updated: 2026-04-16 19:18:10 KST
- Project: `fuzzing-jpeg2000`

---

## 목표
- [x] periodic cron 대신 long-running autonomous supervisor loop 기반 마련
- [x] self-contained prompt + launcher script + status/log artifacts 생성
- [x] 실제 background daemon 기동
- [x] Discord progress channel 연결

## 코드 변경
- [x] `scripts/hermes_watch.py`
  - [x] autonomous supervisor prompt builder 추가
  - [x] autonomous supervisor bundle writer 추가
  - [x] CLI flags 추가
- [x] `tests/test_hermes_watch.py`
  - [x] bundle writer 테스트 추가
  - [x] CLI prepare path 테스트 추가

## RED/GREEN
- [x] RED
  - [x] `python -m pytest tests/test_hermes_watch.py::HermesWatchAutonomousSupervisorTests -q`
  - [x] 2 failed
- [x] GREEN
  - [x] 같은 명령 재실행
  - [x] 2 passed

## runtime
- [x] supervisor bundle 생성
- [x] prompt path 생성
- [x] script path 생성
- [x] status/log path 생성
- [x] background process 시작
- [x] running 상태 확인

## verification
- [x] `python -m pytest tests -q`
  - [x] 294 passed
- [x] cron fallback pause
- [x] Discord channel update post

## 현재 한계
- [ ] remote/proxmox closure 아님
- [ ] supervisor self-healing / overlap lock 강화 필요
- [ ] daemon이 실제로 여러 iteration을 거치며 유효한 progress를 내는지 계속 관찰 필요
