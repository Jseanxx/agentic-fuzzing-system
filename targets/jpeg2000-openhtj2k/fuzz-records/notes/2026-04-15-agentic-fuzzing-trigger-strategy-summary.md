# Agentic fuzzing trigger strategy summary

## 핵심 질문
- 왜 하네스가 처음부터 완벽하지 못한가?
- 퍼징 몇 시간 돌리고 결과를 보고 하네스를 수정하는 방식이 맞는가?
- 자동/자가발전형 퍼징에서는 어떤 신호를 트리거로 삼아야 하는가?
- 타겟마다 트리거와 운영 루틴이 달라져야 하는가?
- 현재 내 환경에서는 어떤 단계별 운영 구조가 최선에 가까운가?

## 핵심 결론
- 완벽한 하네스는 처음부터 만들기 어렵다.
- 실제 퍼징 운영은 `실행 -> coverage/crash/timeout/stability 관찰 -> 하네스/시드 수정 -> 재실행` 루프가 정석에 가깝다.
- AI/agent를 붙이더라도 현재 주류는 완전자율보다 `trigger-based semi-autonomous` 운영이다.
- 고정 주기만으로 개선하는 것보다 `coverage plateau`, `shallow crash dominance`, `timeout/hang surge`, `corpus bloat`, `stability drop`, `deep write-flavor crash emergence` 같은 트리거 기반 개입이 더 효과적이다.
- 현재 환경에서는 `공통 트리거 엔진 + 타겟별 프로파일 + 인간 승인 없는 저위험 개입 + 인간 검토가 필요한 고위험 개입` 구조가 가장 현실적이다.

## 왜 하네스가 처음부터 완벽하지 못한가
1. 타겟 내부 병목과 깊은 경로는 실제로 돌려봐야 드러난다.
2. 깊이/안정성/속도 사이의 타협이 필요하다.
3. 타겟 내부 구조 때문에 하네스 바깥에서도 shallow crash가 섞여 나온다.

## 현대 퍼징 운영에서 실제로 보는 신호
### 가장 중요한 신호
- coverage / feature 증가 추세
- corpus 성장의 질
- dedup된 unique crash family
- timeout / hang / OOM 비율
- stability / determinism
- 가능하면 stage-aware semantic telemetry

### 보조 신호
- bitmap/map density
- exec/s
- dictionary 효과
- compare tracing 효과

## 자동 개입 트리거
### 하네스/시드/운영 개선 트리거
- coverage plateau
- shallow crash dominance
- timeout/hang surge
- corpus bloat with low gain
- stability drop

### 계속 돌려야 하는 좋은 신호
- deep decode/block/tile/idwt 함수에서 새 crash family 등장
- write-flavor / stack-buffer-overflow / UAF 등장
- coverage가 아직 느리게라도 증가

## 타겟별 차이
- 트리거의 큰 분류는 공통으로 가져갈 수 있다.
- 하지만 트리거의 임계값, stage 정의, 좋은 seed의 기준, 위험한 crash의 우선순위는 타겟별로 달라진다.
- 따라서 `공통 프레임워크 + 타겟별 프로파일` 구조가 바람직하다.

## 타겟 분석 루틴
타겟 분석은 루틴에 넣는 것이 맞다. 다만 한 번만 하는 정적 분석이 아니라 아래 두 축이 같이 있어야 한다.
1. 사전 분석
   - 포맷/프로토콜 구조
   - 주요 API와 상태 전이
   - 무거운 경로와 얕은 경로
   - 위험 함수군
2. 실행 중 분석
   - 어떤 stage까지 실제로 도달하는지
   - 어떤 crash family가 반복되는지
   - 어떤 seed가 깊게 들어가는지
   - timeout/OOM/stability 패턴

## 추천 운영 구조
- 공통 엔진:
  - crash dedup
  - coverage plateau 감지
  - timeout/hang 감지
  - corpus quality 감지
  - stability 감지
- 타겟별 프로파일:
  - stage 목록
  - 위험 함수 목록
  - seed 클래스
  - dictionary
  - compare tracing 여부
  - resource gate
  - alert severity rule

## 단계별 운영 구조 v1
### 1단계: 타겟별 초기 설계
- 타겟 구조 분석
- 위험 경로 정의
- 하네스 설계
- seed/corpus 초안 구성
- 관찰할 semantic stage 정의

### 2단계: 퍼징 실행
- 짧은 sanity run
- short evaluation run
- overnight run
- 시간창과 별개로 trigger 기반 관찰 병행

### 3단계: 자동/반자동 재평가
다음을 판정한다.
- 현재 하네스가 shallow path만 도는지
- 현재 하네스가 더 위험한 deep path로 수정 가능한지
- 지금은 그냥 더 돌리는 게 맞는지

### 4단계: 멈춤 -> 재분석 -> 수정
트리거가 의미 있게 발동하면:
- crash family 분류
- coverage/stage 분포 확인
- seed quality 재평가
- 하네스/옵션/코퍼스 수정
- 새 버전 캠페인 시작

### 5단계: 버전 관리된 재실행
- run root를 분리
- watcher도 새 run으로 교체
- old run/watcher는 pause 또는 종료
- status note를 남겨 비교 가능하게 만든다.

## OpenHTJ2K 맥락에서의 해석
- OpenHTJ2K는 parser/main-header 쪽과 deep decode/tile/block/idwt/lifecycle 쪽의 성격 차이가 크다.
- 따라서 stage-aware 운영이 중요하다.
- `ht_block_decoding.cpp`, `coding_units.cpp`, `idwt.cpp`, `add_tile_part`, `decode_line_based` 같은 deep hotspot은 높은 우선순위로 추적한다.
- parser shallow crash가 과도하게 우세하면 하네스/seed를 다시 조정한다.

## 현재 환경 기준 냉정한 평가
### 좋은 점
- WSL + Proxmox 분리 구조라서 로컬 설계/수정과 원격 장기 실행을 나눌 수 있다.
- `js`에서 AFL++ 장기 캠페인을 안정적으로 돌릴 수 있다.
- 이미 target-specific Discord logging과 cron watcher가 있어 운영 루프를 닫기 쉽다.
- 하네스 v1 -> v2 -> v3로 실제 iterative refinement를 이미 해봤기 때문에 이 구조를 적용할 기반이 있다.

### 부족한 점
- 아직 semantic stage telemetry가 충분히 자동화돼 있지 않다.
- dedup/triage는 부분 자동화됐지만 여전히 stack 기반 분류 품질을 더 높일 수 있다.
- compare tracing, dictionary efficacy, corpus distillation 같은 자동 액션은 아직 체계화가 덜 됐다.
- local WSL에 afl 툴이 없어서 일부 루프 검증이 원격 의존적이다.
- 완전 autopilot로 두기엔 아직 타겟별 프로파일과 stop/revise policy가 덜 기계화돼 있다.

## 점수 평가 (현재 환경 기준)
### 총점
- **8.4 / 10**

### 항목별
- 구조 적합성: **9.2 / 10**
  - 지금 네 환경과 목표에는 매우 잘 맞다.
- 실전성: **9.0 / 10**
  - 이미 overnight 운영과 버전 교체에 들어갈 수 있다.
- 자동화 성숙도: **7.6 / 10**
  - watcher/cron은 있지만, semantic trigger 자동화는 더 필요하다.
- 퍼징 효율 잠재력: **8.7 / 10**
  - shallow/deep를 구분해 개입하는 구조라 효율이 좋다.
- 완전자율성: **6.8 / 10**
  - 지금은 완전자율보다 반자동이 맞다.

## 냉정한 최종 의견
- **현재 네 환경에서는 이 구조가 거의 최선에 가깝다.**
- 더 좋은 대안이 있다면 완전 autopilot형인데, 지금 상태에서 그쪽으로 가면 오히려 오판과 잡음이 늘 가능성이 높다.
- 즉 지금은 **반자동 자기개선 루프**가 맞고, 그 위에 점진적으로 semantic telemetry와 target profile automation을 얹는 게 가장 현명하다.

## 다음 우선순위
1. target profile 실파일 작성
2. stage tagging 자동화
3. crash family dedup 고도화
4. corpus quality / plateau / timeout 트리거 자동 액션 연결
5. compare tracing / dictionary 실험 루프 연결

## 한 줄 정리
- 자가발전형 퍼징은 `타겟마다 완전히 다른 시스템`이 필요한 것은 아니지만,
- `공통 트리거 프레임워크 위에 타겟 분석 기반 프로파일`을 얹는 방식이 가장 현실적이고 강하다.
- 현재 네 환경에서 이 구조는 **8.4/10 수준으로 꽤 좋고, 지금 시점 기준 최선에 가까운 방향**이다.
