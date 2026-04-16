# Today First Real Loop Start Checklist

- Updated: 2026-04-16 18:00:29 KST
- Project: `fuzzing-jpeg2000`
- Purpose: **오늘 첫 1회 실사용 루프를 실제로 시작할 때 그대로 따라갈 수 있는 실행 순서**

---

## 0. 오늘 시작 전 냉정한 상태
현재 상태에서 바로 보이는 점:
- `fuzz-artifacts/current_status.json`은 존재한다
- `fuzz-records/llm-evidence/fuzzing-jpeg2000-llm-evidence.json`도 존재한다
- 하지만 현재 evidence packet의 `run_history`는 비어 있다
- 따라서 **지금 packet은 완전히 fresh하다고 보기 어렵다**

즉 오늘 첫 루프의 진짜 시작점은:
**fresh current status + fresh run history + fresh evidence packet을 다시 만드는 것**이다.

---

## 1. Step 1 — 기준선 확인
아무것도 믿기 전에 테스트 기준선부터 본다.

```bash
cd /home/hermes/work/fuzzing-jpeg2000
python -m pytest tests -q
```

판정:
- 실패하면 루프 시작 금지
- 통과하면 다음 단계로 이동

---

## 2. Step 2 — fresh run 1회 생성
오늘 첫 루프에서는 오래 끌지 말고 작은 slice로 다시 run을 만든다.

```bash
cd /home/hermes/work/fuzzing-jpeg2000
python scripts/hermes_watch.py \
  --max-total-time 300 \
  --no-progress-seconds 120 \
  --progress-interval-seconds 60
```

의도:
- fresh `fuzz-artifacts/current_status.json` 생성
- fresh run dir / logs 생성
- fresh `fuzz-artifacts/automation/run_history.json` 생성 또는 갱신

판정:
- build-failed / smoke-failed / fuzz-complete 뭐가 나오든 괜찮다
- 중요한 건 **오늘 기준 fresh artifact를 다시 만드는 것**이다

---

## 3. Step 3 — evidence packet 재생성
fresh run 뒤 packet을 다시 뽑는다.

```bash
cd /home/hermes/work/fuzzing-jpeg2000
python scripts/hermes_watch.py --write-llm-evidence-packet
```

확인 대상:
- `fuzz-records/llm-evidence/fuzzing-jpeg2000-llm-evidence.json`
- `fuzz-records/llm-evidence/fuzzing-jpeg2000-llm-evidence.md`

판정:
- 여기서 `run_history`가 여전히 비어 있으면
  - 오늘의 primary bottleneck은 `observability/freshness`
  - packet/harness/apply 평가로 넘어가지 말 것

---

## 4. Step 4 — packet에서 4개만 읽기
오늘 첫 루프에서는 많이 보지 말고 4개만 본다.

읽을 것:
- `failure_reason_codes`
- `top_failure_reason_narrative`
- `finding_efficiency_summary`
- `suggested_action_code` / `suggested_candidate_route`

판정 질문:
- 이 reason이 지금 상태를 진짜 설명하는가
- suggested action은 말이 되는가
- 그런데도 이건 **가설**일 뿐인가

원칙:
- suggested action을 바로 믿지 말고
- **이번 1회에서 검증할 action hypothesis**로만 취급한다

---

## 5. Step 5 — 오늘 action class 하나만 고르기
오늘 첫 루프는 하나만 고른다.

선택 후보:
- `shift_weight_to_deeper_harness`
- `halt_and_review_harness`
- `minimize_and_reseed`
- bounded apply rail

현재 상태가 smoke-failed + smoke-log memory-safety signal 쪽이면,
오늘 기본 추천은:
- **1순위: `halt_and_review_harness`**
- 이유:
  - 아직 run history freshness가 불안했고
  - smoke 단계에서 이미 UBSan류 신호가 보이며
  - 이 상태에서 바로 bounded apply를 밀기보다
  - **현재 실패 shape를 review-first로 확인하는 게 더 보수적**이기 때문

금지:
- review + apply 같이 하지 말 것
- deeper-stage + reseed 같이 하지 말 것

---

## 6. Step 6 — chosen action 1회만 수행
오늘 첫 루프에서 review-first를 선택하면:

```bash
cd /home/hermes/work/fuzzing-jpeg2000
python scripts/hermes_watch.py --route-harness-probe-feedback
```

그리고 refiner work가 실제로 준비돼 있다면 이어서:

```bash
cd /home/hermes/work/fuzzing-jpeg2000
python scripts/hermes_watch.py --prepare-refiner-orchestration
python scripts/hermes_watch.py --dispatch-refiner-orchestration
python scripts/hermes_watch.py --bridge-refiner-dispatch
```

주의:
- 오늘 첫 루프는 여기까지로도 충분하다
- launch/verify/apply까지 한 번에 다 밀지 않는다
- 오늘 목적은 **실효성 병목 확인**이지 풀오토 연쇄 실행이 아니다

만약 packet이 아주 강하게 bounded apply를 가리키고,
operator 판단상 정말 그게 맞아도:
- 첫 루프에서는 review-first를 기본으로 둔다
- apply-first는 두 번째 루프부터 검토한다

---

## 7. Step 7 — rerun 비교 또는 no-go 판정
오늘 첫 루프의 Go / No-Go 질문은 이것뿐이다.

Go 신호:
- fresh run + fresh packet이 정상 생성됨
- top reason이 이전보다 명확해짐
- chosen action이 실제로 follow-up artifact를 남김
- 다음 루프에서 무엇을 해야 할지 더 선명해짐

No-Go 신호:
- run_history가 여전히 비어 있음
- packet이 여전히 stale하게 보임
- suggested action이 너무 엉뚱함
- follow-up action을 1개 골랐는데도 실제 artifact가 안 이어짐

판정:
- Go면 다음 루프에서 chosen route를 한 번 더 밀 수 있음
- No-Go면 오늘 병목을 `observability/freshness` 또는 `packet`으로 기록하고 종료

---

## 8. 오늘 기록해야 할 최소 메모
오늘 1회 끝나면 아래만 적는다.

- freshness 복구 성공 여부:
- top reason:
- suggested action / route:
- 오늘 실제로 고른 action:
- go / no-go:
- primary bottleneck:
  - `observability/freshness`
  - `packet`
  - `llm-output-discipline`
  - `harness-target`
  - `apply-rail`

---

## 9. 오늘의 최종 운영 문장
**오늘 첫 루프의 목표는 수정 많이 하기 아니다. fresh 상태를 다시 만들고, suggested route를 가설로 검증할 수 있는 최소 1회 실행을 남기는 것이다.**
