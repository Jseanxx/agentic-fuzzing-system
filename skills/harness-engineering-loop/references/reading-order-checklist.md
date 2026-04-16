# Harness Engineering Reading Order Checklist

Use this checklist before any harness change.

## 1. Current state
- [ ] Read `fuzz-records/current-status.md`
- [ ] Read `fuzz-records/llm-evidence/openhtj2k-llm-evidence.json`
- [ ] Read `fuzz-records/profiles/openhtj2k-target-profile-v1.yaml`

## 2. Relevant evidence family
Choose the most relevant family first.

### Duplicate-family heavy
- [ ] Read latest `fuzz-records/duplicate-crash-replays/*.json|md|log`
- [ ] Read latest `fuzz-records/corpus-refinement-executions/*.json|md|log`
- [ ] Read matching `fuzz-records/refiner-plans/*.md`

### Build/smoke instability
- [ ] Read latest `FUZZING_REPORT.md`
- [ ] Read sibling `build.log`
- [ ] Read sibling `smoke.log`
- [ ] Read latest harness probe/apply artifact if relevant

### Shallow-stage dominance
- [ ] Read target profile stage definitions
- [ ] Read evidence packet objective/stage clues
- [ ] Read latest probe/evaluation artifacts

## 3. Source inspection
- [ ] Read exact harness source file first
- [ ] Read only the relevant helper module second
- [ ] Read only the needed function slice in `scripts/hermes_watch.py`
- [ ] Avoid whole-file monolith reading unless dependency tracing truly requires it

## 4. Four LLM roles
- [ ] Diagnose artifact written
- [ ] Proposal artifact written
- [ ] Critique artifact written
- [ ] Post-run analysis artifact written or explicitly deferred with reason

## 5. Success criteria
- [ ] Expected signal change was stated before patching
- [ ] Rerun result was compared against expectation
- [ ] Stage reach / duplicate pressure / crash quality were evaluated
