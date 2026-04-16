# Real Loop Ops Checklist

- Updated: 2026-04-16 17:48:57 KST
- Project: `fuzzing-jpeg2000`
- Purpose: **실사용 루프를 짧고 반복 가능하게 점검하기 위한 운영용 체크리스트**

---

## 0. 목표
이번 점검의 목적은 새 기능 추가가 아니다.

확인할 것:
1. fuzz → evidence → LLM → rerun 루프가 실제로 이어지는가
2. 어디서 병목이 생기는가
3. 그 병목이
   - evidence packet 품질인지
   - 하네스/타깃 문제인지
   - bounded apply rail 문제인지
   를 구분할 수 있는가

---

## 1. 사전 준비
- [ ] 최신 run 산출물이 존재하는지 확인
  - `fuzz-records/current_status.json`
  - `fuzz-records/run_history.json`
  - 관련 `build.log` / `smoke.log` / `fuzz.log`
- [ ] 최신 LLM evidence packet이 생성되는지 확인
  - `fuzz-records/llm-evidence/*.json`
  - `fuzz-records/llm-evidence/*.md`
- [ ] 현재 타깃/프로파일이 의도한 것과 같은지 확인
  - `fuzz-records/profiles/openhtj2k-target-profile-v1.yaml`
- [ ] 현재 테스트 기준선이 깨지지 않았는지 확인
  - `python -m pytest tests -q`

---

## 2. 1회 실행 순서

### Step 1. fuzz / watcher 상태 확보
- [ ] 최신 watcher run을 확보한다
- [ ] current status에 다음이 채워졌는지 본다
  - build status
  - smoke status
  - fuzz status
  - coverage / corpus / crash info

### Step 2. evidence packet 확인
- [ ] evidence packet JSON/Markdown을 연다
- [ ] 아래 4개를 먼저 본다
  - `failure_reason_codes`
  - `top_failure_reason_narrative`
  - `finding_efficiency_summary`
  - `suggested_action_code` / `suggested_candidate_route`

### Step 3. packet 품질 판정
- [ ] reason code가 실제 체감 실패 원인과 맞는가
- [ ] narrative가 너무 장황하지 않고 바로 읽히는가
- [ ] finding-efficiency summary가 “왜 정체됐는지”를 말하는가
- [ ] suggested route가 말이 되는가

### Step 4. LLM next-step 입력 확인
- [ ] LLM/delegate가 evidence packet을 우선 참조하는지 확인
- [ ] objective / failure reasons / raw signal summary가 handoff에 유지되는지 확인
- [ ] LLM 출력이 rail 바깥 과한 수정안을 반복하지 않는지 확인

### Step 5. 수정/후속 액션 1회 수행
- [ ] 현재 suggested action을 따른다
  - deeper-stage 쪽인지
  - review/current candidate인지
  - reseed 쪽인지
- [ ] bounded apply 또는 review lane 중 하나만 1회 수행한다
- [ ] 한 번에 여러 액션을 섞지 않는다

### Step 6. rerun 후 비교
- [ ] build가 나아졌는지
- [ ] smoke가 나아졌는지
- [ ] coverage / corpus / novelty가 움직였는지
- [ ] shallow crash만 반복되는지
- [ ] 같은 실패 reason이 그대로 재발하는지

---

## 3. 병목 판정 규칙

### A. evidence packet 병목
아래면 packet 문제로 본다:
- [ ] 사람이 보기에도 top failure reason이 핵심 원인을 놓친다
- [ ] suggested route가 계속 엉뚱하다
- [ ] finding summary가 실제 stagnation과 다르게 말한다

### B. harness / target 병목
아래면 하네스/타깃 문제로 본다:
- [ ] packet은 그럴듯한데 build/smoke가 계속 같은 지점에서 막힌다
- [ ] stage reach 자체가 계속 안 열린다
- [ ] shallow crash dominance만 반복된다

### C. bounded apply rail 병목
아래면 apply rail 문제로 본다:
- [ ] LLM 제안은 그럴듯한데 항상 comment-only / guard-only rail에서 막힌다
- [ ] semantics/diff safety가 반복적으로 block한다
- [ ] rollback만 반복되고 의미 있는 수정이 안 남는다

---

## 4. 중단 조건
- [ ] 같은 action class를 2~3회 반복했는데도 개선이 없으면 중단
- [ ] 같은 reason/narrative만 되풀이되면 중단
- [ ] packet은 개선됐지만 finding이 전혀 안 늘면 구조 추가 대신 실효성 병목으로 기록
- [ ] 새 기능 구현으로 도망가지 말고, 어떤 층이 병목인지 먼저 적는다

---

## 5. 실행 후 기록 템플릿
- [ ] 이번 루프의 primary 병목:
  - packet / harness / apply rail / 기타
- [ ] 이번 루프의 top reason:
- [ ] suggested action / route:
- [ ] 실제 수행 액션:
- [ ] rerun 결과:
  - build:
  - smoke:
  - coverage:
  - corpus:
  - novelty:
- [ ] 결론:
  - 계속 밀어도 되는가
  - route를 바꿔야 하는가
  - v1 한계로 기록해야 하는가

---

## 6. 한 줄 운영 원칙
**실사용 루프 점검은 “더 많은 slice를 만들기 위한 핑계”가 아니라, 지금 시스템이 실제로 어디서 끊기는지 증거로 확인하는 단계다.**
