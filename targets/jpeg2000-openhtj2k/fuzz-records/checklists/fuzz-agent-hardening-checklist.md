# Fuzz Agent Hardening Checklist

## Phase 1 — WSL workflow validation
- [x] build-failed 기록 확인
- [x] smoke-failed 기록 확인
- [x] crash artifact 생성 확인
- [x] current_status.json 갱신 확인
- [x] coverage/ft/corpus 메트릭 기록 확인
- [x] triage / coverage corpus 분리 시작
- [ ] regression corpus 확정
- [x] 동일 crash fingerprint 중복 판정 규칙 추가
- [ ] artifact 분류 규칙(crash/leak/timeout) 추가

## Phase 2 — Policy engine
- [ ] 로그 타입 분류기 정의
- [ ] 로그 타입별 다음 액션 규칙 정의
- [ ] same-seed known-bad 자동 격리 규칙
- [ ] no-progress 시 seed/harness 재검토 규칙
- [ ] leak-only 모드에서 coverage run 계속 여부 규칙
- [ ] 수정 후 regression run 강제 규칙

## Phase 3 — Self-improving loop
- [ ] 에이전트가 수정 전 baseline 요약 저장
- [ ] 하네스/시드 수정 이유를 md에 기록
- [ ] 수정 후 triage + coverage + regression 3종 재검증
- [ ] 실패 반복 횟수 제한 규칙
- [ ] 3회 이상 실패 시 전략 재설계 플래그

## Phase 4 — Remote target readiness
- [ ] WSL에서 운영 루프 안정화
- [ ] SSH 대상에서 동일 구조 재현 가능하게 스크립트화
- [ ] Proxmox 호스트/VM 접속 절차 문서화
- [ ] 원격 run artifact 동기화 정책
- [ ] Discord/원격 보고 경로 정리

## Phase 5 — GitHub publish readiness
- [ ] repo용 README 초안
- [ ] 정책 프롬프트 공개 버전 작성
- [ ] 로컬/개인정보/비밀정보 분리
- [ ] 재현 가능한 최소 데모 커맨드 정리
- [ ] 한계/위험/비자동 영역도 솔직하게 문서화
