---
name: harness-engineering-loop
description: Run harness engineering as a fixed LLM-first debugging loop by forcing a reading order over fuzz-records artifacts, target profile docs, harness source slices, and post-run signal diffs before any harness change.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [fuzzing, harness-engineering, debugging, llm-first, artifact-first]
    related_skills: [systematic-debugging, self-improving-fuzzing-workflow, fuzzing-records-doc-governance, subagent-driven-development]
---

# Harness Engineering Loop

## Use when
- The user wants **LLM intervention on every harness revision cycle**
- The fuzzing codebase is too large for ad-hoc whole-file reasoning
- A harness change must be grounded in specific evidence, not generic patching
- The workflow has many artifacts (`current-status`, `llm-evidence`, replay logs, refinement logs, plans) and the agent needs a fixed reading order
- The real goal is **meaningful crashes via better harness engineering and better debugging**, not just more automation

## Goal
Turn harness work into a **repeatable debugging protocol**:
- read the right artifacts in the right order
- diagnose the actual bottleneck
- propose a bounded harness or seed change
- critique the proposal before applying it
- compare expected vs actual signal after rerun

This skill exists because large watcher/control-plane codebases drift toward "automation paperwork" unless harness engineering is forced to stay evidence-first.

## Core principle
Do **not** let the LLM start by reading `scripts/hermes_watch.py` end-to-end.

Start from the **smallest artifact set that explains the current bottleneck**, then inspect only the relevant source slice.

In this project, harness intelligence should come from:
1. current state
2. LLM evidence packet
3. target profile / stage map
4. recent replay or refinement artifacts
5. relevant harness/debug source slices
6. rerun comparison

## Mandatory 4-stage loop
Every harness modification cycle should pass through these 4 LLM roles:

1. **Diagnose**
2. **Propose**
3. **Critique**
4. **Post-run Analysis**

If one of these stages is skipped, the loop is incomplete.

---

## Stage 1 — Diagnose

### Read in this order
Always read these before proposing a harness change:

1. `fuzz-records/current-status.md`
2. `fuzz-records/llm-evidence/openhtj2k-llm-evidence.json`
3. `fuzz-records/profiles/openhtj2k-target-profile-v1.yaml`
4. Most relevant latest artifact family:
   - duplicate review: `fuzz-records/duplicate-crash-replays/*.json|md|log`
   - corpus refinement: `fuzz-records/corpus-refinement-executions/*.json|md|log`
   - refiner review: `fuzz-records/refiner-plans/*.md`
5. Relevant run artifacts/logs referenced by the evidence packet:
   - `FUZZING_REPORT.md`
   - sibling `build.log`, `smoke.log`, `fuzz.log`
6. Only then read the relevant source slices:
   - harness source file
   - relevant helper module under `scripts/hermes_watch_support/`
   - specific function region in `scripts/hermes_watch.py` if needed

### Diagnose questions
The diagnosis step must answer:
- What is the **primary bottleneck** right now?
- Is the bottleneck mainly:
  - build
  - smoke
  - harness structure
  - seed toxicity
  - shallow duplicate dominance
  - no-progress / coverage stagnation
  - stage-reach failure
- Are we failing to reach deeper decode stages, or repeatedly rediscovering the same family?
- Is the next action more likely a harness edit, seed/corpus action, or replay/minimization action?

### Required diagnosis output
Produce a compact structure with:
- `primary_bottleneck`
- `secondary_bottlenecks`
- `root_cause_hypotheses`
- `why_current_harness_is_weak`
- `recommended_revision_direction`
- `do_not_do`

### Important rule
Do not propose fixes until the diagnosis identifies **why** the current harness is underperforming.
Use the `systematic-debugging` mindset: no patching without bottleneck understanding.

---

## Stage 2 — Propose

### Inputs
Use:
- diagnosis result
- current harness source slice
- relevant target profile stage / adapter / entrypoint contract
- latest evidence packet
- relevant replay/refinement lineage

### Proposal scope
The proposal must be **small and testable**. Typical change classes:
- `guard-tweak`
- `parse-flow-adjustment`
- `stage-reach-enabler`
- `cleanup/lifetime-hardening`
- `instrumentation-aid`
- `seed-routing-change`
- `minimize/reseed-support`

### Required proposal output
Must include:
- `proposed_change_type`
- `expected_effect`
- `risk`
- `minimal_patch_plan`
- `why_this_should_help`
- `what_signal_should_change_if_successful`

### Important rules
- Prefer a bounded edit over a broad rewrite.
- Do not rewrite the harness just because the codebase is noisy.
- If the evidence points to seed toxicity or duplicate replay pressure, say that explicitly instead of forcing a harness patch.

---

## Stage 3 — Critique

### Purpose
Use a second LLM pass to attack the proposal before it lands.
This step exists to stop:
- fake build/smoke fixes
- shallow-only changes that increase duplicate noise
- broad edits disguised as small safety fixes
- stage-irrelevant patches

### Required critique questions
- Does this patch really address the diagnosed bottleneck?
- Is this just making smoke/build pass without improving fuzz usefulness?
- Could it increase shallow parser noise or duplicate family rediscovery?
- Is it mismatched to the stated goal (`stage-reach`, `duplicate-reduction`, `seed-routing`, etc.)?
- Is the proposal too broad for the current evidence quality?

### Required critique output
Must include:
- `critique_verdict` (`good`, `weak`, `misaligned`, `unsafe`)
- `main_objections`
- `fake_fix_risk`
- `expected_failure_mode`
- `approve_or_revise`
- `revision_notes`

### Important rule
If critique says `misaligned` or `unsafe`, revise before applying.
Do not rely on rollback as the only quality filter.

---

## Stage 4 — Post-run Analysis

### Read after rerun
After a patch or seed action, read:
1. new `current-status.md` or current status JSON/report
2. updated LLM evidence packet
3. rerun `FUZZING_REPORT.md`
4. relevant `build.log` / `smoke.log` / `fuzz.log`
5. duplicate replay or corpus refinement execution artifacts if they changed
6. patch/apply result artifact and diff summary

### Required questions
- Did the expected signal change actually happen?
- Did build/smoke improve only superficially, or did fuzz usefulness improve too?
- Did stage reach improve?
- Did duplicate pressure go down?
- Did crash family quality improve, stay flat, or regress?
- Should the next step continue the same direction, or pivot?

### Required post-run output
Must include:
- `result_verdict` (`improved`, `neutral`, `regressed`, `inconclusive`)
- `observed_signal_changes`
- `expected_vs_actual`
- `why_it_failed_or_worked`
- `next_best_action`
- `should_repeat_same_direction`
- `should_pivot`

### Important rule
Do not judge success by build/smoke alone.
The real questions are:
- deeper stage reach?
- less duplicate rediscovery?
- more meaningful crash signal?

---

## Reading protocol by work type

### If the current issue is duplicate-family heavy
Read first:
- `fuzz-records/duplicate-crash-replays/*`
- `fuzz-records/corpus-refinement-executions/*`
- matching duplicate review / minimize plan
Then inspect harness source.

### If the current issue is smoke/build instability
Read first:
- LLM evidence packet
- `FUZZING_REPORT.md`
- `build.log` / `smoke.log`
- latest harness probe / apply result artifacts
Then inspect the harness source slice tied to the failing path.

### If the current issue is shallow-stage dominance
Read first:
- target profile stage definitions
- evidence packet objective / stage-reach clues
- recent duplicate/replay summaries
- harness probe/evaluation artifacts
Then inspect the harness body or adapter-controlled entrypoint path.

### If the current issue is corpus/seed toxicity
Read first:
- latest replay/refinement execution artifacts
- bucket paths and replay retention evidence
- duplicate family summaries
Only then decide whether a harness edit is even warranted.

---

## Minimal source-inspection rule
When code is large, read source in this order:
1. exact harness file being modified
2. exact helper module relevant to the current bottleneck
3. only the needed function slice inside `scripts/hermes_watch.py`
4. avoid whole-file reading unless a dependency chain truly requires it

For this repository, that usually means preferring a targeted slice from:
- `scripts/hermes_watch_support/llm_evidence.py`
- `scripts/hermes_watch_support/harness_probe.py`
- `scripts/hermes_watch_support/harness_feedback.py`
- `scripts/hermes_watch_support/harness_candidates.py`
- `scripts/hermes_watch_support/harness_skeleton.py`
- targeted functions in `scripts/hermes_watch.py`

instead of reloading the entire watcher monolith.

---

## Recommended markdown companions inside the repo
When evolving the project, keep or create a harness-engineering entrypoint such as:
- `fuzz-records/harness-engineering/README.md`
- `fuzz-records/harness-engineering/current-loop.md`
- `fuzz-records/harness-engineering/debugging-rules.md`
- `fuzz-records/harness-engineering/stage-reach-map.md`
- `fuzz-records/harness-engineering/failure-patterns.md`

Use them as the operator-facing equivalent of this skill.

---

## Anti-patterns
Do NOT:
- start with `scripts/hermes_watch.py` full-file reading when an artifact explains the issue faster
- change the harness before reading the latest evidence packet
- confuse seed/corpus debt with harness debt
- treat build/smoke success as the same thing as fuzz usefulness
- accept repeated duplicate rediscovery as progress
- let queue/orchestration paperwork replace real harness debugging
- skip critique because the proposal "looks reasonable"
- skip post-run analysis and jump straight to the next patch

---

## Cold assessment language
When reporting harness work, prefer language like:
- "현재 병목은 하네스 구조보다 duplicate-family 재발견 압력에 더 가깝다"
- "이번 수정은 deep stage reach보다 smoke stabilization에 치우쳐 있다"
- "이 patch는 build-friendly이지만 fuzz-useful하지 않을 가능성이 높다"
- "하네스 수정이 아니라 seed quarantine/minimize가 먼저일 수 있다"
- "stage reach / duplicate pressure / crash quality 기준으로는 아직 개선이 약하다"

---

## Completion standard for one revision cycle
A harness revision cycle is only complete if:
- diagnosis exists
- proposal exists
- critique exists
- rerun happened or was intentionally deferred with reason
- post-run analysis exists
- next action is grounded in observed signal change

If those artifacts do not exist, the cycle is incomplete.
