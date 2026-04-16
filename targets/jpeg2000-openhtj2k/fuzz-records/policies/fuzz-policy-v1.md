# Fuzz Policy v1

## Core idea
이 시스템은 단순 실행기가 아니라, 퍼징 결과를 보고 다음 액션을 선택하는 운영 정책이 필요하다.

## Modes
### 1. triage
- 목적: sanitizer 이슈 즉시 재현, stack 확보, artifact 저장
- corpus: `fuzz/corpus/triage`
- 기본 정책: 엄격한 sanitizer 설정 유지

### 2. coverage
- 목적: coverage / feature / corpus 성장 관찰
- corpus: `fuzz/corpus/coverage`
- 기본 정책: `detect_leaks=0` 허용
- 이유: leak 때문에 너무 일찍 중단되는 것을 방지

### 3. regression
- 목적: known-bad seed, fixed bug seed, smoke 성격의 회귀 검증
- corpus: `fuzz/corpus/regression`
- 기본 정책: smoke 포함 가능, 엄격 모드 유지

## Event classification
### build-failed
- 의미: 코드/빌드 설정 문제
- 다음 액션: 컴파일 에러 수정, 같은 커밋에서 재빌드

### smoke-failed
- 의미: baseline 입력에서 이미 sanitizer/logic issue 존재
- 다음 액션: triage 대상으로 승격, 해당 seed를 regression에도 등록

### crash
- 의미: sanitizer 또는 libFuzzer artifact 생성
- 다음 액션: artifact fingerprint 기록, known-bad 여부 판정, regression 편입 검토

### leak
- 의미: coverage run을 너무 빨리 끊을 수 있음
- 다음 액션: triage note 생성, coverage mode 정책 유지 여부 판단

### no-progress
- 의미: coverage 증가 정체 또는 harness depth 부족 가능성
- 다음 액션: seed 다양화 / harness 개선 / 모드 전환 검토

## Minimum verification after any code change
1. build
2. regression run
3. triage run (if reproducer exists)
4. coverage run (short)
5. md 기록 업데이트

## Non-goals (current stage)
- 완전 자율 수정 루프
- 무제한 self-healing
- crash dedupe 완성판
- 원격 대규모 분산 퍼징

현재 단계의 목표는 **정책 기반 반자동 운영 루프를 안정화**하는 것이다.


## Policy action layer (v1)
- 분류 결과는 이제 policy action으로 이어진다.
- 현재는 기록/추천 단계이며, 자동 집행 단계는 아니다.
- 기록 필드:
  - `policy_priority`
  - `policy_action_code`
  - `policy_recommended_action`
  - `policy_next_mode`
  - `policy_bucket`


## Policy action auto-execution (v1)
- 현재는 안전한 registry/state 갱신만 자동 수행한다.
- 자동 반영 대상:
  - `policy_actions.json`
  - `known_bad.json`
  - `regression_candidates.json`
- 아직 자동 미수행 대상:
  - corpus 파일 이동/복사
  - regression run 재실행
  - destructive cleanup


## Regression auto-trigger (v1)
- build-failed / smoke-failed는 regression trigger를 자동 생성한다.
- 현재는 queue/registry 기록 단계이며, 실제 regression auto-run은 다음 단계다.
- 기록 파일: `fuzz-artifacts/automation/regression_triggers.json`
