# Self-Improving Fuzzing System Cold Evaluation

- Updated: 2026-04-15 18:03:04 KST
- Scope: `scripts/hermes_watch.py`, `scripts/hermes_watch_support/*`, `tests/test_hermes_watch.py`, `fuzz-records/*`
- Evidence:
  - `python -m py_compile scripts/hermes_watch.py tests/test_hermes_watch.py` → OK
  - `python -m pytest tests/test_hermes_watch.py -q` → 152 passed
  - `wc -l scripts/hermes_watch.py tests/test_hermes_watch.py` → 3820 / 4453 LOC

---

## 한 줄 결론
**지금 시스템은 R19까지 “형식상 도달”했고, 실제 정체성은 `evidence-aware orchestration substrate + shallow harness revision substrate`다. 즉, 반자동 퍼징 제어면으로는 꽤 성숙했지만, 아직 진짜 자가발전형 퍼징 에이전트라고 부르기엔 이르다.**

## 현재 단계 판정

### 공식 단계 판정
- **R19까지 진행됨**

### 단, 정확한 해석
- **R18**: measured execution quality loop는 실제로 들어갔다
  - probe/build/smoke/verification evidence가 registry/scheduler에 반영됨
- **R19**: harness skeleton generation + revision loop는 들어갔다
  - selected candidate 기준 skeleton draft 생성
  - feedback 기반 revision artifact 생성

### 하지만 과장 없이 말하면
- 지금의 R19는
  - **compile/fix/verify가 닫힌 autonomous revision loop**가 아니라
  - **artifact-first skeleton drafting + shallow revision substrate**다
- 따라서 현재 단계는
  - **“R19 substrate complete”**
  - **“autonomous revision intelligence not yet real”**
  로 보는 게 가장 정확하다

---

## 냉정한 전체 평가

### 잘 된 점
1. **control-plane은 꽤 많이 자랐다**
   - watcher → policy → queue → orchestration → dispatch → bridge → launcher → verification 흐름이 실제로 이어진다
2. **evidence-aware 전환이 시작됐다**
   - heuristic-only 후보 선택에서 한 단계 벗어났다
3. **target-side intelligence 초입이 실제 artifact로 내려왔다**
   - profile / recon / candidate / evaluation / probe / skeleton까지 연결됐다
4. **artifact/lineage 문화는 좋다**
   - 나중에 왜 이런 결정을 했는지 되짚기 쉽다

### 부족한 점
1. **상태머신이 분산돼 있다**
   - `status`, `orchestration_status`, `dispatch_status`, `bridge_status`, `launch_status`, `verification_status`, `verification_policy_status`, `lifecycle`
   - single source of truth가 없다
2. **artifact-heavy drift가 있다**
   - 실제 실행력보다 json/md/request/script 산출물이 더 빨리 늘어난 구간이 있다
3. **retry semantics가 약하다**
   - 실제 retry라기보다 retry artifact/policy labeling에 더 가깝다
4. **multi-target는 아직 narrative가 구현보다 앞선다**
   - adapter 형식은 생겼지만 runtime reality는 여전히 OpenHTJ2K 중심이다
5. **skeleton revision은 아직 얕다**
   - compile 실패 해석 / smoke 실패 원인 구조화 / patch-level 자동 제안은 아직 약하다

---

## 점수화
- control-plane 성숙도: **8.8 / 10**
- flow cohesion: **8.1 / 10**
- 상태모델 일관성: **6.6 / 10**
- 테스트의 helper/contract 신뢰도: **8.4 / 10**
- 운영 안정성: **6.1 / 10**
- multi-target readiness: **5.9 / 10**
- self-improving fuzzing readiness: **6.7 / 10**
- 실제 finding efficiency readiness: **6.8 / 10**

### 한 줄 총평
**운영 제어면은 꽤 성숙했고 방향도 맞다. 하지만 아직은 ‘자가발전형 퍼징 에이전트’라기보다 ‘자가발전을 향한 증거 기반 control-plane substrate’다.**

---

## 가장 강한 비판
1. **상태가 너무 많고 의미가 겹친다**
   - 지금은 테스트가 받쳐줘서 버티지만, 단계가 더 늘면 유지보수 비용이 급격히 커질 가능성이 높다
2. **실행보다 artifact가 앞서는 구간이 있다**
   - 더 많은 문서/manifest가 곧 더 나은 agent intelligence를 의미하진 않는다
3. **테스트는 많지만 end-to-end confidence는 제한적이다**
   - 152개 passing은 좋지만 대부분 helper/contract 수준 신뢰다
4. **운영 안정성 리스크가 남아 있다**
   - CLI hang timeout, malformed nested registry, duplicate work/race, brittle parsing
5. **multi-target은 아직 구조적 준비 단계다**
   - runtime이 target-agnostic하다고 부르기엔 이르다

---

## 다음 핵심 단계
1. **R20 skeleton compile/smoke revision intelligence**
   - skeleton artifact를 실제 build/smoke feedback와 더 강하게 닫기
2. **canonical lifecycle 정리**
   - 분산 상태필드를 단일 lifecycle 축으로 재정렬
3. **retry semantics를 실제 retry로 올리거나 이름을 정직하게 바꾸기**
4. **운영 안정성 보강**
   - timeout, malformed registry, duplicate-processing, CLI drift 대응
5. **target adapter 실체화**
   - multi-target 일반화 narrative를 runtime reality로 끌어오기

---

## 최종 판정
**실패한 방향은 아니다. 오히려 꽤 영리하게 잘 쌓아왔다.**
다만 현재 단계의 가장 정확한 이름은:

## `semi-autonomous, artifact-first, evidence-aware fuzz control-plane prototype`

이다.

즉,
- **on-track:** 예
- **R19 claim:** 형식상 예, 실질은 얕은 revision substrate 수준
- **already self-improving agent:** 아니오
- **가장 큰 병목:** state-machine drift + artifact-heavy drift + runtime robustness 부족
