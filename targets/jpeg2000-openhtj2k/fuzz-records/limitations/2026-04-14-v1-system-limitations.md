# System Limitations v1 — 2026-04-14

## Purpose
이 문서는 자가발전형 퍼징 시스템의 **현재 한계점**을 날짜/버전 기준으로 남기는 기록이다.
다음 버전에서 무엇이 개선되었는지 비교하기 위한 기준선 역할을 한다.

## Current version context
- stage: WSL2 로컬 검증 단계
- maturity: 정책 기반 반자동 퍼징 운영 시스템 v1

## Current limitations
### 1. Artifact classification is still v1
- `crash / leak / timeout / no-progress` 분류 규칙은 들어갔지만 아직 단순 규칙 기반이다.
- 복합 신호가 섞일 때 우선순위 해석이 더 정교해질 필요가 있다.

### 2. Crash dedup is string-based
- fingerprint는 `kind | location | summary` 기반이다.
- 의미상 같은 버그라도 summary가 달라지면 다른 fingerprint로 분리될 수 있다.

### 3. No semantic root-cause clustering yet
- 현재는 stack/summary 중심 dedup이다.
- 같은 근본 원인을 자동으로 묶어주는 semantic grouping은 아직 없다.

### 4. Policy action is partially auto-executed
- policy log, known-bad tracking, regression candidate registration 같은 안전한 상태 갱신은 자동 수행된다.
- 하지만 corpus 파일 이동, regression 재실행, Discord 우선순위 조정 같은 실행형 액션은 아직 자동이 아니다.

### 5. Regression auto-trigger exists, but full regression enforcement is incomplete
- build-failed / smoke-failed 경로에서는 regression trigger record를 자동 생성한다.
- 하지만 실제 regression run을 즉시 실행/완료시키는 단계까지는 아직 아니다.

### 6. Remote execution is not implemented yet
- 최종 목표는 Proxmox 머신/VM에 SSH로 붙어서 운영하는 것이다.
- 하지만 현재 구현은 WSL2 로컬 기준이다.

### 7. Discord reporting remains partial
- 로컬 기록은 잘 남는다.
- 하지만 meaningful event만 Discord로 올리는 운영은 아직 완성되지 않았다.

### 8. Corpus lifecycle is improved but not complete
- triage / coverage / regression / known-bad 분리는 시작했다.
- 그러나 minimization, promotion/demotion, aging-out 같은 수명주기 정책은 없다.

### 9. No automatic artifact minimization yet
- crash artifact가 생겨도 자동 최소화(minimize)가 없다.
- 따라서 regression/triage 품질을 높이려면 이 기능이 필요하다.

### 10. No cross-host/global history yet
- 현재 crash index는 로컬 단일 저장소 기준이다.
- 나중에 WSL과 Proxmox를 같이 쓰게 되면 전역 인덱스/동기화 정책이 필요하다.

## What this means honestly
현재 시스템은 분명 발전 중이고 실제로 유용하지만,
아직은 **완전 자율형 self-improving fuzzing agent** 라기보다는
**정책 기반 반자동 운영 시스템**으로 설명하는 것이 정확하다.

## Next version goals
- artifact 분류 정책 고도화
- dedup 정확도 개선
- 정책 자동 집행 일부 도입
- regression 강제 루프 강화
- SSH 원격 실행 모델 설계/이식
