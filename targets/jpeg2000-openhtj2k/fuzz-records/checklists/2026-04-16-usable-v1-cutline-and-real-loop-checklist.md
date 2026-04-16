# Usable v1 Cutline + Real Loop Checklist

- Updated: 2026-04-16 17:31:24 KST
- Project: `fuzzing-jpeg2000`
- Purpose: **지금 시스템의 정체성을 과장 없이 자르고, v1 포함/제외/실사용 체크리스트를 한 장에서 보게 하기**

---

## 0. 현재 정체성 한 줄 정의
**이 프로젝트는 지금 “완성형 자가발전 퍼저”가 아니라, OpenHTJ2K 퍼징 상태를 증거 패킷으로 압축하고 LLM이 다음 하네스 수정 방향을 덜 헤매게 만드는 semi-autonomous evidence/control-plane prototype”이다.**

---

## 1. v1 포함 항목

### 포함 기준
- LLM이 다음 수정 방향을 읽는 데 직접 도움 됨
- bounded/safe loop로 다시 실행 가능함
- control-plane 디테일이 아니라 실사용 루프에 바로 쓰임

### v1 포함 트리
- v1 core
  - evidence packet
    - failure reason codes
    - explanation
    - causal chain
    - top-reason narrative
    - finding-efficiency summary/recommendation
    - suggested action code / candidate route linkage
  - execution substrate
    - build / smoke / fuzz status capture
    - run history / crash-family / corpus / coverage signal capture
    - harness candidate / probe / skeleton artifact flow
  - safe correction rail
    - guarded apply candidate
    - delegate verification
    - bounded apply
    - rollback
    - recovery routing
  - minimum routing safety
    - secondary conflict surfacing
    - severity / actionability split
    - retry blind loop 방지용 hold / abort override

### v1 포함 판정
- [x] evidence packet이 “왜 + 그래서 다음엔 뭐”를 한 장에서 보여준다
- [x] build/smoke/fuzz 상태가 artifact로 남는다
- [x] LLM handoff 전에 failure reason/objective를 압축한다
- [x] bounded apply/rollback이 있다
- [x] recovery decision이 최소한 `retry / hold / abort / resolved`로 나뉜다

---

## 2. v1 제외 항목

### 제외 기준
- control-plane이 더 예뻐지거나 정교해지지만
- 지금 당장 LLM-guided fuzz loop의 실효성 상승을 보장하지 않음

### v1 제외 트리
- defer
  - routing ornament
    - secondary-conflict confidence/budget linkage v0.1
    - finer cooldown / backoff nuance
    - 더 촘촘한 lane confidence math
  - generalization expansion
    - 추가 multi-target abstraction
    - target-agnostic mutation intelligence 확대
  - deeper autonomy claims
    - repair success probability learner
    - semantic planner급 next-action selection
    - open-ended autonomous patching

### v1 제외 판정
- [x] `secondary-conflict confidence/budget linkage v0.1`은 보류
- [x] multi-target 추가 확장은 보류
- [x] 더 깊은 policy nuance는 실사용 병목이 드러나기 전까지 보류

---

## 3. 실사용 루프 체크리스트

### 목표 루프
- real loop
  - fuzz 실행
  - current_status / run_history / logs 생성
  - LLM evidence packet 생성
  - top reason / objective / suggested route 확인
  - 다음 하네스 수정 방향 결정
  - bounded apply 또는 review lane 수행
  - build / smoke / fuzz 재실행
  - 개선 여부 비교

### 실행 체크리스트
- 준비
  - [ ] latest `current_status.json`이 실제 최신 run을 가리키는지 확인
  - [ ] latest `run_history.json`에 최근 plateau / corpus / crash-family signal이 반영되는지 확인
  - [ ] latest `fuzz-records/llm-evidence/*.json` / `*.md`가 생성되는지 확인
- packet 품질
  - [ ] `failure_reason_codes`가 operator 관점에서도 납득 가능한지 확인
  - [ ] `top_failure_reason_narrative`가 장황하지 않고 바로 읽히는지 확인
  - [ ] `finding_efficiency_summary`가 실제 정체 원인을 요약하는지 확인
  - [ ] `suggested_action_code` / `suggested_candidate_route`가 과도하게 엉뚱하지 않은지 확인
- LLM 개입 품질
  - [ ] LLM이 evidence packet을 먼저 읽고 답하게 되어 있는지 확인
  - [ ] LLM 출력이 bounded rail(`comment-only` / `guard-only`)을 자꾸 벗어나지 않는지 확인
  - [ ] 반복적으로 같은 shallow fix만 제안하는지 확인
- 실행 결과
  - [ ] 수정 뒤 build/smoke가 실제로 개선됐는지 확인
  - [ ] coverage / corpus / unique crash novelty가 조금이라도 움직였는지 확인
  - [ ] improvement가 없으면 같은 route를 반복하지 말고 review/reseed/deeper-stage 쪽으로 바꾸는지 확인
- 멈춤 조건
  - [ ] 같은 action class가 2~3회 반복되는데도 stage reach가 안 오르면 그걸 v1 한계로 기록
  - [ ] packet은 좋아졌는데 finding이 안 좋아지면 control-plane 추가보다 harness/domain 쪽 병목으로 판정

---

## 4. 전체 코드 검사 기반 냉정평가

### 코드 규모 / 구조
- Python 오케스트레이션:
  - `scripts/` 약 **10,359 lines**
  - `tests/` Python 약 **9,963 lines**
  - 핵심 모놀리스: `scripts/hermes_watch.py` **6,080 lines**
  - 핵심 테스트: `tests/test_hermes_watch.py` **9,758 lines**
- C/C++ 타깃 코드:
  - `source/` 약 **104,162 lines**
  - `.cpp` 약 **33,135 lines**
  - `.h` 약 **31,380 lines**
  - `.hpp` 약 **12,685 lines**
- 테스트 상태:
  - `python -m pytest tests -q` → **289 passed**

### 의존성 트리
- C++ / build
  - required
    - CMake 3.13+
    - C++11+
    - Threads
  - optional
    - TIFF / libtiff
    - glfw3
    - OpenGL
  - fuzzing
    - libFuzzer
    - AddressSanitizer
    - UndefinedBehaviorSanitizer
  - bundled
    - `source/thirdparty/highway`
- Python / watcher
  - mostly stdlib
    - argparse
    - json
    - pathlib
    - subprocess
    - urllib.request
    - re / shutil / signal / time
  - external
    - `PyYAML` (profile loading / reconnaissance)
  - operator dependency
    - Hermes CLI / subagent / cron execution path

### 구조 평가
- 강한 점
  - artifact-first 기록이 잘 되어 있음
  - 테스트 커버가 watcher 진화 속도에 비해 꽤 탄탄함
  - evidence packet과 bounded apply rail이 분리되어 있어 안전성 설명이 가능함
- 약한 점
  - `hermes_watch.py`가 너무 큼
  - `test_hermes_watch.py`도 초대형이라 유지보수 피로가 커질 수 있음
  - Python dependency management가 공식 패키징 파일 없이 느슨함
  - 구조가 좋아 보이는 것과 실제 finding improvement는 아직 다름

---

## 5. 내 목적에 맞는지 / LLM 개입이 많은지 평가

### 사용자 목적 적합도
- 네 목적
  - 퍼징 돌린다
  - 정체/실패 신호를 많이 뽑는다
  - LLM이 먹기 좋게 정리한다
  - LLM이 다음 하네스 수정 방향을 제안한다
  - 다시 돌린다
- 현재 적합도 평가
  - **방향 적합도: 높음**
  - **실제 finding improvement 보장도: 아직 중간 이하**

### LLM 개입도 평가
- 높은 부분
  - evidence packet 생성
  - failure reason / objective / suggested route linkage
  - subagent review/regeneration orchestration
  - delegate artifact verification lineage
- 낮거나 아직 제한적인 부분
  - 실제 patch autonomy는 bounded rail에 강하게 묶여 있음
  - semantic planner 수준은 아님
  - repair success를 학습해서 다음 행동을 고르는 수준은 아님

### 한 줄 판정
**LLM 개입은 “낮다”가 아니라 이미 꽤 높다. 다만 개입의 중심이 ‘자유로운 코드 생성’이 아니라 ‘증거 압축 + bounded next-step guidance’ 쪽이다.**

---

## 6. 프로젝트 진행도 표현

### 진행도 트리
- progress view
  - 문서상 stage completion
    - 완료 row: 64
    - 보류/중요 row: 1
    - 기록 소화율: **98.5%**
  - usable v1 기준
    - 완료: `failure reason extraction v0.9`
    - 남음: `usable v1 cutline review`
    - 마감선 기준 진도: **50.0%**
  - 실무 기준
    - 필수 남은 일
      - usable v1 종료선 확정
      - 실사용 루프 1회 점검
    - 보류 권장
      - confidence/budget linkage 추가 정교화

### 냉정한 진행도 해석
- 문서/roadmap 소화율은 매우 높다
- 하지만 “실제 finding 효율 개선이 증명됐냐” 기준 진도는 그보다 낮다
- 따라서 지금 프로젝트는 **구조 완성도는 높고, 실효성 검증은 아직 덜 끝난 상태**다

---

## 7. 지금 바로 해야 할 일
- immediate next
  - [ ] `usable v1 cutline review`를 canonical 판단으로 확정
  - [ ] 실제 fuzz → evidence → LLM → rerun 루프를 한 번 돌려서 병목 기록
  - [ ] 병목이 packet 품질인지, harness 질인지, bounded apply rail인지 분리 판정
  - [ ] 새 기능 추가는 그 병목이 확인된 뒤에만 진행

## 8. 최종 한 줄 권고
**이제는 더 만들기보다, 지금 만든 LLM-heavy evidence/control-plane을 실제 루프에 태워 보고 어디서 효과가 끊기는지 확인하는 게 맞다.**
