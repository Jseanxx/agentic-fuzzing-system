# Proxmox Re-run Execution Plan

> Goal: Proxmox `js` 계정에서 OpenHTJ2K를 다시 돌릴 때, 의미 있는 memory-safety finding 품질을 높이는 순서로 실행한다.

Date: 2026-04-15
Remote host: `proxmox-js`
Remote repo: `/home/js/work/fuzzing-jpeg2000`
User: `js`

---

## Current remote reality

이미 확인된 것:
- remote build works
- smoke reproduces known UBSan at `block_decoding.cpp:86`
- coverage run found distinct ASan crashes at:
  - `coding_units.cpp:3076`
  - `j2kmarkers.cpp:52`

즉 지금 단계에서 필요한 것은 “무작정 더 오래 돌리기”가 아니라:
- toxic seed quarantine
- harness role separation
- seed quality upgrade
- bounded comparative runs

이다.

---

## Execution strategy

### Phase 1 — stabilize remote state
Checklist:
- [ ] remote repo working tree 상태 확인
- [ ] local latest scripts/harness/tests synced 확인
- [ ] remote `build-fuzz-libfuzzer` 재빌드
- [ ] smoke known issue 재현 확인
- [ ] latest crash artifacts triage bucket에 존재 확인

Commands:
- `ssh proxmox-js 'cd /home/js/work/fuzzing-jpeg2000 && git status --short'`
- `ssh proxmox-js 'cd /home/js/work/fuzzing-jpeg2000 && bash scripts/build-libfuzzer.sh'`
- `ssh proxmox-js 'cd /home/js/work/fuzzing-jpeg2000 && bash scripts/run-smoke.sh /home/js/work/fuzzing-jpeg2000/build-fuzz-libfuzzer'`

Success criteria:
- build 성공
- smoke known issue 재현
- artifact/log 경로 정상

---

### Phase 2 — clean coverage corpus before rerun
Checklist:
- [ ] 즉사 toxic seed 격리
- [ ] known-bad는 coverage에서 제거
- [ ] crash artifact는 triage/known-bad에만 유지
- [ ] coverage corpus file count와 역할 검토

Success criteria:
- coverage bucket이 “즉사 재현 모음집”이 되지 않음
- 최소 3~6개 정도의 clean-ish seed 유지

---

### Phase 3 — short bounded comparative runs
목표는 밤새 무한 실행이 아니라, 하네스/seed 품질 비교다.

#### Run A — current decode harness / coverage
- mode: `coverage`
- duration: 짧게 5~10분
- purpose: 현재 기준점 확보

Suggested environment:
- `MAX_TOTAL_TIME=600`
- `NO_PROGRESS_SECONDS=180`
- `PROGRESS_INTERVAL_SECONDS=60`

#### Run B — parser-focused corpus or parser-focused harness
- purpose: parser-side crash 증가 여부 확인
- compare against Run A

#### Run C — cleanup-focused corpus or cleanup-focused harness
- purpose: partial failure / cleanup 계열 finding 증가 여부 확인

Evaluation metrics:
- [ ] distinct crash count
- [ ] duplicate ratio
- [ ] crash 위치 다양성
- [ ] parser-side vs lifecycle-side 분포
- [ ] time-to-first-distinct-crash

---

## Recommended first rerun order

1. rebuild
2. smoke
3. coverage with cleaned corpus
4. triage reproduce top 2 recent crashes
5. parser-focused short run
6. cleanup-focused short run
7. compare and keep the highest-signal setup for longer runs

---

## Concrete commands (current setup)

### Rebuild
```bash
ssh proxmox-js 'cd /home/js/work/fuzzing-jpeg2000 && bash scripts/build-libfuzzer.sh'
```

### Smoke
```bash
ssh proxmox-js 'cd /home/js/work/fuzzing-jpeg2000 && bash scripts/run-smoke.sh /home/js/work/fuzzing-jpeg2000/build-fuzz-libfuzzer'
```

### Short coverage rerun
```bash
ssh proxmox-js 'cd /home/js/work/fuzzing-jpeg2000 && MAX_TOTAL_TIME=600 NO_PROGRESS_SECONDS=180 PROGRESS_INTERVAL_SECONDS=60 bash scripts/run-fuzz-mode.sh coverage'
```

### Triage reproduce crash artifact
```bash
ssh proxmox-js 'cd /home/js/work/fuzzing-jpeg2000 && \
ASAN_OPTIONS=abort_on_error=1:detect_leaks=1:strict_string_checks=1:check_initialization_order=1:symbolize=1 \
UBSAN_OPTIONS=print_stacktrace=1:halt_on_error=1 \
/home/js/work/fuzzing-jpeg2000/build-fuzz-libfuzzer/bin/open_htj2k_decode_memory_harness <artifact_path>'
```

---

## Decision rules after rerun

### Keep current decode harness as primary if
- [ ] distinct crash가 계속 parser/lifecycle 양쪽에서 나옴
- [ ] duplicate fixation이 너무 심하지 않음
- [ ] time-to-first-distinct-finding이 짧음

### Promote parser harness if
- [ ] marker parser 계열 crash가 반복적으로 distinct하게 나옴
- [ ] decode harness보다 parser-side findings 분리 효율이 높음

### Promote cleanup harness if
- [ ] UAF/invalid free/stale pointer 계열 signal이 증가함
- [ ] partial failure path가 실제로 sanitizer finding으로 이어짐

---

## Logging and triage policy for reruns

Each distinct finding should record:
- time
- host
- run dir
- crash type
- file:line
- function
- artifact name
- SHA1
- triage level (P1/P2/P3)
- repro status

P1 criteria:
- distinct ASan crash
- heap-buffer-overflow / invalid write / SEGV write / UAF-like behavior

P2 criteria:
- known issue reproduction
- duplicate crash
- toxic seed quarantine info

P3 criteria:
- build success / environment info / sync info

---

## Bottom line

The next Proxmox rerun should not be “just rerun coverage forever”.
It should be:

1. stabilize
2. quarantine
3. compare
4. keep the highest-signal harness/corpus combination
5. only then extend run time
