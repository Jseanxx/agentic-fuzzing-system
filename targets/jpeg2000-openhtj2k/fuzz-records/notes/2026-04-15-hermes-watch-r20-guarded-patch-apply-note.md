# Hermes Watch — R20 guarded patch apply + build/smoke rerun v0.1

- Date: 2026-04-15
- Scope: verified patch-candidate를 제한된 범위에서 target file에 반영하고 build/smoke rerun 결과를 apply result artifact로 남김

## 왜 이 단계가 필요한가
이전 단계에서 system은:
- child LLM patch-candidate artifact를 launch하고
- 그 결과를 session/artifact/shape/quality 기준으로 검증해 ingest할 수 있었다.

하지만 아직 빠져 있던 것은:
**verified patch-candidate를 실제로 매우 제한된 범위에서 적용하고, rerun 결과를 보는 단계**였다.

즉 이제는 advisory/orchestration만이 아니라,
first-pass 제한적 source mutation까지 들어갔다.

## 이번에 붙인 것
### 1. guarded patch injection
새 함수:
- `apply_verified_harness_patch_candidate(repo_root, probe_runner=...)`

이 함수는 latest verified apply candidate를 읽고:
- `comment-only`
  - target file 끝에 Hermes apply note comment 추가
- `guard-only`
  - `LLVMFuzzerTestOneInput` 시작부에 작은 min-size guard 삽입

처럼 제한된 패턴만 허용한다.

즉 지금은 일반 patch apply가 아니라
**tiny bounded mutation**만 허용한다.

### 2. build/smoke rerun
patch 적용 후 system은:
- `build_harness_probe_draft(repo_root)`로 build/smoke command를 얻고
- build probe 재실행
- build 통과 시 smoke probe 재실행
한다.

결과는 새 artifact로 저장된다.

### 3. apply result artifact
새 경로:
- `fuzz-records/harness-apply-results/`
  - `*-harness-apply-result.json`

이 artifact는:
- target file path
- apply status
- build probe result
- smoke probe result
를 담는다.

동시에 apply candidate manifest에도:
- `apply_status`
- `apply_result_manifest_path`
- `build_probe_status`
- `smoke_probe_status`
- `applied_at`
를 기록한다.

### 4. CLI 추가
- `--apply-verified-harness-patch-candidate`

이제 verified patch-candidate 이후 제한적 apply + rerun을 별도 단계로 실행할 수 있다.

## 의미
이번 단계로 loop는 다음처럼 더 또렷해졌다.

- patch-candidate verification
- limited patch apply
- build rerun
- smoke rerun
- apply result artifact

즉 이제 system은 단순히 patch-candidate를 평가하는 게 아니라,
**작은 범위에서 실제 적용하고 결과를 관찰하는 단계**에 진입했다.

이건 자가발전형 하네스 수정 루프의 첫 번째 진짜 실행 slice다.

## 아직 일부러 안 한 것
이번 단계에서도 일부러 하지 않은 것:
- 실패 시 rollback
- diff size/scope safety 고도화
- patch semantics에 대한 더 깊은 검증
- rerun 결과를 다시 correction policy에 자동 되먹이는 루프

즉 지금은 first-pass apply만 있다.
다음은 rollback/failure recovery가 필요하다.

## 냉정한 평가
좋아진 점:
- 이제 verified patch-candidate를 실제로 반영해볼 수 있다
- rerun 결과가 artifact로 남는다
- advisory loop를 넘어 제한적 실행 loop로 들어왔다

여전히 부족한 점:
- mutation 범위가 매우 단순하다
- guard 삽입 로직은 pattern-driven이라 더 일반적이지 않다
- 실패 시 원복이 아직 없어서 아직 production-safe한 auto-loop는 아니다

## 다음 단계
가장 자연스러운 다음 단계는:
- apply 실패 시 원복하고
- 다음 correction policy를 재생성하거나
- 재시도/보류를 결정하는 failure recovery를 붙이는 것이다.

즉 다음은:
**R20 rollback / failure recovery**
가 가장 자연스럽다.
