# 2026-04-16 — hermes_watch LLM evidence packet v0.1 checklist

- [x] 사용자 목표를 LLM-first loop 기준으로 다시 점검
- [x] 기존 코드베이스 전체 감사 수행
- [x] Discord 전용 채널 `jpeg2000-code-audit` 생성 후 감사/구조 설명 게시
- [x] failing test 먼저 추가
  - [x] `test_build_llm_evidence_packet_extracts_failure_reasons_from_latest_artifacts`
  - [x] `test_main_write_llm_evidence_packet_emits_artifacts`
- [x] RED 확인
  - [x] `AttributeError: module 'hermes_watch' has no attribute 'build_llm_evidence_packet'`
  - [x] `unrecognized arguments: --write-llm-evidence-packet`
- [x] `scripts/hermes_watch_support/llm_evidence.py` 추가
- [x] `scripts/hermes_watch.py`에 wrapper + CLI flag 연결
- [x] latest run/probe/apply artifact 수집 구현
- [x] failure reason extraction v0.1 구현
- [x] `llm_objective` 선택 로직 구현
- [x] `fuzz-records/llm-evidence/*.json|md` writer 구현
- [x] GREEN 확인
  - [x] `python -m pytest tests/test_hermes_watch.py::HermesWatchLLMEvidencePacketTests -q` → 2 passed
- [x] syntax 검증
  - [x] `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/llm_evidence.py tests/test_hermes_watch.py` → OK
- [x] targeted/full regression 검증
  - [x] `python -m pytest tests/test_hermes_watch.py -q` → 238 passed
  - [x] `python -m pytest tests -q` → 257 passed
- [x] `current-status.md`, `progress-index.md` 갱신
- [x] note/checklist 기록 남김

## 냉정한 판정
- [x] 이번 slice는 목적 적합하다
- [x] 하지만 아직 failure reason extraction은 얕다
- [x] 다음은 handoff simplification 전에 extraction v0.2가 자연스럽다
