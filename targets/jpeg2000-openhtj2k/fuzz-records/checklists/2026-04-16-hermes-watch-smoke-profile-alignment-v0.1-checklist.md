# Hermes Watch Smoke/Profile Alignment v0.1 Checklist

- Updated: 2026-04-16 18:26:43 KST
- Project: `fuzzing-jpeg2000`

---

## 목표
- [x] active target profile과 watcher smoke 계약의 어긋남을 줄인다
- [x] 기본 smoke baseline에서 known-bad regression seed를 뺀다
- [x] deep-decode-v3 harness/fuzzer 경로로 실제 loop가 진입하는지 확인한다

## 변경
- [x] `scripts/run-smoke.sh`
  - [x] direct harness path 허용
  - [x] 기본 smoke seed를 stable-valid 2개로 축소
  - [x] `p0_12.j2k` 제거
- [x] `fuzz-records/profiles/openhtj2k-target-profile-v1.yaml`
  - [x] `target.adapter` 추가
  - [x] deep-decode-v3 smoke harness 경로 지정
  - [x] deep-decode-v3 fuzzer 계약 반영 시작
- [x] `tests/test_aflpp_setup.py`
  - [x] smoke script 기본 seed 계약 회귀 테스트 추가
  - [x] direct harness path 지원 회귀 테스트 추가
  - [x] profile adapter contract 회귀 테스트 추가

## RED/GREEN
- [x] `python -m pytest tests/test_aflpp_setup.py -q` RED 확인
  - [x] 3 failed
- [x] 최소 수정 적용
- [x] `python -m pytest tests/test_aflpp_setup.py -q` GREEN 확인
  - [x] 7 passed

## 추가 검증
- [x] `python -m pytest tests/test_hermes_watch.py::HermesWatchTargetAdapterTests -q`
  - [x] 11 passed
- [x] `python scripts/hermes_watch.py --max-total-time 30 --no-progress-seconds 20 --progress-interval-seconds 0`
  - [x] smoke-failed 반복 대신 deep-decode-v3 fuzzer 경로 진입 확인
- [x] `python scripts/hermes_watch.py --write-llm-evidence-packet`
  - [x] fresh crash evidence packet 재생성

## 현재 냉정한 상태
- [x] smoke/profile contract mismatch는 줄었다
- [x] loop가 deep-decode-v3 crash evidence를 다시 생산하기 시작했다
- [ ] remote/proxmox orchestration 완성 아님
- [ ] fully autonomous LLM repair loop 완성 아님
