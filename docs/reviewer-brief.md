# Reviewer Brief

Agentic Fuzzing System is an OSS security research project focused on the maintainer side of fuzzing. It is built around a practical problem: fuzzers can generate many crashes and logs, but maintainers need evidence that explains what changed, whether a crash is meaningful, and what safe action should happen next.

## Core Claim

The repository is developing a reusable workflow for evidence-driven fuzzing maintenance:

- target profiles describe how a project should be fuzzed
- harness changes follow a diagnose/propose/critique/post-run loop
- crash families are fingerprinted, replayed, and routed toward minimization or reseeding
- corpora are curated instead of blindly growing forever
- LLM handoff packets summarize the evidence a coding agent should read before acting
- every important step leaves maintainer-readable artifacts

## Why It Matters

Open-source security work often fails after the fuzzer finds something. Crashes can be duplicated, shallow, hard to reproduce, or disconnected from the harness change that caused them. This project aims to make that evidence chain explicit so maintainers can improve parser safety and release confidence without relying on ad hoc notes.

## Current Evidence in the Repository

Start here:

- `README.md`
- `SECURITY.md`
- `CONTRIBUTING.md`
- `skills/harness-engineering-loop/SKILL.md`
- `targets/jpeg2000-openhtj2k/fuzz-records/current-status.md`
- `targets/jpeg2000-openhtj2k/fuzz-records/progress-index.md`
- `targets/jpeg2000-openhtj2k/fuzz/`
- `targets/jpeg2000-openhtj2k/scripts/`
- `crash-samples/jpeg2000-openhtj2k/`

## Codex/API Fit

The token-heavy work is not generic code generation. It is repeated security-maintainer reasoning over long fuzzing artifacts:

- summarize run logs and crash reports
- compare expected vs actual post-run signal
- critique harness changes before they land
- classify duplicate crash families
- draft replay and minimization plans
- produce reports that a maintainer can review

Codex support would help turn this early prototype into a reusable OSS workflow for defensive fuzzing, triage, and security evidence management.
