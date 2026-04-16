# Hermes Watch — R20 retry recursive chaining / termination guard v0.1

- Date: 2026-04-15
- Scope: retry full-chain을 여러 cycle 반복하되, 종료 조건과 최대 반복 수를 둬 무한 루프를 막음

## 왜 이 단계가 필요한가
이전 단계에서 retry lane은 이미:
- consume
- rearm
- launch
- verify
- apply
- reroute
까지 이어졌다.

하지만 아직 진짜 마지막 결절점이 남아 있었다.
바로:
**reroute 결과가 다시 `retry`일 때 다음 cycle로 한 번 더 들어갈 수는 있어도, 이를 loop로 돌리는 명시적 recursion/termination guard가 약했다는 점**이다.

이 guard가 없으면 시스템은 두 가지 위험을 가진다.
1. 반복 시도 자체를 충분히 못 해서 retry rail의 실효성이 약해질 수 있음
2. 반대로 무한 반복으로 빠져 control-plane을 오염시킬 수 있음

## 이번에 붙인 것
### 1. retry recursive chaining 함수 사용 경로 완성
`run_harness_apply_retry_recursive_chaining(repo_root, max_cycles=3)`는 이미 retry full-chain을 반복할 수 있게 설계되어 있었고,
이번 단계에서 main CLI 경로를 실제로 연결했다.

새 CLI:
- `--run-harness-apply-retry-recursive-chaining`

즉 이제 retry recursive chaining을 명시적으로 실행할 수 있다.

### 2. termination guard semantics 명시화
현재 v0.1 종료 규칙:
- reroute 결과가 `retry`가 아니면 종료
- `resolved / aborted / hold / stopped`는 종료 상태로 반환
- `retry`가 계속되면 `max_cycles`에 도달했을 때
  - `recursive_chain_status = max-cycles-reached`
  - `cycle_count = max_cycles`
  로 종료

즉 retry rail은 이제
**계속 가야 할 때는 조금 더 가고, 멈춰야 할 때는 명시적으로 멈추는 최소 guard**를 가진다.

### 3. recursive chain lineage
manifest에는 다음이 남는다.
- `recovery_recursive_chain_status`
- `recovery_recursive_chain_cycle_count`
- `recovery_recursive_chain_checked_at`

즉 나중에
- 몇 번 돌았는지
- 왜 멈췄는지
- guard에 걸렸는지
를 읽을 수 있다.

## 의미
이번 단계 이후 retry lane은 다음처럼 보인다.

- retry full-chain 1회
- reroute가 다시 retry면 다음 cycle
- retry가 아니면 종료
- max cycle 도달 시 강제 종료

즉 이제 retry rail은
**단순한 1회성 chained retry가 아니라, bounded recursive retry loop**
로 진입했다.

이건 중요하다.
여기까지 오면 control-plane은 “retry를 다시 시도할 수 있다” 수준을 넘어,
“retry를 몇 번까지 반복하고 어디서 멈출지 안다”는 수준으로 올라간다.

## 아직 일부러 안 한 것
이번 v0.1에서도 아직 안 한 것:
- cycle 간 cooldown / backoff
- failure class별 max cycle 차등화
- hold/abort lane의 실제 downstream consumer 강화
- retry recursive chain이 자동으로 새 correction policy를 재생성하는 경로
- semantic diff safety의 더 깊은 touched-region/function 단위 검증

즉 지금은 bounded recursion은 있지만,
정교한 운영 정책은 아직 약하다.

## 냉정한 평가
좋아진 점:
- retry loop가 진짜 loop처럼 보이기 시작했다
- 최소 termination guard가 생겨 무한 반복 위험이 줄었다
- recursive retry의 상태가 artifact로 남아 추적 가능하다

여전히 부족한 점:
- main하게 추가된 것은 CLI 연결과 termination semantics 확정이지, 새로운 지능이 크게 늘어난 건 아니다
- max cycle이 아직 고정/단순하다
- hold/abort lane은 여전히 retry lane보다 훨씬 얕다
- semantic safety보다 orchestration 완성도가 더 빨리 올라간 상태다

## 다음 단계
가장 자연스러운 다음 단계는:
- hold/abort downstream consumer 강화
- retry cooldown / budget / priority 고도화
- patch diff scope / touched-region safety 강화

즉 다음은:
**R20 hold/abort downstream consumers**
또는
**R20 patch diff scope / touched-region safety**
가 자연스럽다.
