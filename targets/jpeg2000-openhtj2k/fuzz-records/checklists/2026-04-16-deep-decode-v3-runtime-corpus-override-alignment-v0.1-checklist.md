# Checklist — deep-decode-v3 runtime corpus override alignment v0.1

- [x] fresh state inspection으로 `run-fuzz-mode.sh coverage`와 actual fuzzer corpus 로딩 불일치 확인
- [x] root cause를 target profile adapter `fuzz_command`의 hard-pinned `CORPUS_DIR`로 특정
- [x] RED test 추가/수정: env-override friendly fuzz command contract 요구
- [x] RED 확인: `pytest -q tests/test_aflpp_setup.py -k deep_decode_v3_adapter_contract` fail
- [x] target profile `fuzz_command`를 `${FUZZER_BIN:-...}` / `${CORPUS_DIR:-...}` 형태로 수정
- [x] target profile `meta.updated_at` 갱신
- [x] GREEN 확인: `pytest -q tests/test_aflpp_setup.py` pass (`7 passed`)
- [x] full `pytest -q` pass 확인 (`331 passed`)
- [x] live bounded rerun으로 actual corpus 로딩이 `fuzz/corpus/coverage`로 바뀐 것 확인
- [x] 보고서 `fuzz-artifacts/modes/coverage/20260416_221832_coverage/FUZZING_REPORT.md` 확인
- [x] `current-status.md` 업데이트
- [x] `progress-index.md` 업데이트
- [x] note/checklist 기록 남김

## Follow-up
- [ ] coverage corpus 기준 bounded rerun 전후 novelty / duplicate recurrence / coverage delta 비교 기록
- [ ] active coverage corpus의 toxic seed 식별 및 quarantine 규칙화
- [ ] remote/proxmox 실행 contract에도 같은 env-override friendly corpus wiring 반영
