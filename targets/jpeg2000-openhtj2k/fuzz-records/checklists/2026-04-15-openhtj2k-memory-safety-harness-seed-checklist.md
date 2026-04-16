# OpenHTJ2K memory-safety finding 중심 하네스/시드 개선 체크리스트

Date: 2026-04-15
Target: OpenHTJ2K / JPEG2000
Goal: 방어 가치가 높은 memory-safety finding(UAF, invalid write, heap-buffer-overflow, double free, severe OOB)을 더 잘 드러내는 하네스/시드 운영 기준 정리

---

## 핵심 원칙

이 체크리스트의 목적은 다음과 같다.

- exploitability를 직접 추구하지 않는다.
- 대신 **방어 가치가 높은 distinct memory-safety bug**를 더 안정적으로 드러내는 방향으로 하네스와 시드를 개선한다.
- 단순 crash 수보다 **의미 있는 crash 품질**을 우선한다.

우선순위는 아래 순서로 본다.

1. use-after-free / double free / invalid free
2. heap-buffer-overflow / out-of-bounds write / invalid write
3. parser-side heap OOB / marker handling faults
4. allocator/cleanup/lifetime 관련 crash
5. overflow/underflow 같은 arithmetic bug (단독보다 memory corruption 전조 여부를 같이 봄)

---

## Phase 1 — 현재 하네스 품질 점검

현재 주 하네스:
- `fuzz/decode_memory_harness.cpp`

### 체크포인트
- [ ] 입력 1회마다 fresh decoder/context를 새로 생성하는가
- [ ] `parse()`뿐 아니라 실제 `invoke()` 또는 decode path까지 진입하는가
- [ ] 성공 경로에서 output plane 해제가 누락되지 않는가
- [ ] 예외/실패 경로에서도 해제가 누락되지 않는가
- [ ] 하네스 내부에 입력 간 공유되는 전역/정적 상태가 없는가
- [ ] 하네스가 sanitizer report를 삼키지 않고 그대로 드러내는가
- [ ] `LLVMFuzzerTestOneInput`가 side effect를 남기지 않는가

### 목표
- 단순 parser reject 하네스가 아니라
- **decode lifecycle + allocation/free path**를 실제로 타는 하네스를 유지한다.

---

## Phase 2 — memory-safety finding에 유리한 하네스 조건

### 좋은 하네스 특성
- [ ] 메모리 버퍼 입력 기반이다
- [ ] 포맷 파싱 이후 실제 객체 생성/참조/해제까지 간다
- [ ] 타일/코드블록/마커 처리처럼 구조가 깊은 경로를 탄다
- [ ] 실패 입력에서도 cleanup path를 많이 타게 만든다
- [ ] 출력 버퍼 할당과 해제 타이밍이 분명하다

### 피해야 할 하네스 특성
- [ ] 너무 이른 reject만 반복해서 깊은 경로에 못 들어감
- [ ] 단순 header validation만 하고 종료함
- [ ] 정상 종료 path만 많이 타고 exceptional cleanup path를 거의 안 탐
- [ ] 파일 I/O에 의존해 재현성과 throughput이 떨어짐

---

## Phase 3 — 보조 하네스 추가 후보

현재 decode-memory 하네스는 유지하되, 아래 보조 하네스를 검토한다.

### A. parser/marker 집중 하네스
목표:
- `j2kmarkers.cpp` 계열 marker parsing / length handling / short codestream / malformed marker 경로 강화

체크포인트:
- [ ] parse-only 또는 parse-light 하네스를 별도 구성할지 검토
- [ ] marker sequence, segment length, truncation 경로를 많이 타는지 확인
- [ ] 너무 shallow하지 않게 최소한의 downstream object interaction을 유지할지 결정

### B. tile-part / packet / codestream lifecycle 하네스
목표:
- `coding_units.cpp` 계열 tile-part / packet / allocation / cleanup 경로 강화

체크포인트:
- [ ] 현재 `invoke()` 기반 하네스로 충분히 타는지 측정
- [ ] 필요하면 tile-part handling 전용 경로를 더 직접 타는 보조 하네스 검토

### C. exceptional cleanup 하네스
목표:
- partially valid input 후반부에서 실패하도록 유도해 cleanup / free / rollback 경로를 두드림

체크포인트:
- [ ] near-valid truncated sample 위주 시드로 depth 확보
- [ ] decode 중간 실패 시 메모리 해제/상태 전이 문제를 더 잘 드러내는지 확인

---

## Phase 4 — 시드 전략 (중요)

### 목표
coverage를 무한히 늘리는 것보다,
**깊은 경로에 들어가면서도 매번 동일 crash로 즉사하지 않는 corpus**를 만든다.

### 시드 버킷 규칙
- [ ] `coverage/` : 깊이 들어가는 clean-ish seed
- [ ] `triage/` : distinct crash 재현용 seed/artifact
- [ ] `regression/` : 고정적으로 다시 확인해야 하는 failing seed
- [ ] `known-bad/` : coverage를 오염시키는 toxic seed

### 좋은 coverage seed 조건
- [ ] decoder가 어느 정도 parse를 통과한다
- [ ] tile / marker / packet 경로에 실제로 들어간다
- [ ] 즉시 같은 known crash로만 끝나지 않는다
- [ ] 입력 구조가 서로 너무 비슷하지 않다

### 좋은 regression seed 조건
- [ ] known smoke failure를 재현한다
- [ ] 최근 distinct crash artifact를 재현한다
- [ ] 수정 후 반드시 다시 확인할 가치가 있다

### toxic seed 격리 기준
- [ ] 너무 빠르게 동일 crash만 유도한다
- [ ] coverage growth를 거의 막는다
- [ ] distinct finding 없이 한 경로만 계속 고정시킨다

---

## Phase 5 — 시드 구성 방향

### 반드시 포함할 seed 유형
- [ ] 정상 decodable baseline seed
- [ ] 작은 입력 / 짧은 codestream
- [ ] marker layout이 다른 seed
- [ ] tile 구조가 다른 seed
- [ ] near-valid but truncated seed
- [ ] known-bad reproducer

### 특히 OpenHTJ2K에서 중요한 seed 관점
- [ ] marker sequence variation
- [ ] segment length variation
- [ ] tile-part layout variation
- [ ] codestream truncation 지점 variation
- [ ] header는 맞지만 body가 깨지는 변형
- [ ] body는 길지만 내부 marker 경계가 깨지는 변형

---

## Phase 6 — sanitizer / debug 옵션 기준

### 기본 원칙
초기 단계에서는 속도보다 관측성을 우선한다.

### triage / regression 권장
- [ ] ASan on
- [ ] UBSan on
- [ ] `abort_on_error=1`
- [ ] `halt_on_error=1`
- [ ] `symbolize=1`
- [ ] leak detection on

### coverage 권장
- [ ] ASan on
- [ ] UBSan on
- [ ] `abort_on_error=1`
- [ ] `halt_on_error=1`
- [ ] leak detection은 상황에 따라 완화 가능
- [ ] 단, write/OOB/UAF류 관측성은 절대 낮추지 않음

### 점검 포인트
- [ ] stack trace가 충분히 symbolized 되는가
- [ ] sanitizer output이 watcher/report에 구조적으로 남는가
- [ ] crash artifact가 보존되는가

---

## Phase 7 — distinct finding 품질 판정

새 crash를 봤을 때 아래 기준으로 먼저 평가한다.

### P1로 볼 조건
- [ ] distinct ASan crash
- [ ] heap-buffer-overflow / invalid write / SEGV write 성격
- [ ] UAF / double free / invalid free 정황
- [ ] parser 또는 lifecycle 핵심 경로에서 발생
- [ ] harness로 재현 가능

### P2로 볼 조건
- [ ] 기존 crash와 사실상 동일 위치/동일 성격
- [ ] duplicate이지만 회귀검증 가치가 있음
- [ ] toxic seed 분리 필요성을 알려주는 crash

### P3로 볼 조건
- [ ] 단순 환경 문제
- [ ] logging-only 정보
- [ ] 의미 없는 reject/noise에 가까움

---

## Phase 8 — OpenHTJ2K 기준 현재 우선 목표

현재까지 관측된 중요한 방향:
- `block_decoding.cpp:86` UBSan smoke issue
- `coding_units.cpp:3076` ASan SEGV in tile-part handling
- `j2kmarkers.cpp:52` ASan heap-buffer-overflow in marker parsing

### 그래서 현재 우선순위는
- [ ] marker parsing 경로 강화
- [ ] tile-part / lifecycle 경로 강화
- [ ] toxic coverage seed 지속 격리
- [ ] distinct crash artifact를 regression/triage에 명시적으로 편입

---

## Phase 9 — 실무 운영 체크리스트

### 바로 실행 가능한 항목
- [ ] 현재 coverage corpus에서 즉사 toxic seed 다시 점검
- [ ] 최근 distinct crash artifact를 triage/regression에 반영
- [ ] parser-focused 보조 하네스 추가 여부 판단
- [ ] tile-part focused 보조 하네스 추가 여부 판단
- [ ] crash channel에 P1/P2/P3 기준으로 finding 정리
- [ ] 수정 후 smoke + triage + regression + coverage 재확인

---

## 결론

OpenHTJ2K에서는 지금 방향이 맞다.

핵심은:
- 하네스를 억지로 복잡하게 만드는 것이 아니라
- **실제 allocation / parse / decode / cleanup 경로를 잘 타는 하네스**를 유지하고,
- **coverage를 오염시키는 toxic seed를 분리**하고,
- **distinct memory-safety crash를 빠르게 triage 가능한 구조**로 운영하는 것이다.

이 체크리스트는 그 목적에 맞춘 운영 기준이다.
