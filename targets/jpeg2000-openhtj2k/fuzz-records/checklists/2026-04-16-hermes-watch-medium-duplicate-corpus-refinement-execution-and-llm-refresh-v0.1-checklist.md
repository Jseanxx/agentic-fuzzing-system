# Checklist — medium duplicate corpus refinement execution + LLM refresh v0.1

- [x] `coding_units.cpp:3076` medium duplicate family pending `minimize_and_reseed` entry 확인
- [x] refiner executor completion 후 LLM evidence packet refresh 부재를 test로 고정
- [x] RED 확인: refresh regression test fail
- [x] `execute_next_refiner_action(...)`에서 `refresh_llm_evidence_packet_best_effort(repo_root)` 호출 연결
- [x] result payload에 refreshed evidence artifact path 노출
- [x] targeted refiner/corpus/llm-evidence test pass 확인
- [x] full `pytest -q` pass 확인 (`331 passed`)
- [x] live `execute_next_refiner_action(...)`로 medium duplicate `minimize_and_reseed` entry 실제 consume
- [x] `triage/regression/known-bad` bucket copy 생성 확인
- [x] regression bucket retention replay exit/signature 확인
- [x] refreshed `openhtj2k-llm-evidence.json`에 latest duplicate review/corpus refinement context 반영 확인
- [x] `current-status.md` 업데이트
- [x] `progress-index.md` 업데이트
- [x] note/checklist 기록 남김

## Follow-up
- [ ] retained regression seed 기준 bounded rerun으로 novelty/coverage 효과 측정
- [ ] same family에 대한 bounded minimization artifact 추가
- [ ] remote/proxmox에서도 같은 preservation/replay/packet loop 재현
