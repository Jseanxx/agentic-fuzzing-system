# Agentic Fuzzing System

이 저장소는 단일 JPEG2000 실험 레포가 아니라, **LLM-first 자동 에이전트 퍼징 시스템**을 키우기 위한 상위 프로젝트다.

현재 구조는 다음과 같다.

## 핵심 개념
- 상위 목표: 의미 있는 크래시를 찾기 위해 하네스 엔지니어링, 시드/코퍼스 운영, 리플레이/정제, LLM 디버깅 루프를 하나의 시스템으로 묶는다.
- 운영 원칙: artifact-first, evidence-aware, bounded automation.
- LLM 역할: 단순 요약이 아니라 하네스 수정 전/후 진단, 제안, 비판, 결과 해석을 반복한다.

## 현재 포함된 주요 자산

### 1. In-repo skills
- `skills/harness-engineering-loop/`
  - 하네스 수정 전에 어떤 md/증거를 어떤 순서로 읽어야 하는지 고정하는 프로토콜
  - Hermès 없이 Codex/다른 에이전트에서 읽어도 되는 repo-contained skill 자산

### 2. Active target testbed
- `targets/jpeg2000-openhtj2k/`
  - JPEG2000 / OpenHTJ2K 기반 실험 타깃
  - 퍼징 harness, watcher/control-plane, fuzz records, replay/refinement artifacts, 테스트 코드 포함
  - 큰 시스템 안의 **테스트베드/검증 타깃** 역할

### 3. Crash samples
- `crash-samples/jpeg2000-openhtj2k/`
  - 루트에 흩어져 있던 샘플 크래시를 정리한 폴더
  - 타깃별로 분리 보관

## 시작점
1. 상위 규칙 확인:
   - `skills/harness-engineering-loop/SKILL.md`
2. JPEG2000 타깃 작업 시작:
   - `targets/jpeg2000-openhtj2k/README.md`
3. 현재 상태/기록 확인:
   - `targets/jpeg2000-openhtj2k/fuzz-records/README.md`
   - `targets/jpeg2000-openhtj2k/fuzz-records/current-status.md`
   - `targets/jpeg2000-openhtj2k/fuzz-records/progress-index.md`

## 왜 이렇게 정리했나
기존 작업은 JPEG2000/OpenHTJ2K를 기반으로 빠르게 성장했지만, 목표는 처음부터 더 컸다.
즉 진짜 프로젝트는:
- 하나의 타깃만 계속 만지는 레포가 아니라
- 여러 테스트베드/타깃으로 확장 가능한
- **자동 에이전트 퍼징 시스템**이다.

JPEG2000/OpenHTJ2K는 그 안에서 가장 먼저 깊게 밀어본 실험 타깃이다.

## 현재 권장 역할 분담
- 빠른 구현/반복: Codex 같은 코드 중심 에이전트
- 규칙/감사/프로토콜/기록: Hermes

이 저장소는 두 흐름이 같이 쓸 수 있도록 정리되어 있다.
