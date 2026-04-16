# 2026-04-16 — hermes_watch LLM evidence packet v0.1 note

## 왜 이 단계를 먼저 넣었나
사용자 목표를 다시 점검한 결과,
최근 시스템은 recovery/control-plane/adapter 일반화 쪽으로 많이 확장됐지만
**LLM이 실제로 더 잘 고치게 만드는 입력 패킷**은 아직 약했다.

그래서 이번 단계는 multi-target polish를 더 밀지 않고,
`latest run/probe/apply artifacts -> failure reason extraction -> LLM-facing packet`
이라는 가장 얇은 증거 경로를 먼저 만들었다.

## 이번에 실제로 한 것
- `scripts/hermes_watch_support/llm_evidence.py` 추가
- latest artifact 수집 대상:
  - `fuzz-artifacts/current_status.json`
  - `fuzz-records/probe-feedback/*-probe-feedback.json`
  - `fuzz-records/harness-probes/*-harness-probe.json`
  - `fuzz-records/harness-apply-candidates/*-harness-apply-candidate.json`
  - `fuzz-records/harness-apply-results/*-harness-apply-result.json`
- 규칙 기반 failure reason 추출 추가
- `llm_objective`를 reason 우선순위에서 압축
- `fuzz-records/llm-evidence/*-llm-evidence.json|md` 출력 추가
- CLI path `--write-llm-evidence-packet` 추가

## v0.1에서 추출하는 이유 코드
- `build-blocker`
- `smoke-invalid-or-harness-mismatch`
- `no-crash-yet`
- `repeated-crash-family`
- `shallow-crash-dominance`
- `harness-build-probe-failed`
- `harness-smoke-probe-failed`
- `guarded-apply-blocked`

## 의미
이 단계는 아직 LLM handoff를 완전히 바꾼 건 아니다.
하지만 이제 system은 최소한:
- 최신 증거를 한곳에 모으고
- 왜 실패했는지의 1차 이유를 구조화해서
- 다음 LLM 호출이 어디에 집중해야 하는지(`llm_objective`)를 먼저 적어준다.

즉 이건 control-plane 확장보다
**LLM 입력 품질 개선 쪽으로 우선순위를 돌렸다는 첫 실제 코드 변화**다.

## 냉정한 한계
- 아직 raw fuzz log 전체를 semantic하게 읽는 수준은 아니다.
- coverage plateau / corpus stagnation / stage reach failure는 아직 얕다.
- current design은 여전히 latest-artifact selection에 의존한다.
- correction/delegate path가 새 packet을 자동 우선 소비하는 단계는 아직 아니다.

한 줄로 줄이면:
**이번 단계는 LLM-first loop의 시작점은 만들었지만, 아직 진짜 좋은 failure analysis engine은 아니다.**

## 다음 자연스러운 단계
1. failure reason extraction v0.2
   - no-progress / repeated shallow crash / stage reach failure / corpus stagnation 강화
2. LLM handoff prompt simplification
   - correction/delegate path가 evidence packet을 우선 읽도록 연결
3. 그 다음에만 필요한 구조 보강
