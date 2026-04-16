# 2026-04-16 — failure reason extraction v0.3 checklist

- [x] v0.3 범위 결정
  - [x] raw log/body-level signal
  - [x] direct script entrypoint 실행성
- [x] failing test 먼저 추가
  - [x] smoke log body signal이 packet reason으로 들어와야 함
  - [x] `python scripts/hermes_watch.py --write-llm-evidence-packet` direct 실행이 성공해야 함
- [x] RED 확인
  - [x] `smoke-log-memory-safety-signal` 미검출
  - [x] direct script entrypoint가 `ModuleNotFoundError: scripts`로 실패
- [x] `hermes_watch.py` import-path bootstrap 추가
- [x] `llm_evidence.py` raw log signal extraction 추가
- [x] `raw_signal_summary` packet 필드 추가
- [x] `smoke-log-memory-safety-signal` reason 추가
- [x] GREEN 확인
  - [x] `python -m pytest tests/test_hermes_watch.py::HermesWatchLLMEvidencePacketV03Tests -q` → 2 passed
- [x] syntax 검증
  - [x] `python -m py_compile scripts/hermes_watch.py scripts/hermes_watch_support/llm_evidence.py tests/test_hermes_watch.py` → OK
- [x] regression 검증
  - [x] `python -m pytest tests/test_hermes_watch.py -q` → 242 passed
  - [x] `python -m pytest tests -q` → 261 passed
- [x] 실제 direct entrypoint 실행 확인
  - [x] `python scripts/hermes_watch.py --repo /home/hermes/work/fuzzing-jpeg2000 --write-llm-evidence-packet` → 성공
- [x] status / progress / note / checklist 갱신

## 냉정한 판정
- [x] 실제 로그 본문 단서가 packet reason으로 들어오기 시작했다
- [x] 실행성 문제 하나를 같이 정리한 건 가치 있었다
- [x] 하지만 아직 build/fuzz/probe/apply body signal은 더 읽어야 한다
