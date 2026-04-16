# Hermes Watch — R20 recovery full closed-loop chaining v0.1

- Date: 2026-04-15
- Scope: retry lane에서 verify 이후 guarded apply와 recovery reroute까지 다시 연결

## 왜 이 단계가 필요한가
이전 단계까지 retry lane은:
- queue consume
- bridge rearm
- launch
- verify
까지 이어졌다.

하지만 아직 마지막 연결이 남아 있었다.
바로:
**verify가 끝난 뒤 다시 apply와 reroute로 돌아가는 chaining이 비어 있었다는 점**이다.

이 간격 때문에 retry lane은 꽤 많이 닫혔지만,
엄밀히 말하면 아직 완전한 self-consuming loop는 아니었다.

## 이번에 붙인 것
### 1. full closed-loop chaining 함수 추가
`run_harness_apply_recovery_full_closed_loop_chaining(repo_root)`를 추가했다.

현재 v0.1 흐름:
1. 기존 `run_harness_apply_recovery_downstream_automation(...)` 실행
2. retry downstream이 `verification_status=verified`까지 도달하면
3. `apply_verified_harness_patch_candidate(...)` 실행
4. apply 결과를 바탕으로 `route_harness_apply_recovery(...)`를 다시 실행

즉 retry lane은 이제:
- consume
- rearm
- launch
- verify
- apply
- reroute
까지 이어진다.

### 2. full-chain status lineage
apply candidate manifest에:
- `recovery_full_chain_status`
- `recovery_full_chain_checked_at`
- `recovery_full_chain_apply_status`
- `recovery_full_chain_reroute_decision`
- `recovery_full_chain_reroute_action_code`
를 기록한다.

즉 full-chain도 artifact 상에서 역추적 가능하다.

### 3. CLI 추가
새 CLI:
- `--run-harness-apply-recovery-full-closed-loop-chaining`

이제 retry lane의 consume→execute→reroute를 한 번에 실행할 수 있다.

## 의미
이번 단계 이후 retry lane은 다음처럼 닫힌다.

- recovery decision = retry
- recovery routing
- recovery queue placement
- recovery queue consumption
- bridge rearm
- launch
- verify
- guarded apply
- reroute

즉 이제 retry rail은 거의 명백한 의미에서
**retry-centered closed loop**로 진입했다.

이건 중요한 진전이다.
여기까지 오면 retry는 단순 재시도 표식이 아니라,
실제로 다음 cycle로 다시 스스로 들어가는 rail이 된다.

## 아직 일부러 안 한 것
이번 v0.1에서도 아직 안 한 것:
- reroute 이후 next cycle을 다시 자동 재귀 실행하는 chaining
- hold lane의 실제 review consumer / Discord hold lane 연결
- abort lane의 correction regeneration / deeper corrective route 연결
- retry budget / cool-down / launch backoff / priority 고도화

즉 retry lane은 꽤 닫혔지만,
전체 recovery ecosystem이 완전 자동은 아니다.

## 냉정한 평가
좋아진 점:
- retry rail은 이제 verify 이후 apply와 reroute까지 닫혔다
- 실제로 loop다운 느낌이 생겼다
- control-plane이 상태 기록에서 실행 연쇄로 한 단계 더 진화했다

여전히 부족한 점:
- reroute 이후 next cycle을 다시 자동 재귀 실행하지는 않는다
- hold lane은 여전히 review parking 수준이다
- abort lane도 terminal 기록 후 deeper correction route가 없다
- safety 측면에선 patch diff semantics/touched-region 검증이 아직 얕다

## 다음 단계
가장 자연스러운 다음 단계는:
- hold/abort downstream consumer 강화
- patch diff scope / touched-region safety 강화
- retry 운영 규칙(cooldown/budget/priority) 고도화

즉 다음은:
**R20 hold/abort downstream consumers**
또는
**R20 patch diff scope / touched-region safety**
가 자연스럽다.
