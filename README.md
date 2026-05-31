# Agentic Fuzzing System

Agentic Fuzzing System is an open-source security research project for turning fuzzing into an evidence-driven maintainer workflow. It combines target profiling, harness engineering, corpus management, crash replay, and LLM-assisted debugging into a repeatable loop for finding, preserving, and explaining meaningful bugs in native-code software.

The project started with a JPEG 2000 / OpenHTJ2K target, but the goal is broader: build a reusable control plane that can help maintainers fuzz complex native-code projects without losing the reasoning trail between a crash, the harness that reached it, the corpus that triggered it, and the next safe change.

## Reviewer Summary

This repository is designed around a concrete security-maintainer problem: fuzzers can find crashes, but maintainers often lose time to noisy corpora, duplicate crash rediscovery, weak triage, and unreviewed harness changes. The project turns that workflow into auditable artifacts that a human maintainer or coding agent can review.

What is already present:

- a realistic native-code parser target: OpenHTJ2K / JPEG 2000
- multiple fuzzing harnesses and run scripts
- crash samples and replay-oriented records
- corpus refinement and quarantine records
- progress/status documents that track completed research slices
- a repo-contained agent skill for evidence-first harness engineering
- a responsible-use boundary for defensive, authorized security work

The intended contribution is not another one-off fuzz harness. It is a reusable maintainer workflow for turning fuzzing output into security evidence that can improve parser safety, crash handling, and release confidence across open-source projects.

## Why This Exists

Traditional fuzzing pipelines can produce a lot of artifacts without answering the questions a maintainer actually needs answered:

- Is this crash new, duplicated, shallow, or worth preserving?
- Did the latest harness change improve deeper code reach, or only make smoke tests pass?
- Which seeds should stay active, and which should be quarantined?
- What evidence should an LLM read before proposing a harness change?
- How do we keep autonomous debugging bounded, reviewable, and reversible?

This repository explores those questions through an artifact-first workflow. Every important action should leave behind enough evidence for a human maintainer or coding agent to understand what happened and why the next step is justified.

## Current Capabilities

- **Harness engineering loop**: a repo-contained skill that forces agents through diagnose, propose, critique, and post-run analysis before changing a harness.
- **Target profiling**: target-specific profiles describe fuzz commands, entrypoints, seed classes, guard policies, and preferred rerun paths.
- **Crash triage and replay**: repeated crash families are fingerprinted, replayed, and routed toward minimization or reseeding instead of being rediscovered forever.
- **Corpus refinement**: active coverage corpora can be curated from target profiles while noisy opaque seeds are moved into quarantine instead of being deleted.
- **Evidence packets for LLMs**: current status, failure reasons, run artifacts, replay context, and suggested next actions are compressed into handoff artifacts.
- **Bounded automation**: proposed changes are scoped, validated, recorded, and connected back to build, smoke, fuzz, and replay evidence.

## Active Testbed

The first validation target is:

```text
targets/jpeg2000-openhtj2k/
```

This target uses OpenHTJ2K, an open-source C++ implementation of JPEG 2000 Part 1 and High-Throughput JPEG 2000. JPEG 2000 decoding is a useful fuzzing testbed because it combines binary parsing, marker handling, tile state, entropy decoding, memory lifetime concerns, and a large space of valid and semi-valid codestream inputs.

The current target contains:

- libFuzzer/AFL++ harnesses under `fuzz/`
- build and run scripts under `scripts/`
- conformance and seed material under `conformance_data/`
- progress, status, replay, corpus, and LLM handoff records under `fuzz-records/`
- crash samples under `../../crash-samples/jpeg2000-openhtj2k/`

## Evidence of Progress

The project is intentionally tracked like a sequence of research versions rather than a loose pile of scripts.

Useful entry points:

- `targets/jpeg2000-openhtj2k/fuzz-records/current-status.md`
- `targets/jpeg2000-openhtj2k/fuzz-records/progress-index.md`
- `skills/harness-engineering-loop/SKILL.md`

Recent completed slices include:

- runtime corpus override alignment for the active deep-decode-v3 profile
- profile-curated coverage corpus quarantine
- medium duplicate replay escalation and packet recovery
- replay-derived corpus refinement execution
- LLM evidence packet generation and refresh
- multi-target adapter generalization slices
- guarded patch apply, rollback, and recovery routing experiments

These records are part of the project surface, not private notes. They are meant to make the system auditable by other maintainers and agents.

## Repository Layout

```text
.
|-- README.md
|-- LICENSE
|-- SECURITY.md
|-- CONTRIBUTING.md
|-- docs/
|   |-- codex-oss-application.md
|   `-- reviewer-brief.md
|-- skills/
|   `-- harness-engineering-loop/
|-- targets/
|   |-- README.md
|   `-- jpeg2000-openhtj2k/
|       |-- fuzz/
|       |-- fuzz-records/
|       |-- scripts/
|       |-- tests/
|       `-- conformance_data/
|-- crash-samples/
|   `-- jpeg2000-openhtj2k/
`-- REPO_RESTRUCTURE_CHECKLIST.md
```

## How an Agent Should Work in This Repo

For harness work, start with the skill:

```text
skills/harness-engineering-loop/SKILL.md
```

The expected loop is:

1. Diagnose the current bottleneck from status, evidence packets, target profiles, and replay artifacts.
2. Propose one bounded harness, seed, corpus, or replay change.
3. Critique the proposal before applying it.
4. Run the relevant build/smoke/fuzz check.
5. Compare expected and actual signal, especially deeper stage reach, duplicate pressure, and crash quality.

The important rule is simple: do not patch from vibes. Patch from evidence, then preserve the evidence that proves whether the patch helped.

## Quick Start

Read the project status first:

```bash
sed -n '1,160p' targets/jpeg2000-openhtj2k/fuzz-records/current-status.md
```

Build and smoke commands for the active target live in:

```text
targets/jpeg2000-openhtj2k/scripts/
```

Target-specific build details live in:

```text
targets/jpeg2000-openhtj2k/FUZZING.md
targets/jpeg2000-openhtj2k/FUZZING_PLAN.md
targets/jpeg2000-openhtj2k/README.md
```

## Roadmap

- Split the reusable control plane from the OpenHTJ2K validation target more cleanly.
- Add a second target to prove that the adapter model is not JPEG2000-specific.
- Improve crash minimization and reseed measurement after duplicate replay.
- Publish a shorter maintainer guide for using the diagnose/propose/critique/post-run loop in other native-code projects.
- Add CI coverage for the top-level agent workflow contracts.

## Responsible Use

This repository is for defensive research, maintainer automation, and authorized testing. Do not use it to fuzz, scan, or test software you do not own or do not have permission to assess. Crash samples and automation artifacts should be handled as security-relevant research material.

## License

Original automation assets in this repository are licensed under the MIT License unless otherwise noted. Third-party target code keeps its own license; the OpenHTJ2K target retains its BSD 3-Clause license under `targets/jpeg2000-openhtj2k/LICENSE`.
