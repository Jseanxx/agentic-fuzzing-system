# Hermes Watch / Refiner System Audit

## 목표
현재 `scripts/hermes_watch.py` + `tests/test_hermes_watch.py` 기반의 반자동 퍼징 운영 시스템이
사용자 목표(안전한 semi-autonomous fuzz orchestration, OpenHTJ2K 우선, 이후 타겟 일반화 가능성)대로 가고 있는지 점검한다.

## 감사 범위
- 아키텍처 / state machine / 유기적 연결성
- 코드 품질 / 중복 / 쓰레기 코드 위험
- 테스트 품질 / 테스트 공백
- 예외 상황 / 운영 위험
- 다른 타겟으로 확장 가능한지
- 지금 단계에서 우선 고쳐야 할 부분

## 근거
- `python3 -m py_compile scripts/hermes_watch.py tests/test_hermes_watch.py` → OK
- `python3 -m unittest tests/test_hermes_watch.py -v` → 83 tests OK
- `hermes cron list --all` / `hermes sessions list --limit 5` 로 실제 CLI 출력 형식 일부 확인
- 정적 코드/테스트 리뷰 + 3개 독립 감사 관점(아키텍처, 테스트, 운영 리스크) 병렬 검토

---

## 1. 전체 총평

### 결론
현재 시스템은 **사용자 목표 방향으로 분명히 가고 있다.**
특히 다음은 이미 상당히 잘 서 있다.

- fuzz run 분석 → policy decision
- structured refiner queue 생성
- queue 소비 / orchestration / dispatch / bridge / launcher
- result parsing / verification / retry-escalation policy

즉 이건 더 이상 단순 watcher가 아니라,
**실행 뼈대를 가진 semi-autonomous orchestration skeleton** 이다.

### 하지만 냉정한 핵심 문제
가장 큰 문제는 두 가지다.

1. **refiner state machine이 너무 분산돼 있다**
   - `status`
   - `orchestration_status`
   - `dispatch_status`
   - `bridge_status`
   - `launch_status`
   - `verification_status`
   - `verification_policy_status`
   이 각각 따로 놀 수 있다.

2. **멀티타겟 구조라고 보기엔 아직 OpenHTJ2K-specific leakage가 크다**
   - profile/semantic layer는 일반화 방향
   - runtime/build/smoke/reporting/corpus/bootstrap은 많이 하드코딩됨

### 점수
- 방향성: **9.4 / 10**
- 현재 실전성: **8.8 / 10**
- 구조 일관성: **7.9 / 10**
- 멀티타겟 확장성: **6.9 / 10**
- 테스트 신뢰도: **8.3 / 10**

### 한 줄 요약
**방향은 맞고 실제 실행 뼈대도 생겼지만, refiner 후반부 state machine 정리와 multi-target 분리가 아직 덜 됐다.**

---

## 2. 체크리스트 기반 세부 점검

## A. 목표 정렬성 점검

### A1. 원래 목표와 현재 시스템이 맞는가?
- [x] target-profile 기반으로 타겟 분석 신호를 정책에 반영한다
- [x] shallow/deep, stage, trigger, history-aware 판단이 있다
- [x] destructive mutation 없이 low-risk automation 위주다
- [x] run 후 follow-up action을 structured artifact로 남긴다
- [x] 반자동 자기개선 루프라는 원래 철학과 일치한다

### A2. 원래 목표에서 틀어진 부분은 없는가?
- [!] 일부 있음
- refiner 이후 단계가 점점 세분화되면서 **artifact 생성 자체가 목적처럼 보이는 구간**이 생김
- 실제 action보다 `json/md/prompt/script` 생성이 많아져서 과잉 추상화 징후가 있음
- retry도 아직 실제 retry가 아니라 retry artifact/state 수준

### A3. 냉정 평가
- **크게 틀어진 건 아니다.**
- 다만 후반부 refiner pipeline은 “실행력”보다 “구조물”이 조금 앞서간 상태다.

---

## B. 유기적 연결성 점검

### B1. 파이프라인이 유기적으로 이어지는가?
현재 파이프라인:
- policy
- refiner queue
- executor
- orchestration bundle
- dispatch request
- bridge script
- launcher
- result parsing
- verification
- retry/escalation policy

이 흐름 자체는 **논리적으로 연결돼 있다.**

### B2. 끊기는 부분은 없는가?
- [!] 있다
- `retry`가 아직 실제 재검증/재런치로 이어지지 않는다
- `next_mode`는 많이 기록되지만 실제 mode transition executor가 거의 없다
- 일부 action code는 recommendation 성격에 머물고 실제 effect path가 약하다

### B3. 상태머신 일관성은 어떤가?
가장 큰 아키텍처 리스크.

문제:
- queue entry가 `execute_next_refiner_action()`에서 너무 일찍 `status=completed` 처리된다
- 실제로는 plan만 쓴 상태인데 completed라서 의미가 어색하다
- 이후 세부 상태가 별도 필드로 분산되어 single source of truth가 없다

추천:
- 장기적으로 단일 lifecycle enum으로 재정리 필요
  - `queued -> planned -> dispatch_ready -> armed -> launched -> verified -> escalated/resolved`

### B4. 냉정 평가
- 유기적 연결은 **의외로 잘 되어 있다**
- 하지만 state model은 이미 복잡도 한계에 가깝다
- 지금 안 정리하면 나중에 maintenance cost가 커진다

---

## C. 코드 품질 / 쓰레기 코드 위험 점검

### C1. 쓰레기 코드가 있는가?
- 명백한 dead code dump는 아직 크지 않다
- 하지만 **dead-field smell / disconnected-field smell** 은 있다

예:
- verification에서 보는 필드들
  - `cron_name`
  - `cron_schedule`
  - `cron_deliver`
  - `cron_prompt_lineage_tokens`
  - `delegate_expected_sections`
  - `delegate_quality_sections`
  가 실제 production pipeline에서 항상 자동으로 채워지지 않는다
- 테스트에서는 수동 주입으로 잘 맞추는데, 실제 런타임 생산 경로와 완전히 밀착돼 있지 않은 부분이 있다

### C2. 중복은 있는가?
- [!] 있음
- 동일한 registry spec list가 여러 함수에 반복된다
  - prepared finder
  - ready finder
  - armed finder
  - verifiable finder
  - verification policy candidate finder
  - executor
- 유지보수 시 registry 추가/이름 변경 시 drift 위험 큼

### C3. 과잉복잡도는 있는가?
- [!] refiner 후반부에 있음
- 기능 단계별 helper가 많고 각 단계마다 artifact가 생긴다
- 지금은 이해 가능한 수준이지만 “조금만 더 늘면 한 파일에서 관리하기 어려운” 경계선이다

### C4. 냉정 평가
- 완전한 쓰레기 코드는 아니다
- 하지만 **과잉 단계 분해 + 중복된 registry traversal + 일부 disconnected fields** 는 분명히 존재한다

---

## D. 테스트케이스 품질 점검

### D1. 현재 테스트의 강점
- breadth는 좋다
- 새로 만든 refiner pipeline 단계들이 대부분 unit-contract 수준에서 테스트됨
- history/policy/stage tagging/regression 쪽도 누적 커버리지가 꽤 있다
- 현재 `83 tests OK`

### D2. 현재 테스트의 한계
가장 중요한 한계:
**refiner pipeline end-to-end 통합 테스트가 없다.**

즉 지금은:
- executor 테스트
- orchestration 테스트
- dispatch 테스트
- bridge 테스트
- launcher 테스트
- verification 테스트
- retry/escalation 테스트
각각 따로는 통과한다.

하지만:
- queued entry 하나가 끝까지 전 단계 통합으로 흘러가는지
- 실제 stage 간 schema drift가 없는지
는 아직 강하게 증명되지 않았다.

### D3. 부족한 테스트 구체 목록
우선순위 높음:
1. malformed JSON / malformed YAML
2. wrong-type registry payload (`[]`, string, malformed dict)
3. missing request/prompt/artifact files
4. same registry에 여러 pending entries
5. cross-registry ordering/starvation
6. missing bridge script
7. launcher success but parser metadata missing
8. verification negative branches
   - cron metadata mismatch
   - lineage token missing
   - session visible but artifact missing
   - artifact present but shape/quality missing
9. `main()` watcher integration path
   - build fail
   - smoke fail
   - no-progress kill path
   - periodic progress notify
   - final return code path
10. `apply_policy_action(..., repo_root=...)` side-effect path

### D4. 냉정 평가
- 테스트는 **적지 않다**
- 하지만 coverage 착시가 있을 수 있다
- 지금은 “helper-rich unit test suite”에 가깝고,
  “full pipeline integration confidence”는 아직 부족하다

---

## E. 예외상황 / 운영 리스크 점검

### E1. malformed registry / corrupted JSON
- [!] 고위험
- `load_registry()`가 `json.loads()` 실패를 직접 던진다
- 부분 저장/수동 편집/손상 시 watcher 전체가 죽을 수 있다

### E2. concurrent update / race condition
- [!] 고위험
- save는 temp replace로 atomic-ish 하지만
- load -> mutate -> save 전체 트랜잭션은 lock 없음
- 두 프로세스가 같은 registry를 동시에 만지면 update loss 가능

### E3. 같은 work item 중복 처리
- [!] 있음
- claim/lease/in-progress lock state가 없어서
- 동시에 같은 entry를 뽑아 launch 가능

### E4. notification path failure
- [!] 있음
- `send_discord()` 예외가 critical path를 깨뜨릴 가능성 있음
- notification failure가 run 자체 실패로 전파될 수 있다

### E5. no-progress kill robustness
- [!] 있음
- SIGTERM 이후 hard kill timeout이 없다
- child process가 안 죽으면 watcher가 hang 가능

### E6. CLI output drift
- [!] 있음
- cron/session parsing이 현재 format-sensitive
- wording 바뀌면 parse/verify 약화됨

### E7. UTF-8 / file assumptions
- 일부 `read_text(encoding='utf-8')` 가 그대로 실패할 수 있다
- path가 비정상/없음/깨짐일 때 예외 일관성이 부족한 부분 있음

### E8. 냉정 평가
- 예외상황은 **현실적으로 꽤 많다**
- 다만 지금 단계에서 전부 해결하려고 하면 과도하다
- 우선순위는:
  1. malformed registry guard
  2. state-claim/lease
  3. send_discord isolation
  4. kill timeout

---

## F. multi-target 적합성 점검

### F1. profile-driven layer는 잘 일반화되어 있는가?
- [x] 꽤 잘 됨
- target profile loading
- stage tagging
- trigger/policy override
- target summary
이 부분은 다른 타겟으로 확장 가능한 방향이다

### F2. runtime/execution layer도 일반화되어 있는가?
- [!] 아니다

OpenHTJ2K leakage 예:
- default profile path가 OpenHTJ2K fixed
- Discord label이 `[OpenHTJ2K fuzz]`
- build/smoke/fuzzer wrapper names fixed
- smoke seed extension parsing이 `.j2k|.jp2|.jph`
- corpus bootstrap path가 target-specific
- stage depth가 `parse-main-header` hardcoded
- 일부 crash label semantics가 OpenHTJ2K stage 어휘에 의존

### F3. 다른 타겟이 바로 들어오면?
현실적으로:
- 같은 구조의 JPEG2000 target: **억지로 가능**
- 완전히 다른 parser/decoder target: **그대로는 어려움**

즉 지금 구조는:
## policy/generalization layer는 멀티타겟 지향
## runtime/orchestration layer는 아직 타겟별 adapter가 부족
하다.

### F4. 냉정 평가
- “멀티타겟-ready”라고 말하기엔 아직 이르다
- “멀티타겟으로 진화 가능한 단일 타겟 중심 아키텍처” 정도가 정확하다

---

## G. 지금 가장 먼저 고쳐야 할 것

### 우선순위 1 — refiner state machine 정리
왜 중요?
- 지금 가장 큰 구조 리스크
- 상태 필드 분산이 계속 누적되면 나중에 수정 비용 커짐

권장:
- lifecycle enum/phase field 재설계
- `status=completed` 남발 제거

### 우선순위 2 — malformed registry 방어
왜 중요?
- 운영 중 가장 현실적이고 치명적인 failure source

권장:
- `load_registry` / `load_crash_index` safe loader
- bad file quarantine or fallback default + error note

### 우선순위 3 — retry를 실제 retry로 연결할지 결정
왜 중요?
- 지금 retry는 policy state일 뿐 실제 재실행이 아님

권장:
- actual retry runner를 붙이거나
- 아니면 retry를 “operator review required” 상태로 명시해 오해를 막기

### 우선순위 4 — end-to-end integration test 2개
최소 추천:
- cron path E2E 1개
- delegate path E2E 1개

### 우선순위 5 — multi-target adapter layer 분리
권장 분리 대상:
- build command
- smoke command
- fuzz command
- target label/report title
- corpus bootstrap path
- accepted seed extension

---

## H. 지금 안 건드려도 되는 것
- 현재 helper 분해 자체를 무조건 줄이는 것
- LLM semantic verification 고도화
- retry 자동재시도 무한 loop
- 완전자율 destructive action

이건 지금 단계에선 오히려 독이다.

---

## I. 최종 냉정 판정

### 내 판정
**네 목표대로 만들어지고 있다.**
다만 완성에 가까워질수록,
초반에 좋았던 “보수적이고 저위험” 원칙을 유지하면서도
후반부 state machine / runtime adapter / real retry semantics 를 정리해야 한다.

### 현재 상태를 한 문장으로
**좋은 방향으로 크게 진전한 시스템이지만, refiner 후반부는 state complexity와 OpenHTJ2K leakage를 아직 정리하지 못한 상태다.**

### 총점
- 구조 적합성: **8.9 / 10**
- 실행 연결성: **9.1 / 10**
- 운영 안정성: **7.6 / 10**
- 테스트 신뢰도: **8.3 / 10**
- 타겟 일반화 가능성: **6.9 / 10**

## 최종 총평
**지금 시스템은 실패한 방향이 아니다. 오히려 꽤 잘 가고 있다. 다만 이제부터는 기능을 더 붙이는 것보다, 상태모델/예외처리/타겟분리 정리가 더 중요해지는 단계다.**
