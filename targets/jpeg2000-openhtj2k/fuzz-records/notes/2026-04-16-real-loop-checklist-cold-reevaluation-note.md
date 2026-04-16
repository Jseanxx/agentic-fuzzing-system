# Real Loop Checklist Cold Reevaluation Note

- Updated: 2026-04-16 17:52:59 KST
- Project: `fuzzing-jpeg2000`
- Scope: **실사용 루프 점검 체크리스트가 지금 프로젝트 목적에 대해 정말 최선인지 다시 냉정하게 재평가한 기록**

---

## 한 줄 결론
**이전 체크리스트는 나쁘지 않았지만, 아직도 “점검 항목 나열” 성격이 강했고, 네 프로젝트의 진짜 목적(실제 퍼징 효율 개선 검증)보다 packet/readability 쪽을 약간 더 친 상태였다. 그래서 더 냉정한 운영판으로 다시 줄이는 게 맞다.**

---

## 왜 이전 버전이 완전히 최선은 아니었나

### 1. packet 중심으로는 괜찮았지만, 실효성 판정이 약했다
기존 체크리스트는 잘 본 것:
- evidence packet 존재 여부
- reason / narrative / finding summary 품질
- suggested route의 그럴듯함

하지만 부족했던 것:
- **실제 rerun 뒤 무엇이 개선되어야 “성공”인지**가 약했다
- build/smoke pass 여부와 별도로
  - coverage 움직임
  - novelty 움직임
  - shallow crash 탈출
  - 같은 action 반복 여부
  를 더 강하게 go/no-go 기준으로 박아야 했다.

즉 기존 버전은
- “읽기 좋은 packet” 확인에는 괜찮았지만
- “이 루프가 실제로 가치 있나” 판정에는 약간 느슨했다.

### 2. suggested action을 약간 믿는 쪽으로 적혀 있었다
현재 `v0.9`의 `suggested_action_code` / `suggested_candidate_route`는 유용하다.
하지만 냉정하게 보면 이건:
- **semantic planner 결과가 아니라**
- rule-based linkage다.

그래서 체크리스트는
- suggested action을 따르라
가 아니라
- **suggested action을 가설로 취급하고, 실제 rerun 결과로 검증하라**
로 더 명확해야 했다.

### 3. “한 번에 하나만” 원칙은 있었지만, 실패 기록 기준이 약했다
기존에도 한 번에 하나만 수행하라고 적었지만,
더 중요한 건:
- 한 번의 루프에서 무엇을 바꿨는지
- 그 결과가 좋아졌는지/나빠졌는지
- 변화가 없으면 왜 없는지
를 **작게 기록하는 것**이다.

이게 없으면 또 구조 개선으로 도망가게 된다.

### 4. 실제 병목 분류가 3개만으로는 약간 단순했다
기존 분류:
- packet
- harness / target
- apply rail

이건 기본 뼈대로는 맞다.
하지만 실제로는 추가로:
- **run freshness / observability 문제**
  - 최신 run이 아니거나 로그/상태가 어긋나면 packet 품질 평가도 다 틀어진다.
- **LLM output discipline 문제**
  - packet은 괜찮은데 delegate 출력이 자꾸 bounded rail 밖으로 나가면 LLM 개입 품질 자체가 병목이다.

즉 운영용으로는 병목축을 조금 더 정교하게 봐야 한다.

### 5. 이 프로젝트 전체 목적 대비 가장 중요한 질문이 더 앞에 와야 했다
네 목적은:
1. 퍼징 돌린다
2. 정체/실패 신호를 많이 뽑는다
3. LLM이 먹기 좋게 정리한다
4. LLM이 다음 수정 방향을 제안한다
5. 다시 돌린다

그러면 실사용 체크리스트의 최상단 질문은 사실 이것이어야 한다:
- **이번 루프가 실제로 다음 퍼징 iteration의 질을 올렸는가?**

기존 체크리스트는 이 질문이 뒤에 있었다.
그건 우선순위가 약간 뒤집혀 있던 셈이다.

---

## 이번 재평가 기준
이번 수정에서는 다음 기준으로 다시 잘랐다:

1. **freshness 먼저**
   - 최신 run / 최신 evidence / 최신 로그 정합성부터 확인
2. **single-loop discipline**
   - 한 번에 하나만 바꾸고 비교
3. **go / no-go 판정 강화**
   - rerun 뒤 실제 개선 기준을 더 선명하게 기록
4. **suggested action 불신 원칙**
   - 추천 route는 정답이 아니라 가설로 취급
5. **병목 분류 강화**
   - packet / harness-target / apply rail / observability / LLM output discipline
6. **새 기능 추가 금지 원칙 강화**
   - 병목이 확인되기 전엔 구조 확장 금지

---

## 냉정한 전체 판단

### 지금 시스템은 여전히 방향은 맞다
맞는 점:
- evidence packet 품질은 꽤 좋아졌다
- LLM 개입도는 충분히 높다
- bounded apply / rollback / routing 안전장치도 있다
- 실사용 v1 판단을 할 수 있을 정도의 구조는 이미 있다

### 하지만 아직 최종 가치는 증명되지 않았다
아직 미증명:
- 실제 finding efficiency 상승
- shallow crash 탈출 능력
- 하네스 revision의 누적 실효성
- suggested route가 실제로 iteration quality를 올리는 비율

즉 지금 가장 중요한 일은 여전히:
**“더 나은 구조를 만드는 것”이 아니라 “이 구조가 실제 루프에서 쓸모 있는지 증명하는 것”**이다.

---

## 따라서 체크리스트 수정 방향
이번 수정판은 다음 쪽으로 더 기울어야 한다:
- packet readability 확인
n보다
- **실제 loop efficacy 검증**

즉 핵심은:
- 최신 상태 확인
- packet 읽기
- suggested action을 가설로 채택
- 단일 액션 1회
- rerun 비교
- go / no-go
- 병목층 기록

이 순서다.

---

## 최종 한 줄 평가
**이전 체크리스트는 “좋은 operator checklist”였지만, 이번 프로젝트의 진짜 목적에는 아직 약간 친절하고 느슨했다. 이번 수정판은 더 차갑게, 실효성 판정 중심으로 바꾸는 게 맞다.**
