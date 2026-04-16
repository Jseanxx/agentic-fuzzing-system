# Hermes Watch Loader Hardening Checklist

**Goal:** malformed registry / crash-index payload이 watcher를 죽이지 않도록 safe loader를 도입한다.

**Scope:** 이번 단계는 low-risk loader hardening만 한다.
- malformed JSON fallback
- wrong top-level type fallback
- crash index fingerprints wrong-type repair
- error note metadata 기록

---

## 냉정한 사전 평가

### 현재 상태
- `load_registry()` / `load_crash_index()`는 direct `json.loads()`를 사용한다.
- malformed file 하나로 watcher가 바로 죽을 수 있다.
- 실제 운영에서는 partial write / manual edit / truncation이 충분히 발생할 수 있다.

### 이번 단계에서 실제로 붙일 것
- safe registry loader
- safe crash index loader
- wrong-type fingerprint store repair
- fallback result에 error note metadata 포함

### 이번 단계에서 일부러 안 할 것
- file quarantine/rename
- file lock 도입
- YAML loader hardening
- notification failure isolation

### 설계 원칙
- watcher를 살리는 쪽이 우선이다.
- malformed payload는 default structure로 fallback한다.
- silent ignore 대신 `__load_error__`를 남긴다.

---

## 작업 체크리스트

### Phase 1 — 구조 설계
- [x] registry fallback shape 정의
- [x] crash index fallback shape 정의
- [x] wrong-type fingerprints repair 규칙 정의

### Phase 2 — 테스트 먼저 작성
- [x] malformed registry JSON 테스트
- [x] wrong top-level type registry 테스트
- [x] malformed crash index JSON 테스트
- [x] wrong-type fingerprint store repair 테스트
- [x] 먼저 테스트를 돌려 failure 확인

### Phase 3 — 구현
- [x] `load_registry()` hardening
- [x] `load_crash_index()` hardening
- [x] fallback error note (`__load_error__`) 추가

### Phase 4 — 검증
- [x] fingerprint test block 재실행
- [x] 전체 watcher 테스트 실행
- [x] 회귀 확인

### Phase 5 — 냉정한 사후 평가
- [x] malformed registry crash risk가 줄었는지 명시
- [x] 다음 단계 file lock / YAML hardening / notification isolation 필요성 기록

---

## 성공 기준
- malformed JSON이 watcher를 죽이지 않는다.
- wrong-type top-level payload가 safe default로 fallback한다.
- crash index의 invalid fingerprints store가 복구된다.
- full test suite가 유지된다.

## 실패 기준
- fallback이 너무 조용해서 corruption을 숨긴다.
- default structure가 downstream 코드와 맞지 않는다.
- 기존 정상 흐름을 깨뜨린다.

## 한 줄 냉정 평가 기준
**이번 단계가 끝나면 malformed registry / crash-index payload 하나가 watcher 전체를 즉시 죽이는 리스크는 줄어든다.**
