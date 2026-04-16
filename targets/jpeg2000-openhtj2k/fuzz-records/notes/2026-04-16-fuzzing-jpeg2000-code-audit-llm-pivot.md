# fuzzing-jpeg2000 코드 감사 + LLM-first pivot 점검

- 작성 시각: 2026-04-16 09:47:00 KST
- 범위: `scripts/hermes_watch.py`, `scripts/hermes_watch_support/*.py`, `tests/test_hermes_watch.py`, `scripts/*`, `fuzz/*`, `fuzz-records/*`
- 기준: 사용자 목표는 **LLM-first 자가발전형 퍼징 루프**이며, control-plane 자체가 목적이 아니다.

## 검증 상태
- `python -m pytest tests/test_hermes_watch.py -q` → 236 passed
- `python -m pytest tests -q` → 255 passed
- `git status --short` 기준 현재 작업트리는 매우 dirty 상태이며, 기능 확장 흔적이 큼

## 냉정한 총평
현재 시스템은 **망가진 상태는 아니고 테스트도 통과한다.**
하지만 목적 대비 구조가 과도하게 앞서간 부분이 분명하다.

한 줄로 말하면:
**지금 코드는 "LLM이 더 잘 고치게 만드는 증거 루프"보다 "artifact/control-plane/state-machine"에 더 많은 복잡도를 투자한 상태다.**

## 우선 위험/개선 포인트

### P0. `scripts/hermes_watch.py` 단일 파일 과대화
- 파일 크기: 5516 lines
- 함수 수: 외부 감사 기준 약 157개
- 문제:
  - build/smoke/fuzz core runner
  - policy/classification
  - refiner orchestration
  - delegate/apply/recovery/reingestion/ecosystem recursion
  이 한 파일에 과도하게 응집되어 있다.
- 영향:
  - 디버깅 난이도 증가
  - 실제 에러 원인 추적 비용 증가
  - LLM-first loop 개선 작업이 watcher monolith에 묻힘

### P0. evidence보다 artifact state-machine이 앞서감
- recovery / bridge / routing / recursive chaining / downstream reingestion이 많이 붙어 있음
- 반면 LLM에게 넘길 표준 evidence packet / failure reason extraction은 아직 약함
- 영향:
  - 자동화 구조는 많지만, LLM 수정 품질을 직접 높이는 정보 공급이 부족함

### P1. `latest manifest wins` 패턴 다수
지원 모듈 여러 곳이 최신 파일(mtime) 기준으로 상태를 고른다.
예:
- `harness_feedback.py`
- `harness_routing.py`
- `harness_candidates.py`
- `harness_skeleton.py`
- 영향:
  - 병렬 실행, 재시도, 중간 rerun 시 잘못된 최신 artifact를 집을 위험
  - self-improving loop에서 lineage 혼선 가능성 큼

### P1. candidate feedback 적용 idempotency 약함
- `harness_candidates.py`에서 latest feedback를 반복 적용할 수 있는 구조
- 점수/부채/pass-fail streak가 중복 반영될 여지가 있음
- 영향:
  - candidate ranking drift
  - evidence-aware scheduler의 신뢰도 저하

### P1. queue entry update가 unique key보다 action_code 중심
- 같은 action이 여러 entry에 존재할 때 잘못된 항목이 갱신될 위험
- 영향:
  - orchestration/recovery queue 정합성 저하

### P2. multi-target 확장성은 아직 절반짜리
- adapter seam은 많이 퍼졌지만 기본 fallback이 사실상 OpenHTJ2K 중심
- profile 기반 adapter가 없으면 대부분 기존 target-shaped default로 귀결
- 영향:
  - reusable substrate라고 부르기엔 아직 이르며, 현재는 "OpenHTJ2K를 일반화하려는 중간 상태"에 가깝다

### P2. 저가치 wrapper / helper 중복
- `_load_json`, `_load_registry`, `_slugify` 류가 여러 모듈에 분산
- 일부 wrapper는 runtime 단순화보다 테스트 주입 편의를 위해 존재하는 인상이 강함
- 영향:
  - drift risk 증가
  - 스키마 repair/fallback 동작이 미묘하게 달라질 수 있음

## 내 목적 기준에서 무엇이 쓰레기인가?
완전히 버려야 할 dead code가 대량으로 보이진 않았다.
하지만 **목적 대비 저효율 코드**는 있다.

가장 대표적인 건:
- recovery ecosystem recursion 추가 고도화
- skeleton TODO/comment/lifetime hint 세밀 일반화
- artifact/plan 문서 생성이 실제 evidence consumption보다 앞서는 부분

즉 "쓰레기"라기보다,
**지금 목표에 비해 너무 이른 일반화 / 너무 많은 orchestration 코드**가 문제다.

## 바로 필요한 리팩토링 방향

### 1. `hermes_watch.py` 역할 분리
최소 다음 축으로 분리하는 게 맞다.
- core fuzz run loop
- evidence extraction / failure summarization
- harness improvement driver
- optional recovery/orchestration extras

### 2. 명시적 lineage key 도입
- latest mtime 기반 선택 축소
- run_id / candidate_id / feedback_id / apply_id로 연결

### 3. feedback consumption idempotency 보강
- consumed feedback marker
- duplicate apply 방지

### 4. LLM evidence path를 1급 객체로 승격
추가해야 할 것:
- latest build/smoke/fuzz/probe/apply artifact 묶음
- no-crash / shallow-only / repeated-crash / build blocker / smoke invalidity / coverage plateau 요약
- LLM handoff JSON + markdown

## 전체 구조 요약 트리
```text
fuzzing-jpeg2000/
├── scripts/
│   ├── hermes_watch.py                # 메인 watcher + policy + refiner + apply/recovery monolith
│   ├── build-libfuzzer.sh             # libFuzzer 빌드
│   ├── run-smoke.sh                   # smoke 실행
│   ├── run-fuzzer.sh                  # libFuzzer 실행
│   ├── build-aflpp.sh                 # AFL++ 빌드
│   ├── run-aflpp-mode.sh              # AFL++ 모드별 실행
│   ├── run-fuzz-mode.sh               # triage/coverage/regression 상위 wrapper
│   └── hermes_watch_support/
│       ├── profile_loading.py         # target profile 로드
│       ├── profile_validation.py      # profile 검증
│       ├── profile_summary.py         # runtime summary 생성
│       ├── target_adapter.py          # command / policy / entrypoint adapter
│       ├── reconnaissance.py          # heuristic recon
│       ├── harness_draft.py           # harness candidate draft
│       ├── harness_evaluation.py      # candidate 평가 계획
│       ├── harness_probe.py           # short build/smoke probe
│       ├── harness_feedback.py        # probe -> feedback/queue
│       ├── harness_candidates.py      # ranked candidate registry
│       ├── harness_routing.py         # next candidate / route handoff
│       └── harness_skeleton.py        # skeleton/revision/closure/correction/apply
├── fuzz/
│   ├── decode_memory_harness.cpp
│   ├── parse_memory_harness.cpp
│   ├── cleanup_memory_harness.cpp
│   ├── deep_decode_lifecycle_harness.cpp
│   ├── deep_decode_focus_v3_harness.cpp
│   ├── corpus/                        # libFuzzer corpus buckets
│   └── corpus-afl/                    # AFL++ corpus buckets
├── fuzz-artifacts/
│   ├── current_status.json            # live operational state
│   ├── crash_index.json               # crash dedup index
│   ├── runs/                          # per-run logs/status/report
│   ├── modes/                         # triage/coverage/regression runs
│   └── automation/                    # policy/queue/trigger machine state
├── fuzz-records/
│   ├── profiles/                      # target profile YAML
│   ├── current-status.md              # 최신 상태 설명
│   ├── progress-index.md              # 단계별 실험 이력
│   ├── notes/                         # 해석/평가 기록
│   ├── checklists/                    # 검증 기록
│   └── ...                            # harness/recovery/refiner artifact 문서들
└── tests/
    ├── test_hermes_watch.py           # watcher 회귀 테스트 대형 파일
    ├── test_aflpp_setup.py
    ├── test_additional_harnesses.py
    ├── test_deep_decode_v2_harness.py
    └── test_deep_decode_v3_harness.py
```

## 트리 설명
- `scripts/hermes_watch.py`
  - 실제 실행의 중심이다.
  - 좋은 점: 한 곳에서 흐름을 다 볼 수 있다.
  - 나쁜 점: 너무 많은 책임이 뭉쳐 있다.
- `scripts/hermes_watch_support/`
  - 원래 monolith를 쪼개기 시작한 흔적이다.
  - profile / adapter / recon / draft / probe / feedback / candidates / routing / skeleton까지 나뉘어 있다.
  - 하지만 최종 orchestration은 아직 main watcher가 많이 쥐고 있다.
- `fuzz/`
  - 실제 퍼징 표면이다. parser/cleanup/deeper-decode harness가 분화돼 있다.
- `fuzz-artifacts/`
  - 기계 상태 저장소다. 자동화가 읽는 live state가 여기 있다.
- `fuzz-records/`
  - 사람/에이전트가 읽는 reasoning memory다. 장점은 풍부한 이력, 단점은 문서가 많아졌다는 점.
- `tests/`
  - 현재 구조를 강하게 고정하고 있다. 특히 `test_hermes_watch.py`가 크다.

## 목적 적합성 재판정
질문: **이제 우리가 `LLM evidence packet v0.1`부터 들어가면 되는가?**

대답: **맞다. 지금은 그게 최우선이 맞다.**

이유:
1. 최소 안전장치(build/smoke/apply/rollback/artifact)는 이미 있음
2. 지금 병목은 orchestration 부족이 아니라 evidence packaging 부족임
3. LLM이 실제로 더 잘 고치게 하려면, 다음은 구조 추가가 아니라 실패 근거 압축이 먼저임

## 다음 safe slice 제안
### `LLM evidence packet v0.1`
최소 범위:
- latest build/smoke/fuzz/probe/apply artifact 수집
- failure reason extraction v0.1
  - build blocker
  - smoke invalidity
  - no-crash / shallow-only
  - repeated crash family
  - coverage/corpus 정체
- LLM 전달용 JSON + markdown packet 생성
- 이후 correction/delegate path가 이 packet을 우선 참조하도록 seam 추가

## 최종 한 줄 평가
**코드가 완전히 망가졌거나 dead code 투성이인 건 아니지만, 최근에는 목표 대비 control-plane 과투자가 있었고, 지금부터는 `LLM evidence packet` 중심으로 우선순위를 바꾸는 게 맞다.**
