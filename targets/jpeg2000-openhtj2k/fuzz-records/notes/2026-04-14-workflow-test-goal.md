# Workflow Test Goal — 2026-04-14

## 이번 테스트에서 검증하려는 것
1. WSL2 노트북 환경에서 build → smoke → fuzz 흐름이 실제로 이어지는지
2. 퍼징 중 coverage / ft / corpus / crash / timeout / no-progress 같은 유의미한 피드백이 남는지
3. 그 피드백을 바탕으로 하네스/시드/기록을 다시 갱신하는 루프가 가능한지
4. build-failed / smoke-failed 같은 조기 실패도 `current_status.json`과 md 기록으로 남는지

## 운영 원칙
- 지금은 성능 최적화보다 **흐름 검증**이 우선
- 짧은 러닝으로도 로그/상태/기록 경로가 검증되면 의미 있음
- 문제가 나오면 바로 다음 액션 후보를 기록

## 현재 선행 이슈
- `coding_units.cpp`에서 `<stdexcept>` 누락으로 보이는 빌드 실패가 있었음
- watcher는 조기 실패(build/smoke fail) 시 `current_status.json`을 남기지 않던 문제가 있었음

## 이번 라운드 목표
- 위 두 이슈를 정리하고 실제로 한 번 퍼징을 시작시켜 본다
