# Hermes Watch — deeper semantic diff safety / corrective intent analysis v0.1

- Date: 2026-04-16
- Scope: guard-only patch safety를 pattern substring 허용에서 token-aware exact-match 쪽으로 강화

## 왜 이 단계가 필요한가
지금까지의 guard-only safety는 꽤 유용했지만 아직 빈틈이 있었다.
대표적으로:
- `LLVMFuzzerTestOneInput` 문자열만 포함하면 signature mutation도 통과할 수 있었고
- `if (size < 4)` 문자열만 포함하면 inline side-effect를 섞은 줄도 통과할 수 있었다.

즉 표면적으로는 guard patch처럼 보여도,
실제로는 함수 시그니처를 바꾸거나 side-effect를 끼워 넣는 식의 **의미적으로 더 위험한 수정**이 아직 가능했다.

이번 단계는 그 빈틈을 막는 최소 semantic hardening이다.

## 이번에 붙인 것
### 1. token-aware guard-only line validation helper
새 helper:
- `_guard_only_line_allowed(stripped)`

이 helper는 guard-only scope에서 변경된 라인이 아래 exact intent에 맞는지 본다.
허용 범위:
- canonical `LLVMFuzzerTestOneInput(...) {` signature
- `if (size < 4)` / `if (size < 4) {`
- `return 0;`
- brace / blank line
- Hermes comment line

즉 이제는 단순 substring 포함 여부가 아니라,
**허용된 guard-intent token 모양 자체**를 본다.

### 2. signature mutation 차단
이제 다음 같은 수정은 차단된다.
- `int LLVMFuzzerTestOneInput(..., int mode) {`

즉 entrypoint line에 `LLVMFuzzerTestOneInput` 문자열이 들어 있다고 해서 자동 허용되지 않는다.

### 3. inline side-effect guard line 차단
이제 다음 같은 수정도 차단된다.
- `if (size < 4) { helper(); return 0; }`

즉 guard line에 허용 패턴 문자열이 들어 있다고 해서,
그 안에 추가 side-effect나 call expression을 섞는 것을 더 이상 허용하지 않는다.

## 이번 TDD에서 실제 검증한 것
### 1. guard-only signature mutation 차단
entrypoint signature에 extra parameter를 끼워 넣는 patch를 주입했을 때:
- `apply_status = blocked`
- `diff_safety_status = blocked`
- `guard-only-non-whitelisted-edit`

로 막히는지 확인했다.

### 2. guard-only inline side-effect 차단
`if (size < 4)` guard 안에 `helper();` side-effect를 섞은 patch를 주입했을 때:
- `apply_status = blocked`
- `diff_safety_status = blocked`
- `guard-only-non-whitelisted-edit`

로 막히는지 확인했다.

## 의미
이번 단계 이후 guard-only patch safety는:
- touched-region 기반
- whitelist 기반
- 이제 token-aware exact-match 기반

으로 한 단계 더 깊어졌다.

즉 control-plane은 이제 단순히 “entrypoint 안에서만 수정했는가”를 넘어서,
**그 수정이 정말 guard-intent에 맞는 모양인가**까지 보기 시작한다.

## 아직 일부러 안 한 것
이번 v0.1에서도 아직 안 한 것:
- full parser/AST 기반 C syntax understanding
- assignment / call / literal / macro level semantic token classifier
- target-specific editable region model
- diff 내용과 delegate summary intent의 양방향 consistency scoring

즉 지금은 parser-level safety가 아니라,
**cheap but meaningful token-aware hardening** 단계다.

## 냉정한 평가
좋아진 점:
- guard-only safety의 허점 두 개(signature mutation, inline side-effect)를 실제로 닫았다
- string-substring whitelist보다 훨씬 덜 허술해졌다
- low-cost guardrail 대비 효과가 좋다

아직 부족한 점:
- AST 수준 의미 이해는 아니다
- comment-only scope 쪽 semantic intent analysis는 아직 얕다
- corrective patch의 broader semantic correctness는 여전히 probe/build/smoke에 많이 의존한다

## 다음으로 자연스러운 단계
다음은:
- full recovery ecosystem recursion
또는
- comment-only/guard-only beyond exact-line rules로 가는 deeper intent analysis

인데, 현재 control-plane 균형상 다음 우선은 recursion ecosystem 쪽이 더 자연스럽다.
