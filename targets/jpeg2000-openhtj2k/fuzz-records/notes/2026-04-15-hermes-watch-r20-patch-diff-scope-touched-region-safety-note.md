# Hermes Watch — R20 patch diff scope / touched-region safety v0.1

- Date: 2026-04-15
- Scope: generated harness 내부에서도 touched region / whitelist 수준의 diff safety를 더 세밀하게 검증

## 왜 이 단계가 필요한가
이전 단계의 diff safety는 이미 의미가 있었다.
- generated harness 디렉터리 밖 파일 차단
- changed line count 상한 적용

하지만 아직 충분하진 않았다.
왜냐하면 generated harness 안쪽이라도:
- 전혀 다른 helper 함수
- entrypoint 바깥 영역
- comment-only scope인데 실제 로직 변경
같은 수정이 여전히 통과할 수 있었기 때문이다.

즉 기존 guardrail은
**경로 + 변경 줄 수** 수준이었고,
이번 단계가 필요한 이유는
**같은 파일 안에서도 어디를 어떤 형태로 건드렸는지**를 보게 만들기 위해서다.

## 이번에 붙인 것
### 1. fuzzer entrypoint touched-region 판정
새 helper:
- `_find_fuzzer_entrypoint_region(content)`

이 함수는 `LLVMFuzzerTestOneInput` 함수의 line region을 잡는다.

그리고 guard-only scope에서는 diff hunk가 touching 하는 원본 line들이
이 region 밖을 건드리면 차단한다.

차단 reason 예:
- `touched-region-outside-fuzzer-entrypoint`

즉 guard-only patch는 이제
**generated harness 안이라도 아무 함수나 건드릴 수 없고, fuzzer entrypoint 내부에만 머물러야 한다.**

### 2. scope별 whitelist 강화
#### comment-only
이제 comment-only는 다음만 허용한다.
- EOF append
- inserted line이 `Hermes guarded apply candidate` 계열 comment인 경우

즉 comment-only scope인데 실제 코드 로직을 바꾸는 inline edit는 차단된다.

차단 reason 예:
- `comment-only-non-whitelisted-edit`

#### guard-only
guard-only는 이제 다음 계열 line만 허용한다.
- `LLVMFuzzerTestOneInput` signature line
- `Hermes guarded apply candidate` comment
- `if (size < 4)` guard
- `return 0;`
- brace/blank line

즉 guard-only scope라도
entrypoint 내부에서 임의의 다른 코드 편집은 차단된다.

차단 reason 예:
- `guard-only-non-whitelisted-edit`

### 3. multi-hunk baseline 추가
diff hunk 수를 세고,
여러 군데를 건드리는 patch는 baseline에서 차단한다.

차단 reason:
- `multi-hunk-diff-not-allowed`

즉 이제는 한 번의 apply가
**한정된 좁은 위치에서 한 덩어리 수정**이라는 전제가 더 명시적이다.

### 4. diff lineage 메타데이터 확장
이제 diff safety 결과에 추가로 남는다.
- `diff_hunk_count`
- `diff_touched_region_status`
- `diff_touched_region_summary`

그리고 blocked return payload에도
- `diff_safety_reasons`
- touched-region metadata
를 직접 포함시켰다.

즉 blocked reason이 이제
단순 blocked/pass를 넘어서
**왜 막혔는지, region 문제인지 whitelist 문제인지** 바로 읽힌다.

## 의미
이번 단계 이후 diff safety는:
- path safety
- changed line count safety
- touched region safety
- scope whitelist safety
- single-hunk bounded mutation

까지 보게 됐다.

즉 guardrail은 이제
**“generated harness 안인지”만 보는 수준**에서,
**“generated harness 안에서도 fuzzer entrypoint의 허용된 작은 패턴만 건드리는지”를 보는 수준**으로 올라갔다.

## 이번 TDD에서 실제 검증한 것
### 1. guard-only가 helper 함수 쪽을 건드리면 차단
monkeypatch로 `_inject_guarded_patch(...)`를 바꿔
fuzzer entrypoint가 아닌 helper function line을 수정하게 만들었고,
이 경우:
- `apply_status = blocked`
- `diff_safety_status = blocked`
- `touched-region-outside-fuzzer-entrypoint`
를 확인했다.

### 2. comment-only가 실제 코드 로직을 바꾸면 차단
comment-only scope인데 inline `return` 값을 바꾸는 patch를 주입했고,
이 경우:
- `apply_status = blocked`
- `diff_safety_status = blocked`
- `comment-only-non-whitelisted-edit`
를 확인했다.

## 아직 일부러 안 한 것
이번 v0.1에서도 아직 안 한 것:
- AST/token 기반 semantic diff verifier
- 함수 내부에서도 exact statement whitelist / span whitelist 고도화
- target-specific editable region profile
- abort/hold follow-up 결과를 다시 apply loop로 자동 재주입

즉 지금은 deep semantic verifier가 아니라,
**bounded text-diff guardrail을 한 단계 더 정교하게 만든 상태**다.

## 냉정한 평가
좋아진 점:
- generated harness 내부 오염 위험이 줄었다
- comment-only / guard-only의 의미가 더 실제적인 제약이 됐다
- blocked reason이 더 읽기 쉬워졌다
- orchestration이 앞서간 상태에서 safety 계층을 따라붙게 만들었다

여전히 부족한 점:
- 여전히 text-diff 기반이다
- guard-only whitelist는 패턴 기반이라 더 복잡한 안전 수정은 아직 표현력이 약하다
- 진짜 semantic correctness를 판정하는 건 아니다
- function 내부 span whitelist, token-level diff 해석은 아직 없다

## 다음 단계
가장 자연스러운 다음 단계는:
- hold/abort follow-up 결과 auto-reingestion
- retry cooldown/backoff/budget 고도화
- diff safety를 function span / token-aware 수준으로 더 세분화

즉 이제는 safety baseline은 한 단계 더 올라왔고,
다음은 **follow-up 결과를 다시 control-plane에 되먹이거나 diff safety를 더 깊게 semantic화하는 단계**가 자연스럽다.
