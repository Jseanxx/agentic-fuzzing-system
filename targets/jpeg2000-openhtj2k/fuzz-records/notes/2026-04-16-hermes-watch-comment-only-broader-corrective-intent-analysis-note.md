# Note — comment-only / broader corrective intent analysis v0.1

- Date: 2026-04-16 06:55:29 KST
- Scope: `scripts/hermes_watch.py`, `tests/test_hermes_watch.py`

## 이번 단계에서 한 일
- `comment-only` scope에 대한 semantic intent guardrail을 한 단계 강화했다.
- 기존에는 `comment-only`라도 delegate summary가 실제 코드 수정을 요구하면,
  최종 diff가 append-only Hermes comment라는 이유만으로 apply가 통과할 수 있었다.
- 이제 `_candidate_semantics_guardrails(...)`에서 `comment-only` summary가 아래 성격이면 선제 차단한다.
  - `return` 값 변경 요구
  - `#include` / include 추가 요구
  - helper 호출/삽입 요구
  - signature/logic 수준 변경 요구
- blocked return payload에도 `candidate_semantics_summary`, `candidate_semantics_reasons`를 직접 포함시켜 왜 막혔는지 즉시 읽히게 했다.

## 왜 가치가 있나
이전 단계까지 diff safety는 강했지만,
`comment-only`의 **의도 자체**는 충분히 걸러지지 않았다.
즉,
- patch summary는 실제 코드 변경을 요구하는데
- 현재 bounded apply rail은 comment만 붙이는 상태
인 모순이 남아 있었다.

이번 단계로 최소한:
1. scope와 corrective intent가 정면으로 어긋나는 요청을 apply 전에 차단한다.
2. "안전한 diff라서 통과"가 아니라 "요청 의도도 rail과 맞아야 통과"로 기준이 올라갔다.
3. 이후 broader corrective intent analysis를 더 깊게 갈 때 comment-only 쪽의 첫 semantic baseline이 생겼다.

## 아직 얕은 점
- 아직 AST/CFG 수준 의미 이해는 아니다.
- 자연어 summary의 의도를 키워드 기반으로 읽는 보수적 1차 필터다.
- `comment-only`가 허용해야 할 긍정 패턴(예: note/review/todo/annotation)을 더 정교하게 모델링한 것은 아니다.
- 실제 correction draft 내용과 delegate artifact 본문을 더 깊게 대조하는 단계도 아직 없다.

## 검증
- RED
  - 새 테스트 2개 추가 후 기존 구현에서 실제로 `apply_status=applied`가 나오는 실패를 확인
- GREEN / regression
  - `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_apply_verified_harness_patch_candidate_comment_only_updates_source_and_reruns_probes tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_apply_verified_harness_patch_candidate_blocks_comment_only_summary_requesting_return_mutation tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_apply_verified_harness_patch_candidate_blocks_comment_only_summary_requesting_include_and_helper_call -q`
  - `python -m py_compile scripts/hermes_watch.py tests/test_hermes_watch.py`
  - `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests -q`
  - `python -m pytest tests/test_hermes_watch.py -q`
  - `python -m pytest tests -q`

## 냉정한 평가
이 단계는 화려하진 않다.
하지만 지금 시스템에서 진짜 중요한 건 mutation power 확대가 아니라,
**기존 bounded rail이 스스로 거짓된 의도를 통과시키지 않게 만드는 것**이다.
그 기준에서는 꽤 값진 hardening이다.
다만 finding efficiency를 직접 올리는 단계는 아니고,
control-plane이 과신하지 않도록 만드는 safety/consistency hardening에 가깝다.
