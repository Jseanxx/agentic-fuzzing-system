# Self-Improving Fuzzing System Progress Index

- Updated: 2026-04-16 22:19:23 KST
- Purpose: **자가발전형 퍼징 시스템 개발을 버전처럼 추적하고, 각 단계의 가치/한계/피드백 근거를 남기기 위한 상위 진행표**

---

## 한 줄 결론
**지금까지의 기록은 단순 연대기가 아니라, “이 시스템이 어떤 버전의 사고를 거쳐 현재 구조로 왔는지”를 추적하기 위한 실험 이력이다.**

## 왜 이 문서가 필요한가
우리가 만드는 것은 단순 fuzz harness가 아니라,
장기적으로는:
- 타겟 분석
- 하네스 후보 생성
- probe / verification
- 퍼징 실행
- crash / coverage / stall feedback
- 다음 revision 제안
을 반복하는 **자가발전형 퍼징 시스템**이다.

하지만 이게 실제로 잘 될지는 아직 모른다.
그래서 각 단계를
## **git commit처럼 버전형으로 남기고, 나중에 무엇이 효과 있었는지 되돌아볼 수 있어야 한다.**

이 문서는 그 상위 인덱스다.

---

## 현재 상위 단계 맵

| 버전/단계 | 상태 | 핵심 의미 | 관련 문서 |
|---|---|---|---|
| Foundation v1 | 완료 | build/smoke/fuzz 기록, crash dedup, policy substrate 확보 | `current-status.md`, `notes/2026-04-14-crash-fingerprint-dedup-v1.md`, `notes/2026-04-14-policy-action-v1.md` |
| Refiner control-plane | 완료 | queue → orchestration → dispatch → bridge → launcher → verification 루프 확보 | `notes/2026-04-15-hermes-watch-system-audit.md`, `checklists/2026-04-15-hermes-watch-refiner-*.md` |
| Target profile / recon / candidate draft | 완료 | 타겟 분석과 harness candidate 추론의 기초 확보 | `notes/2026-04-15-hermes-watch-target-reconnaissance-draft-note.md`, `notes/2026-04-15-hermes-watch-harness-candidate-draft-note.md` |
| Harness evaluation / short probe / feedback bridge | 완료 | 후보를 짧게 검증하고 registry/refiner로 연결하는 단계 확보 | `notes/2026-04-15-hermes-watch-harness-evaluation-draft-note.md`, `notes/2026-04-15-hermes-watch-harness-short-probe-note.md`, `notes/2026-04-15-hermes-watch-harness-probe-feedback-bridge-note.md` |
| R18 evidence-aware registry weighting | 완료 | heuristic scheduler에서 evidence-aware scheduler로 진전 | `notes/2026-04-15-hermes-watch-measured-execution-quality-loop-note.md`, `checklists/2026-04-15-hermes-watch-measured-execution-quality-loop-checklist.md` |
| R19 skeleton generation + revision loop | 완료 | selected candidate 기준 skeleton draft와 shallow revision loop 확보 | `notes/2026-04-15-hermes-watch-harness-skeleton-generation-note.md`, `checklists/2026-04-15-hermes-watch-harness-skeleton-generation-checklist.md` |
| Pre-R20 runtime hardening | 완료 | timeout/env parsing 등 값싼 운영 취약점 1차 완화 | `notes/2026-04-15-hermes-watch-runtime-hardening-timeout-env-note.md`, `checklists/2026-04-15-hermes-watch-runtime-hardening-timeout-env-checklist.md` |
| R20 revision intelligence v0.1 | 완료 | skeleton layer가 latest build/smoke evidence를 읽고 next revision focus를 구조화 | `notes/2026-04-15-hermes-watch-r20-revision-intelligence-note.md`, `checklists/2026-04-15-hermes-watch-r20-revision-intelligence-checklist.md` |
| R20 actual closure v0.1 | 완료 | latest skeleton artifact를 실제 build/smoke closure와 연결하고 revision layer가 그 evidence를 우선 소비 | `notes/2026-04-15-hermes-watch-r20-actual-closure-note.md`, `checklists/2026-04-15-hermes-watch-r20-actual-closure-checklist.md` |
| R20 patch-level autonomous correction v0.1 | 완료 | failed closure를 보고 source-adjacent correction draft를 생성 | `notes/2026-04-15-hermes-watch-r20-patch-correction-note.md`, `checklists/2026-04-15-hermes-watch-r20-patch-correction-checklist.md` |
| R20 correction-consumption / apply policy v0.1 | 완료 | correction draft를 closure evidence와 대조해 승격/보류 policy artifact로 남김 | `notes/2026-04-15-hermes-watch-r20-correction-consumption-note.md`, `checklists/2026-04-15-hermes-watch-r20-correction-consumption-checklist.md` |
| R20 guarded apply candidate generation v0.1 | 완료 | promoted correction policy를 guarded apply candidate artifact와 optional delegate request로 연결 | `notes/2026-04-15-hermes-watch-r20-guarded-apply-candidate-note.md`, `checklists/2026-04-15-hermes-watch-r20-guarded-apply-candidate-checklist.md` |
| R20 guarded apply delegate consumption v0.1 | 완료 | guarded apply candidate의 delegate request를 bridge/launch로 실제 소비해 child patch-candidate 작업을 시작 | `notes/2026-04-15-hermes-watch-r20-guarded-apply-delegate-consumption-note.md`, `checklists/2026-04-15-hermes-watch-r20-guarded-apply-delegate-consumption-checklist.md` |
| R20 patch-candidate result verification / ingestion v0.1 | 완료 | child LLM이 만든 patch-candidate artifact를 검증하고 apply candidate manifest에 반영 | `notes/2026-04-15-hermes-watch-r20-patch-candidate-verification-note.md`, `checklists/2026-04-15-hermes-watch-r20-patch-candidate-verification-checklist.md` |
| R20 guarded patch apply + build/smoke rerun v0.1 | 완료 | verified patch-candidate를 제한적으로 적용하고 rerun 결과를 apply result artifact로 남김 | `notes/2026-04-15-hermes-watch-r20-guarded-patch-apply-note.md`, `checklists/2026-04-15-hermes-watch-r20-guarded-patch-apply-checklist.md` |
| R20 rollback / failure recovery v0.1 | 완료 | apply 실패 시 backup에서 원본 target file을 복구하고 rollback 상태를 artifact에 기록 | `notes/2026-04-15-hermes-watch-r20-rollback-failure-recovery-note.md`, `checklists/2026-04-15-hermes-watch-r20-rollback-failure-recovery-checklist.md` |
| R20 candidate semantics / diff safety v0.1 | 완료 | apply 전에 patch 의미/범위를 guardrail로 차단하고 blocked apply도 lineage로 남김 | `notes/2026-04-15-hermes-watch-r20-candidate-semantics-diff-safety-note.md`, `checklists/2026-04-15-hermes-watch-r20-candidate-semantics-diff-safety-checklist.md` |
| R20 multi-step recovery policy v0.1 | 완료 | blocked/rollback/success 결과를 `hold / retry / abort / resolved`로 분기하는 recovery layer 추가 | `notes/2026-04-15-hermes-watch-r20-multi-step-recovery-policy-note.md`, `checklists/2026-04-15-hermes-watch-r20-multi-step-recovery-policy-checklist.md` |
| R20 recovery policy consumption / routing v0.1 | 완료 | recovery decision을 queue/registry artifact로 연결해 후속 orchestration 입력으로 변환 | `notes/2026-04-15-hermes-watch-r20-recovery-policy-consumption-routing-note.md`, `checklists/2026-04-15-hermes-watch-r20-recovery-policy-consumption-routing-checklist.md` |
| R20 recovery queue consumption / bridge rearming v0.1 | 완료 | retry queue를 bridge rearm으로, hold queue를 review parking으로 연결하는 consumer 추가 | `notes/2026-04-15-hermes-watch-r20-recovery-queue-consumption-bridge-rearming-note.md`, `checklists/2026-04-15-hermes-watch-r20-recovery-queue-consumption-bridge-rearming-checklist.md` |
| R20 recovery downstream automation v0.1 | 완료 | retry lane을 consume → rearm → launch → verify까지 이어 붙이는 downstream automation 추가 | `notes/2026-04-15-hermes-watch-r20-recovery-downstream-automation-note.md`, `checklists/2026-04-15-hermes-watch-r20-recovery-downstream-automation-checklist.md` |
| R20 recovery full closed-loop chaining v0.1 | 완료 | retry lane에서 verify 이후 apply와 reroute까지 다시 연결하는 full-chain 추가 | `notes/2026-04-15-hermes-watch-r20-recovery-full-closed-loop-chaining-note.md`, `checklists/2026-04-15-hermes-watch-r20-recovery-full-closed-loop-chaining-checklist.md` |
| R20 retry recursive chaining / termination guard v0.1 | 완료 | retry full-chain을 bounded recursive loop로 반복하고 종료 조건을 추가 | `notes/2026-04-15-hermes-watch-r20-retry-recursive-chaining-termination-guard-note.md`, `checklists/2026-04-15-hermes-watch-r20-retry-recursive-chaining-termination-guard-checklist.md` |
| R20 hold/abort downstream consumers v0.1 | 완료 | hold review lane과 abort corrective route를 실제 refiner consumer에 연결 | `notes/2026-04-15-hermes-watch-r20-hold-abort-downstream-consumers-note.md`, `checklists/2026-04-15-hermes-watch-r20-hold-abort-downstream-consumers-checklist.md` |
| R20 patch diff scope / touched-region safety v0.1 | 완료 | generated harness 내부에서도 touched region/function/whitelist 수준 안전성을 더 세밀하게 검증 | `notes/2026-04-15-hermes-watch-r20-patch-diff-scope-touched-region-safety-note.md`, `checklists/2026-04-15-hermes-watch-r20-patch-diff-scope-touched-region-safety-checklist.md` |
| R20 hold/abort follow-up auto-reingestion v0.1 | 완료 | verified hold/abort follow-up 결과를 correction-policy / apply-candidate loop 입력으로 재주입 | `notes/2026-04-16-hermes-watch-r20-hold-abort-followup-auto-reingestion-note.md`, `checklists/2026-04-16-hermes-watch-r20-hold-abort-followup-auto-reingestion-checklist.md` |
| R20 reingested downstream chaining v0.1 | 완료 | verified hold/abort follow-up 재주입 뒤 bridge/verify/apply/reroute rail까지 더 이어붙임 | `notes/2026-04-16-hermes-watch-r20-reingested-downstream-chaining-note.md`, `checklists/2026-04-16-hermes-watch-r20-reingested-downstream-chaining-checklist.md` |
| R20 follow-up failure policy reverse linkage v0.1 | 완료 | unverified/escalated follow-up 결과를 original apply candidate lineage에 역반영 | `notes/2026-04-16-hermes-watch-r20-followup-failure-policy-reverse-linkage-note.md`, `checklists/2026-04-16-hermes-watch-r20-followup-failure-policy-reverse-linkage-checklist.md` |
| R20 retry and downstream budget/cooldown v0.1 | 완료 | retry 및 reingested downstream rail에 최소 cooldown/budget/backoff guard를 도입 | `notes/2026-04-16-hermes-watch-r20-retry-downstream-budget-cooldown-note.md`, `checklists/2026-04-16-hermes-watch-r20-retry-downstream-budget-cooldown-checklist.md` |
| R20 reverse-linked follow-up failure routing integration v0.1 | 완료 | reverse-linked follow-up failure를 next recovery routing / risk 판단에 직접 반영 | `notes/2026-04-16-hermes-watch-r20-reverse-linked-followup-failure-routing-integration-note.md`, `checklists/2026-04-16-hermes-watch-r20-reverse-linked-followup-failure-routing-integration-checklist.md` |
| Adaptive retry / downstream budget-cooldown v0.1 | 완료 | reverse-linked failure / routing risk / failure class 기반으로 cooldown/budget을 차등화 | `notes/2026-04-16-hermes-watch-adaptive-retry-downstream-budget-cooldown-note.md`, `checklists/2026-04-16-hermes-watch-adaptive-retry-downstream-budget-cooldown-checklist.md` |
| Deeper semantic diff safety / corrective intent analysis v0.1 | 완료 | guard-only corrective patch safety를 token-aware exact-match 쪽으로 강화 | `notes/2026-04-16-hermes-watch-deeper-semantic-diff-safety-corrective-intent-analysis-note.md`, `checklists/2026-04-16-hermes-watch-deeper-semantic-diff-safety-corrective-intent-analysis-checklist.md` |
| Full recovery ecosystem recursion v0.1 | 완료 | retry recursive lane과 reingested downstream lane을 bounded ecosystem recursion으로 묶고 stop reason lineage를 기록 | `notes/2026-04-16-hermes-watch-full-recovery-ecosystem-recursion-note.md`, `checklists/2026-04-16-hermes-watch-full-recovery-ecosystem-recursion-checklist.md` |
| Comment-only / broader corrective intent analysis v0.1 | 완료 | comment-only rail이 summary 단계에서 실제 코드 mutation 의도를 선제 차단하도록 강화 | `notes/2026-04-16-hermes-watch-comment-only-broader-corrective-intent-analysis-note.md`, `checklists/2026-04-16-hermes-watch-comment-only-broader-corrective-intent-analysis-checklist.md` |
| Multi-target adapter generalization v0.1 | 완료 | target profile adapter spec이 main runtime command/label/target selection에 실제 반영되도록 연결 | `notes/2026-04-16-hermes-watch-multi-target-adapter-generalization-v0.1-note.md`, `checklists/2026-04-16-hermes-watch-multi-target-adapter-generalization-v0.1-checklist.md` |
| Multi-target adapter generalization v0.2 — command separation slice | 완료 | harness probe / skeleton closure의 build·smoke command derivation도 profile-driven adapter를 우선 사용하도록 확장 | `notes/2026-04-16-hermes-watch-multi-target-adapter-generalization-v0.2-command-separation-note.md`, `checklists/2026-04-16-hermes-watch-multi-target-adapter-generalization-v0.2-command-separation-checklist.md` |
| Multi-target adapter generalization v0.2 — editable-region policy seam slice | 완료 | mutation safety rail이 editable harness root / fuzz entrypoint policy도 profile-driven adapter에서 읽도록 확장 | `notes/2026-04-16-hermes-watch-multi-target-adapter-generalization-v0.2-editable-region-policy-note.md`, `checklists/2026-04-16-hermes-watch-multi-target-adapter-generalization-v0.2-editable-region-policy-checklist.md` |
| Multi-target adapter generalization v0.2 — regression smoke matrix slice | 완료 | main / probe / closure / policy 관점의 adapter contract를 한 장에서 점검 가능한 regression smoke matrix artifact 추가 | `notes/2026-04-16-hermes-watch-multi-target-adapter-generalization-v0.2-regression-smoke-matrix-note.md`, `checklists/2026-04-16-hermes-watch-multi-target-adapter-generalization-v0.2-regression-smoke-matrix-checklist.md` |
| Multi-target adapter generalization v0.2 — mutation generation seam slice | 완료 | guard-only patch generation이 runtime adapter의 fuzz entrypoint policy를 실제 소비하고 planning helper로 분리되기 시작 | `notes/2026-04-16-hermes-watch-multi-target-adapter-generalization-v0.2-mutation-generation-seam-note.md`, `checklists/2026-04-16-hermes-watch-multi-target-adapter-generalization-v0.2-mutation-generation-seam-checklist.md` |
| Multi-target adapter generalization v0.2 — guard policy contract slice | 완료 | runtime adapter가 guard condition / return policy까지 들고 다니며 guarded apply generation과 whitelist가 같은 계약을 실제 소비 | `notes/2026-04-16-hermes-watch-multi-target-adapter-generalization-v0.2-guard-policy-contract-note.md`, `checklists/2026-04-16-hermes-watch-multi-target-adapter-generalization-v0.2-guard-policy-contract-checklist.md` |
| Multi-target adapter generalization v0.2 — skeleton entrypoint de-hardcode slice | 완료 | harness skeleton source draft가 runtime adapter의 fuzz entrypoint 이름을 실제 반영하도록 확장 | `notes/2026-04-16-hermes-watch-multi-target-adapter-generalization-v0.2-skeleton-entrypoint-dehardcode-note.md`, `checklists/2026-04-16-hermes-watch-multi-target-adapter-generalization-v0.2-skeleton-entrypoint-dehardcode-checklist.md` |
| Multi-target adapter generalization v0.2 — skeleton body guard-policy alignment slice | 완료 | harness skeleton source draft body가 runtime adapter의 guard contract를 실제 반영하도록 확장 | `notes/2026-04-16-hermes-watch-multi-target-adapter-generalization-v0.2-skeleton-body-guard-policy-alignment-note.md`, `checklists/2026-04-16-hermes-watch-multi-target-adapter-generalization-v0.2-skeleton-body-guard-policy-alignment-checklist.md` |
| Multi-target adapter generalization v0.2 — skeleton call-contract generalization slice | 완료 | harness skeleton source draft가 runtime adapter의 target-call TODO / lifetime hint를 실제 반영하도록 확장 | `notes/2026-04-16-hermes-watch-multi-target-adapter-generalization-v0.2-skeleton-call-contract-generalization-note.md`, `checklists/2026-04-16-hermes-watch-multi-target-adapter-generalization-v0.2-skeleton-call-contract-generalization-checklist.md` |
| LLM evidence packet v0.1 | 완료 | latest run/probe/apply artifacts에서 failure reason을 추출해 LLM 전달용 packet(JSON/Markdown)을 생성 | `notes/2026-04-16-hermes-watch-llm-evidence-packet-v0.1-note.md`, `checklists/2026-04-16-hermes-watch-llm-evidence-packet-v0.1-checklist.md`, `notes/2026-04-16-fuzzing-jpeg2000-code-audit-llm-pivot.md` |
| Failure reason extraction v0.2 | 완료 | latest run history까지 읽어 no-progress / coverage plateau / corpus low-gain / shallow crash recurrence / stage reach blockage를 evidence packet에 직접 구조화 | `notes/2026-04-16-hermes-watch-failure-reason-extraction-v0.2-note.md`, `checklists/2026-04-16-hermes-watch-failure-reason-extraction-v0.2-checklist.md` |
| LLM handoff prompt simplification v0.1 | 완료 | guarded apply delegate handoff가 latest LLM evidence packet의 `failure_reasons` / `llm_objective`를 우선 참조하도록 단순화 | `notes/2026-04-16-hermes-watch-llm-handoff-prompt-simplification-v0.1-note.md`, `checklists/2026-04-16-hermes-watch-llm-handoff-prompt-simplification-v0.1-checklist.md` |
| Failure reason extraction v0.3 | 완료 | smoke/build/fuzz log body-level signal을 evidence packet에 끌어오고 direct script entrypoint 실행성을 복구 | `notes/2026-04-16-hermes-watch-failure-reason-extraction-v0.3-note.md`, `checklists/2026-04-16-hermes-watch-failure-reason-extraction-v0.3-checklist.md` |
| Delegate verification / apply policy evidence-aware lineage v0.1 | 완료 | verification/apply/result artifact가 `llm_objective` / `failure_reason_codes` / `raw_signal_summary`를 다시 유지하도록 연결 | `notes/2026-04-16-hermes-watch-delegate-verification-apply-policy-evidence-aware-lineage-v0.1-note.md`, `checklists/2026-04-16-hermes-watch-delegate-verification-apply-policy-evidence-aware-lineage-v0.1-checklist.md` |
| Failure reason extraction v0.4 | 완료 | build/fuzz log와 harness probe/apply result body signal까지 evidence packet에 포함하고 reason code로 승격 | `notes/2026-04-16-hermes-watch-failure-reason-extraction-v0.4-note.md`, `checklists/2026-04-16-hermes-watch-failure-reason-extraction-v0.4-checklist.md` |
| Failure reason extraction v0.5 | 완료 | repeated body signal을 dedup하고 plane별 signal summary와 top failure reason prioritization을 넣어 evidence packet 압축 품질을 개선 | `notes/2026-04-16-hermes-watch-failure-reason-extraction-v0.5-note.md`, `checklists/2026-04-16-hermes-watch-failure-reason-extraction-v0.5-checklist.md` |
| Failure reason extraction v0.6 | 완료 | per-reason explanation과 top failure reason explanation을 추가해 body signal summary와 reason의 연결을 더 직접 노출 | `notes/2026-04-16-hermes-watch-failure-reason-extraction-v0.6-note.md`, `checklists/2026-04-16-hermes-watch-failure-reason-extraction-v0.6-checklist.md` |
| Failure reason extraction v0.7 | 완료 | per-reason causal chain과 top failure reason chain을 추가해 source/outcome/signal-summary-to-reason 압축을 더 chain-like하게 노출 | `notes/2026-04-16-hermes-watch-failure-reason-extraction-v0.7-note.md`, `checklists/2026-04-16-hermes-watch-failure-reason-extraction-v0.7-checklist.md` |
| Failure reason extraction v0.8 | 완료 | top failure reason들을 primary/supporting/deferred narrative step으로 압축해 왜 이 reason들이 함께 보이는지 multi-reason reading을 더 직접 노출 | `notes/2026-04-16-hermes-watch-failure-reason-extraction-v0.8-note.md`, `checklists/2026-04-16-hermes-watch-failure-reason-extraction-v0.8-checklist.md` |
| Evidence-aware output schema tightening v0.1 | 완료 | delegate patch artifact가 `## Evidence Response` section으로 `llm_objective` / `failure_reason_codes`에 직접 답하도록 요구·검증하고 결과 artifact에도 다시 남김 | `notes/2026-04-16-hermes-watch-evidence-aware-output-schema-tightening-v0.1-note.md`, `checklists/2026-04-16-hermes-watch-evidence-aware-output-schema-tightening-v0.1-checklist.md` |
| Evidence-faithful patch validation v0.1 | 완료 | delegate artifact의 Patch Summary와 Evidence Response를 함께 읽어 objective/response summary와 최소 정합성 검증을 추가하고 결과 lineage에 반영 | `notes/2026-04-16-hermes-watch-evidence-faithful-patch-validation-v0.1-note.md`, `checklists/2026-04-16-hermes-watch-evidence-faithful-patch-validation-v0.1-checklist.md` |
| Diff-aware evidence-to-patch validation v0.1 | 완료 | apply 단계에서 실제 mutation shape(comment-only / guard-only)를 계산하고 delegate patch summary와의 정합성을 결과 lineage에 반영 | `notes/2026-04-16-hermes-watch-diff-aware-evidence-to-patch-validation-v0.1-note.md`, `checklists/2026-04-16-hermes-watch-diff-aware-evidence-to-patch-validation-v0.1-checklist.md` |
| Hunk-intent-aware diff validation v0.1 | 완료 | apply 결과의 added hunk line preview를 기록하고 Patch Summary가 실제 changed line 의미와 맞는지 최소 검증을 추가 | `notes/2026-04-16-hermes-watch-hunk-intent-aware-diff-validation-v0.1-note.md`, `checklists/2026-04-16-hermes-watch-hunk-intent-aware-diff-validation-v0.1-checklist.md` |
| Failure-reason-to-hunk mapping v0.1 | 완료 | changed hunk intent를 작게 분류하고 `failure_reason_codes`가 기대하는 수정 방향과의 최소 정합성을 apply/result lineage에 반영 | `notes/2026-04-16-hermes-watch-failure-reason-to-hunk-mapping-v0.1-note.md`, `checklists/2026-04-16-hermes-watch-failure-reason-to-hunk-mapping-v0.1-checklist.md` |
| Multi-reason hunk prioritization v0.1 | 완료 | `top_failure_reason_codes`를 apply 단계의 primary reason basis로 연결해 packet priority와 hunk validation priority를 같은 spine으로 맞추기 시작 | `notes/2026-04-16-hermes-watch-multi-reason-hunk-prioritization-v0.1-note.md`, `checklists/2026-04-16-hermes-watch-multi-reason-hunk-prioritization-v0.1-checklist.md` |
| Secondary-reason conflict surfacing v0.1 | 완료 | primary/top reason에 맞춘 hunk alignment 뒤에 숨던 deferred secondary reason tension을 apply/result lineage에 노출 | `notes/2026-04-16-hermes-watch-secondary-reason-conflict-surfacing-v0.1-note.md`, `checklists/2026-04-16-hermes-watch-secondary-reason-conflict-surfacing-v0.1-checklist.md` |
| Secondary-conflict-aware routing v0.1 | 완료 | deferred secondary tension이 `retry` recovery routing을 보수적인 `hold`/risk override로 실제 꺾도록 연결 | `notes/2026-04-16-hermes-watch-secondary-conflict-aware-routing-v0.1-note.md`, `checklists/2026-04-16-hermes-watch-secondary-conflict-aware-routing-v0.1-checklist.md` |
| Secondary-conflict severity/actionability v0.1 | 완료 | deferred secondary conflict를 reviewable tension과 corrective-regeneration 급 tension으로 나누어 `hold`/`abort` routing을 실제 분기 | `notes/2026-04-16-hermes-watch-secondary-conflict-severity-actionability-v0.1-note.md`, `checklists/2026-04-16-hermes-watch-secondary-conflict-severity-actionability-v0.1-checklist.md` |
| Finding-efficiency-facing intelligence v0.1 | 완료 | run history에서 coverage delta / corpus growth / shallow novelty 신호를 별도 summary/recommendation으로 압축해 LLM packet 상단에 노출 | `notes/2026-04-16-hermes-watch-finding-efficiency-facing-intelligence-v0.1-note.md`, `checklists/2026-04-16-hermes-watch-finding-efficiency-facing-intelligence-v0.1-checklist.md` |
| Failure reason extraction v0.9 | 완료 | top reason narrative와 finding recommendation을 suggested action code / candidate route / objective linkage summary로 연결 | `notes/2026-04-16-hermes-watch-failure-reason-extraction-v0.9-note.md`, `checklists/2026-04-16-hermes-watch-failure-reason-extraction-v0.9-checklist.md` |
| Smoke/profile alignment v0.1 | 완료 | watcher smoke baseline에서 regression seed를 빼고 deep-decode-v3 harness/fuzzer 경로로 실제 진입시키는 runtime contract 정렬 | `notes/2026-04-16-hermes-watch-smoke-profile-alignment-v0.1-note.md`, `checklists/2026-04-16-hermes-watch-smoke-profile-alignment-v0.1-checklist.md` |
| Autonomous supervisor loop v0.1 | 완료 | periodic cron 대신 self-prompt 기반 local long-running daemon과 status/log artifacts를 도입 | `notes/2026-04-16-hermes-watch-autonomous-supervisor-loop-v0.1-note.md`, `checklists/2026-04-16-hermes-watch-autonomous-supervisor-loop-v0.1-checklist.md` |
| Leak closure evidence slice v0.1 | 완료 | LeakSanitizer/stack line을 crash excerpt에 보존하고 stale current_status에서도 leak-aware LLM objective/routing을 복구 | `notes/2026-04-16-hermes-watch-leak-closure-evidence-slice-v0.1-note.md`, `checklists/2026-04-16-hermes-watch-leak-closure-evidence-slice-v0.1-checklist.md` |
| Leak signature capture hardening v0.1 | 완료 | long leak stack에서도 summary/artifact/meaningful project frame을 보존해 watcher 원본 signature를 `leak|coding_units.cpp:3927|...` 쪽으로 복구 | `notes/2026-04-16-hermes-watch-leak-signature-capture-hardening-v0.1-note.md`, `checklists/2026-04-16-hermes-watch-leak-signature-capture-hardening-v0.1-checklist.md` |
| Leak state rehydration v0.1 | 완료 | stale latest run의 current_status/run_history/crash_index를 `fuzz.log`에서 다시 읽어 canonical leak signature와 policy로 복구 | `notes/2026-04-16-hermes-watch-leak-state-rehydration-v0.1-note.md`, `checklists/2026-04-16-hermes-watch-leak-state-rehydration-v0.1-checklist.md` |
| Rehydrated report sync v0.1 | 완료 | rehydrate 이후 stale `FUZZING_REPORT.md` section도 canonical leak classification/policy/fingerprint/excerpt로 다시 써서 artifact/state/report surface를 정렬 | `notes/2026-04-16-hermes-watch-rehydrated-report-sync-v0.1-note.md`, `checklists/2026-04-16-hermes-watch-rehydrated-report-sync-v0.1-checklist.md` |
| Policy-aware Recommended Next Action + bounded rerun v0.1 | 완료 | report 말미 action summary를 policy spine에 맞추고 fresh bounded rerun에서 새 deep-stage crash family + aligned action contract를 함께 검증 | `notes/2026-04-16-hermes-watch-policy-aware-recommended-next-action-and-bounded-rerun-v0.1-note.md`, `checklists/2026-04-16-hermes-watch-policy-aware-recommended-next-action-and-bounded-rerun-v0.1-checklist.md` |
| Critical crash follow-up triage trigger v0.1 | 완료 | `continue_and_prioritize_triage`/`high_priority_alert`가 실제 `triage` follow-up command와 same-mode skip guard를 타도록 연결해 critical crash policy를 실행 rail로 복구 | `notes/2026-04-16-hermes-watch-critical-crash-followup-triage-trigger-v0.1-note.md`, `checklists/2026-04-16-hermes-watch-critical-crash-followup-triage-trigger-v0.1-checklist.md` |
| Deep crash routing override v0.1 | 완료 | 이미 deep critical crash가 잡힌 packet에서는 stale deeper push를 review-current-candidate로 꺾어 LLM routing을 현재 reality와 맞춤 | `notes/2026-04-16-hermes-watch-deep-crash-routing-override-v0.1-note.md`, `checklists/2026-04-16-hermes-watch-deep-crash-routing-override-v0.1-checklist.md` |
| Duplicate deep crash replay review routing v0.1 | 완료 | repeated deep duplicate crash family를 단순 known-bad sink 대신 replay/minimization review registry와 refiner plan rail로 승격 | `notes/2026-04-16-hermes-watch-duplicate-deep-crash-replay-review-routing-v0.1-note.md`, `checklists/2026-04-16-hermes-watch-duplicate-deep-crash-replay-review-routing-v0.1-checklist.md` |
| Duplicate crash compare plan enrichment v0.1 | 완료 | duplicate review plan/prompt가 first/latest run·report·artifact lineage와 low-risk compare command를 자동 포함하도록 보강 | `notes/2026-04-16-hermes-watch-duplicate-crash-compare-plan-enrichment-v0.1-note.md`, `checklists/2026-04-16-hermes-watch-duplicate-crash-compare-plan-enrichment-v0.1-checklist.md` |
| LLM evidence sync and duplicate review rehydration v0.1 | 완료 | watcher 종료마다 latest evidence packet을 자동 refresh하고 duplicate review registry/packet context가 recurrence를 따라가게 보강 | `notes/2026-04-16-hermes-watch-llm-evidence-sync-and-duplicate-review-rehydration-v0.1-note.md`, `checklists/2026-04-16-hermes-watch-llm-evidence-sync-and-duplicate-review-rehydration-v0.1-checklist.md` |
| Duplicate replay execution closure v0.1 | 완료 | duplicate review rail이 actual first/latest bounded replay artifact·exit·signature를 남기고 symbolized offline replay를 canonical plan/registry/markdown surface에 반영 | `notes/2026-04-16-hermes-watch-duplicate-replay-execution-closure-v0.1-note.md`, `checklists/2026-04-16-hermes-watch-duplicate-replay-execution-closure-v0.1-checklist.md` |
| Duplicate replay follow-up routing v0.1 | 완료 | stable duplicate replay evidence가 `minimize_and_reseed` corpus refinement queue와 duplicate-review LLM routing override로 이어지기 시작 | `notes/2026-04-16-hermes-watch-duplicate-replay-followup-routing-v0.1-note.md`, `checklists/2026-04-16-hermes-watch-duplicate-replay-followup-routing-v0.1-checklist.md` |
| Replay-derived corpus refinement execution closure v0.1 | 완료 | duplicate replay 기반 `minimize_and_reseed` rail이 실제 corpus bucket sync + retention replay evidence까지 남기기 시작 | `notes/2026-04-16-hermes-watch-replay-derived-corpus-refinement-execution-closure-v0.1-note.md`, `checklists/2026-04-16-hermes-watch-replay-derived-corpus-refinement-execution-closure-v0.1-checklist.md` |
| Medium duplicate replay escalation + packet recovery v0.1 | 완료 | repeated medium duplicate family도 replay review rail과 LLM packet recovery를 다시 타며 latest repeated crash를 reseed/minimization next step으로 연결 | `notes/2026-04-16-hermes-watch-medium-duplicate-replay-escalation-and-packet-recovery-v0.1-note.md`, `checklists/2026-04-16-hermes-watch-medium-duplicate-replay-escalation-and-packet-recovery-v0.1-checklist.md` |
| Medium duplicate corpus refinement execution + refiner LLM refresh v0.1 | 완료 | `coding_units.cpp:3076` medium duplicate family도 actual bucket sync + retention replay를 닫고, refiner executor 종료 시 LLM evidence packet도 즉시 refresh되도록 보강 | `notes/2026-04-16-hermes-watch-medium-duplicate-corpus-refinement-execution-and-llm-refresh-v0.1-note.md`, `checklists/2026-04-16-hermes-watch-medium-duplicate-corpus-refinement-execution-and-llm-refresh-v0.1-checklist.md` |
| Deep-decode-v3 runtime corpus override alignment v0.1 | 완료 | active profile의 hard-pinned `CORPUS_DIR` contract를 env-override friendly로 바꿔 `run-fuzz-mode.sh`의 triage/coverage/regression wrapper가 실제 corpus를 fuzzer까지 전달하도록 수정 | `notes/2026-04-16-deep-decode-v3-runtime-corpus-override-alignment-v0.1-note.md`, `checklists/2026-04-16-deep-decode-v3-runtime-corpus-override-alignment-v0.1-checklist.md` |
| Replay-derived corpus refinement plan closure v0.1 | 완료 | duplicate replay에서 생긴 `minimize_and_reseed` queue가 actual plan/orchestration/dispatch request artifact로 소비되기 시작 | `notes/2026-04-16-hermes-watch-replay-derived-corpus-refinement-plan-closure-v0.1-note.md`, `checklists/2026-04-16-hermes-watch-replay-derived-corpus-refinement-plan-closure-v0.1-checklist.md` |
| Multi-target adapter generalization | 보류/중요 | OpenHTJ2K-specific leakage를 더 줄이고 reusable substrate로 넓히는 후속 일반화 단계 | `.hermes/plans/2026-04-15_133343-semi-autonomous-multi-target-fuzzing-roadmap.md`, `checklists/2026-04-16-multi-target-adapter-generalization-prep-checklist.md` |

---

## 단계별 해석

### 1. Foundation v1
이 시기에는 시스템이 “돌아가긴 하는 watcher”에서
**기록과 정책을 남길 수 있는 substrate**로 올라왔다.

핵심:
- crash fingerprint dedup
- policy action
- regression trigger
- corpus/mode 분리

의미:
- 이후 모든 자동화의 기반이 되는 관측면 확보

### 2. Refiner control-plane
이 시기에는 recommendation만 하던 시스템이
**실제로 후속 작업을 queue로 만들고 orchestration artifact로 다루는 구조**를 얻었다.

핵심:
- queue / orchestration / dispatch / bridge / launcher / verification

의미:
- 이 시점부터 시스템은 “판단만 하는 watcher”가 아니라 “후속 조치 substrate”를 갖게 됨

### 3. Target-side intelligence 초입
이 시기에는 타겟을 단순히 fuzz target으로 보지 않고,
**profile / recon / candidate / evaluation** 계층으로 보기 시작했다.

의미:
- 자가발전형 시스템으로 가려면 target model이 필요하므로 매우 중요

### 4. R18 — measured execution quality loop
이 단계에서 처음으로
**실제로 probe/build/smoke/verification에서 얻은 evidence가 registry와 scheduler에 반영**됐다.

의미:
- heuristic-only 판단에서 벗어나기 시작한 전환점

### 5. R19 — harness skeleton generation + revision loop
이 단계에서
**선택된 candidate를 기준으로 skeleton source를 뽑고, feedback를 다음 revision draft로 연결하는 얕은 revision substrate**가 생겼다.

의미:
- 이제 harness generation은 추상 개념이 아니라 artifact-first loop로 내려옴

---

## 이 기록을 어떻게 읽어야 하나

### “최신 상태만 보고 싶다”
- `current-status.md`

### “왜 이런 구조가 되었는지 보고 싶다”
- 이 문서(`progress-index.md`)
- `notes/2026-04-15-hermes-watch-system-audit.md`

### “특정 단계 구현 근거를 보고 싶다”
- 각 `notes/*-note.md`
- 각 `checklists/*-checklist.md`

### “장기적으로 어디까지 가려는지 보고 싶다”
- `.hermes/plans/2026-04-15_133343-semi-autonomous-multi-target-fuzzing-roadmap.md`

---

## 피드백/버전관리 관점 운영 규칙

### 규칙 1. 단계는 버전처럼 다룬다
각 단계는 단순 완료가 아니라:
- 무엇을 새로 가능하게 했는지
- 무엇은 여전히 못 하는지
- 다음 단계가 왜 필요한지
를 남긴다.

### 규칙 2. 실패 가능성도 기록한다
나중에 이 시스템이 기대만큼 finding efficiency를 못 낼 수도 있다.
그 경우를 대비해:
- 어떤 가정이 틀렸는지
- 어떤 단계가 실효성이 낮았는지
- 어떤 구조가 과잉이었는지
도 기록한다.

### 규칙 3. note + checklist + status를 삼각 구조로 유지한다
- `note`: 의미/해석
- `checklist`: 실행 검증
- `current-status`: 최신 판단

### 규칙 4. 상위 문서는 입구 역할을 해야 한다
문서가 많아질수록 `README.md`, `current-status.md`, `progress-index.md`가
항상 먼저 읽히는 canonical 문서가 되어야 한다.

---

## 현재 냉정한 판단
### 잘 되고 있는가?
**방향은 꽤 잘 가고 있다.**

왜냐면 지금까지는:
- 관측면
- 정책면
- orchestration면
- target-side intelligence 초입
- evidence-aware weighting
- skeleton revision substrate
순으로 비교적 안전하게 올라왔기 때문이다.

### 아직 보장되지 않는 것은?
아직 보장되지 않는 것은:
- 실제 finding efficiency 상승
- skeleton auto-revision의 실효성
- 멀티타겟 일반화의 비용 대비 효율

그래서 지금 문서 체계는 성공 기록이 아니라
## **실험 버전 기록 + 피드백 메모리**
여야 한다.

---

## 다음 단계
1. `reseed effectiveness measurement`
   - 이제 wrapper corpus override가 실제로 먹으므로 coverage corpus 기준 bounded rerun 전후 novelty / duplicate recurrence / coverage delta를 계측
2. `active corpus toxic-seed quarantine`
   - 이번 rerun에서 다시 드러난 `j2kmarkers.cpp:52` duplicate dominance를 active coverage bucket 수준에서 줄이는 안전한 격리 규칙 추가
3. `remote/proxmox closure`
   - local evidence/triage 품질을 유지한 채 remote bridge에서도 같은 override-friendly corpus contract와 preservation/replay loop가 재현되는지 검증

---

## 한 줄 운영 원칙
## **이 시스템은 ‘언젠가 잘 될 거라 믿고 밀어붙이는 프로젝트’가 아니라, 각 단계를 버전처럼 남기고 피드백을 통해 더 나은 구조로 수렴시키는 퍼징 연구/엔지니어링 시스템이다.**
