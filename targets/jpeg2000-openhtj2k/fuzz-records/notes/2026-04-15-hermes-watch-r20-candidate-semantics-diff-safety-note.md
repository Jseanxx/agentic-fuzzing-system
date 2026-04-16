# Hermes Watch — R20 candidate semantics / diff safety v0.1

- Date: 2026-04-15
- Scope: verified apply candidate를 실제 source에 반영하기 전에 patch 의미/범위를 먼저 차단하는 guardrail 추가

## 왜 이 단계가 필요한가
이전 단계에서 system은:
- verified patch-candidate를 제한적으로 apply하고
- build/smoke rerun을 수행하고
- 실패 시 rollback까지 할 수 있게 됐다.

하지만 아직 중요한 빈틈이 있었다.
바로:
**apply 전에 그 patch candidate가 정말 허용 범위의 의미를 갖는지, 그리고 target/diff 범위가 충분히 좁은지 미리 막는 단계가 약했다는 점**이다.

rollback이 있다고 해도,
애초에 위험한 apply를 자주 시도하면 control-plane은 noisy해지고
working harness를 불필요하게 흔들게 된다.

## 이번에 붙인 것
### 1. candidate semantics guardrail
`apply_verified_harness_patch_candidate(...)`가 delegate artifact summary를 읽고
현재 scope와 맞는 의미인지 먼저 확인한다.

현재 v0.1 기준:
- `guard-only`는 `guard/size/input/smoke/seed/early return` 계열 의도가 summary에 보여야 함
- 다음 같은 out-of-scope 표현이 보이면 차단함
  - `rewrite build`
  - `build script`
  - `CMakeLists`
  - `meson.build`
  - `Makefile`
  - `rename`
  - `entrypoint`
  - `persistent mode`
  - `delete/remove`

즉 지금은 deep semantic verifier는 아니지만,
적어도 **작은 guard/comment patch rail에 build-system rewrite나 entrypoint rename 같은 요청이 섞이면 바로 막는다.**

### 2. diff safety guardrail
semantics가 통과한 뒤에는 실제 injected patch를 기준으로
다음 범위 제한을 확인한다.

- target file이 `fuzz-records/harness-skeletons/` 아래 generated harness인지 확인
- changed line count 상한 확인
  - `comment-only`: 최대 2 line
  - `guard-only`: 최대 6 line

즉 이제는:
- 아무 파일이나 건드리는 apply
- generated harness 바깥 파일을 건드리는 apply
- bounded mutation이라 보기 어려운 line churn
을 차단한다.

### 3. blocked apply lineage 기록
guardrail에 막힌 경우에도 그냥 조용히 끝내지 않고:
- `apply_status = blocked`
- `apply_guardrail_status = blocked`
- `candidate_semantics_status`
- `diff_safety_status`
- 관련 summary/reasons
를 `harness-apply-results/`와 apply candidate manifest에 남긴다.

즉 다음 단계는
“왜 apply가 실행되지 않았는가”를 artifact로 읽을 수 있다.

## 의미
이번 단계 이후 apply loop는 다음처럼 바뀌었다.

- verified patch-candidate
- candidate semantics check
- diff safety check
- 통과한 경우에만 limited apply
- build/smoke rerun
- 실패 시 rollback

이건 중요하다.
이제 system은 단순히 “고쳐보고 실패하면 되돌리는” 수준이 아니라,
**애초에 rail 밖의 수정은 apply 전에 막는 구조**를 갖기 시작했다.

즉 rollback 이전에 preventive guardrail이 생겼다.

## 아직 일부러 안 한 것
이번 단계에서도 아직 안 한 것:
- AST/CFG 수준 semantic validation
- touched function count / touched region count 같은 더 정교한 diff policy
- delegate artifact의 실제 unified diff parsing
- rollback 이후 retry / hold / abort를 나누는 multi-step recovery policy
- finding-quality objective와의 직접 연결

즉 지금은 strict formal verifier가 아니라,
**bounded mutation rail을 지키기 위한 first-pass semantics/diff gate**다.

## 냉정한 평가
좋아진 점:
- 위험한 patch summary를 apply 전에 차단할 수 있게 됐다
- generated harness 밖 파일 오염을 막는 최소 diff safety가 생겼다
- blocked apply도 artifact로 남아 lineage가 더 선명해졌다
- rollback에만 의존하던 safety 모델에서 한 단계 전진했다

여전히 부족한 점:
- semantics 판단은 keyword 기반이라 아직 얕다
- diff safety도 changed line 수 + 경로 제한 수준이라 충분히 깊진 않다
- “작다”는 건 보지만 “정말 타당하다”는 건 아직 약하다

## 다음 단계
가장 자연스러운 다음 단계는:
- rollback 이후 `retry / hold / abort`를 나누는 multi-step recovery policy
- delegate artifact diff scope/touched region 검증 강화
- coverage/stage reach/novelty를 patch quality objective에 연결

즉 다음은:
**R20 multi-step recovery policy**
또는
**R20 patch diff scope / touched-region safety**
가 가장 자연스럽다.
