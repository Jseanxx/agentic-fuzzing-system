# Checklist — Hermes Watch deeper semantic diff safety / corrective intent analysis v0.1

- [x] guard-only token-aware line validation helper 추가
- [x] canonical entrypoint signature exact-match 허용 규칙 추가
- [x] inline side-effect가 섞인 guard line 차단 규칙 추가
- [x] TDD로 guard-only signature mutation 차단 테스트 추가 후 실패 확인
- [x] TDD로 guard-only inline side-effect 차단 테스트 추가 후 실패 확인
- [x] targeted semantic safety tests 통과 확인
- [ ] comment-only semantic intent hardening 추가 검토
- [ ] AST/token classifier 확장 필요성 재평가
- [ ] function/token-aware diff classification 다음 slice 설계

## 검증 명령
- `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_apply_verified_harness_patch_candidate_blocks_guard_only_signature_mutation tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests::test_apply_verified_harness_patch_candidate_blocks_guard_only_inline_side_effect -q`
- `python -m pytest tests/test_hermes_watch.py::HermesWatchHarnessSkeletonDraftTests -q`
- `python -m pytest tests/test_hermes_watch.py -q`
- `python -m pytest tests -q`
- `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/harness_skeleton.py scripts/hermes_watch_support/__init__.py tests/test_hermes_watch.py`
