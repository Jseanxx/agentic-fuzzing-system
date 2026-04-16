# Real Loop Ops Checklist v2

- Updated: 2026-04-16 17:52:59 KST
- Project: `fuzzing-jpeg2000`
- Purpose: **실사용 루프를 정말 쓸모 있는지 판정하기 위한 더 차갑고 더 좁은 운영 체크리스트**

---

## 0. 운영 원칙
- [ ] 이번 점검의 목적은 새 기능 추가가 아니다
- [ ] suggested action / suggested route는 **정답이 아니라 가설**로 취급한다
- [ ] 한 번에 **하나의 action class만** 수행한다
- [ ] rerun 결과가 없으면 성공/개선 주장 금지
- [ ] 병목을 기록하기 전에는 구조 확장 금지

---

## 1. Freshness gate
이 단계에서 하나라도 틀리면 점검을 진행하지 않는다.

- [ ] `current_status.json`이 실제 최신 run을 가리킨다
- [ ] `run_history.json`이 최신 run window를 반영한다
- [ ] `build.log` / `smoke.log` / `fuzz.log` 중 이번 루프에 필요한 로그가 실제로 존재한다
- [ ] `fuzz-records/llm-evidence/*.json` / `*.md`가 최신 상태로 다시 생성돼 있다
- [ ] target profile이 현재 의도한 타깃과 일치한다
- [ ] 기준선이 깨지지 않았다
  - `python -m pytest tests -q`

### Freshness gate 실패 시 기록
- [ ] 병목층을 `observability/freshness`로 기록
- [ ] packet/harness/apply 판단으로 넘어가지 않는다

---

## 2. Packet read gate
여기서는 “읽기 좋냐”보다 “이번 loop action을 정당화하냐”를 본다.

- [ ] `failure_reason_codes`가 실제 실패/정체와 맞는다
- [ ] `top_failure_reason_narrative`가 핵심 원인을 흐리지 않는다
- [ ] `finding_efficiency_summary`가 정체 원인을 말한다
- [ ] `suggested_action_code` / `suggested_candidate_route`가 최소한 터무니없지는 않다

### Packet gate 실패 시 판정
- [ ] 병목층을 `packet`으로 기록
- [ ] suggested action을 실행하지 않는다
- [ ] 구조 확장 대신 packet 품질 문제로 남긴다

---

## 3. Action selection gate
여기서는 한 번에 하나만 고른다.

- [ ] 이번 루프의 primary action class를 1개만 고른다
  - `shift_weight_to_deeper_harness`
  - `halt_and_review_harness`
  - `minimize_and_reseed`
  - bounded apply
- [ ] 왜 이 action을 고르는지 한 줄로 적는다
- [ ] 이번 루프에서 하지 않을 action도 적는다
  - 예: reseed는 이번 루프에서 안 함
  - 예: apply는 이번 루프에서 안 함

### Action gate 실패 시 판정
- [ ] action이 2개 이상 섞이면 루프 중단
- [ ] 병목층을 `operator discipline`으로 기록

---

## 4. LLM output discipline gate
LLM 개입은 많아도, bounded rail을 못 지키면 실사용 가치가 떨어진다.

- [ ] LLM/delegate가 evidence packet을 먼저 읽고 답했는지 확인
- [ ] objective / failure reasons / raw signal summary가 handoff에 유지됐는지 확인
- [ ] LLM 출력이 rail 바깥 과한 수정안을 반복하지 않는지 확인
- [ ] 반복적으로 shallow fix만 제안하지 않는지 확인

### LLM gate 실패 시 판정
- [ ] 병목층을 `llm-output-discipline`으로 기록
- [ ] apply/harness 탓으로 바로 넘기지 않는다

---

## 5. Single-loop execution
이 단계는 실제로 한 번만 돈다.

- [ ] 선택한 action class 1개만 수행
- [ ] 수행 전 상태를 짧게 기록
  - build
  - smoke
  - coverage
  - corpus
  - novelty / crash-family
- [ ] 수행 후 rerun 한다
- [ ] rerun 후 같은 항목을 다시 기록한다

---

## 6. Go / No-Go gate
여기가 핵심이다. 아래 중 하나라도 개선이 보여야 “계속 밀어도 됨” 후보가 된다.

### Go 신호
- [ ] build가 실패 → 성공으로 개선
- [ ] smoke가 실패/skip → 성공으로 개선
- [ ] coverage가 조금이라도 의미 있게 움직임
- [ ] corpus가 불기만 하는 게 아니라 novelty signal이 생김
- [ ] shallow crash dominance가 약해짐
- [ ] top failure reason이 더 깊은 단계의 문제로 이동함

### No-Go 신호
- [ ] build/smoke/fuzz 상태가 사실상 그대로다
- [ ] shallow crash만 반복된다
- [ ] 같은 action class를 또 권하게 된다
- [ ] packet은 좋아 보이는데 finding은 그대로다
- [ ] rollback / semantics block만 반복된다

### Go / No-Go 판정
- [ ] Go면: 같은 방향으로 **한 번 더** 시도 가능
- [ ] No-Go면: 같은 방향 반복 금지
- [ ] No-Go면 반드시 병목층을 기록하고 route 변경 또는 v1 한계로 올린다

---

## 7. 병목층 최종 분류
이번엔 5개로 본다.

- [ ] `observability/freshness`
  - 최신 상태/로그/evidence 정합성이 틀림
- [ ] `packet`
  - top reason / finding summary / suggested route가 실제와 어긋남
- [ ] `llm-output-discipline`
  - packet은 괜찮은데 LLM 출력이 rail 밖으로 나감
- [ ] `harness-target`
  - packet/LLM은 그럴듯한데 build/smoke/stage reach가 계속 막힘
- [ ] `apply-rail`
  - 제안은 그럴듯한데 semantics/diff safety/rollback이 반복됨

---

## 8. 즉시 중단 조건
- [ ] 같은 action class 2회 연속 No-Go
- [ ] 같은 failure reason / narrative만 재생산
- [ ] packet은 좋아졌는데 finding이 안 좋아짐
- [ ] 새 slice를 만들고 싶어지는 충동이 드는데 병목 기록이 아직 없음

---

## 9. 실행 후 기록 템플릿
- [ ] 이번 루프의 freshness 상태:
- [ ] 이번 루프의 chosen action class:
- [ ] chosen 이유 1줄:
- [ ] 실행 전 상태:
  - build:
  - smoke:
  - coverage:
  - corpus:
  - novelty/crash-family:
- [ ] 실행 후 상태:
  - build:
  - smoke:
  - coverage:
  - corpus:
  - novelty/crash-family:
- [ ] Go / No-Go 판정:
- [ ] 최종 병목층:
  - observability/freshness / packet / llm-output-discipline / harness-target / apply-rail
- [ ] 다음 결정:
  - 같은 방향 1회 추가
  - route 변경
  - v1 한계 기록

---

## 10. 최종 운영 문장
**이 체크리스트의 목적은 시스템이 똑똑해 보이는지 확인하는 게 아니라, 이번 한 번의 루프가 실제 다음 퍼징 iteration의 질을 올렸는지 차갑게 판정하는 것이다.**
