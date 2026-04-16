# Immediate Reinforcements Applied — 2026-04-14

## What was strengthened first
1. `triage / coverage / regression` 모드 스크립트 추가
2. corpus 디렉토리 표준화
3. hardening checklist 추가
4. fuzz policy v1 문서화
5. GitHub 공개용 prompt 초안 작성
6. WSL → Proxmox SSH 최종 목표 문서화

## Important bug found during validation
- mode wrapper가 `RUN_DIR`를 넘겨도 `hermes_watch.py`가 내부에서 자체 run_dir를 다시 만들어서 mode별 artifact 경로가 일관되지 않는 문제가 있었음
- 이건 운영 분리 관점에서 결함이라 즉시 수정함

## Why this matters
자가발전형 퍼징 시스템은 단순 실행보다 **실행 컨텍스트 분리**가 중요하다.
mode별 경로가 섞이면 triage / coverage / regression 결과가 섞여 정책 엔진이 오판하기 쉬워진다.
