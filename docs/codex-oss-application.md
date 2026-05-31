# Codex for Open Source Application Notes

This document collects the form fields, OSINT notes, and application-ready text for the OpenAI Codex for Open Source program.

## Form Fields

Source: https://openai.com/ko-KR/form/codex-for-oss/

| Field | Draft value |
| --- | --- |
| 성 / Last name | IM |
| 이름 / First name | JUNSEO |
| Email | `<ChatGPT account email>` |
| GitHub username | Jseanxx |
| GitHub repository URL | https://github.com/Jseanxx/agentic-fuzzing-system |
| Role | Primary maintainer |
| Interested in | Codex Security, API credits |
| OpenAI organization ID | `<OpenAI organization ID from platform.openai.com>` |

## OSINT Notes

Official signals to optimize for:

- OpenAI says the program supports maintainers of important open-source software, with benefits for coding, triage, review, maintainer workflows, Codex Security, and API credits.
- Selection can consider repository usage, ecosystem importance, active maintenance, role/permissions, and program capacity.
- Projects that do not perfectly match the criteria can still apply if they play an important ecosystem role and explain why.
- Terms say OpenAI may verify identity, repository affiliation, maintainer status, and repository control.
- Public examples emphasize repeatable maintainer workflows: issue/PR triage, release prep, verification, integration testing, repo-local skills, and GitHub Actions.
- Community examples suggest the strongest narrative is not "AI writes code for me", but "Codex helps maintainers reason over large evidence/history and make reviewable decisions."

Application strategy:

- Do not overfocus on stars. This repo is early, so lead with ecosystem importance and workflow quality.
- Emphasize that this is a maintainer tool for authorized defensive fuzzing, not arbitrary scanning.
- Show concrete artifacts already in the repo: harness loop skill, current status, progress index, crash replay records, corpus refinement records, target profile, and LLM evidence packets.
- Explain why API credits are needed: repeated evidence summarization, harness critique, replay/minimization planning, and post-run comparison are token-heavy.
- Keep the safety line explicit: bounded, reviewable, authorized, artifact-first.

## Final Recommended Form Answers

Use these answers first. They are written to be strong but still defensible from the repository contents.

### Role Answer

Primary maintainer and security researcher. I design the workflow, maintain the OpenHTJ2K/JPEG2000 testbed, write the harness/control-plane code, review fuzzing evidence, and use this repository as the canonical record for crash replay, corpus refinement, and LLM-assisted harness engineering.

### Why This Repository Fits

Agentic Fuzzing System is an OSS security-research project for evidence-driven fuzzing maintenance. We are building a reusable workflow that helps native maintainers turn target profiles, harness revisions, corpus curation, crash replay, and LLM handoffs into reviewable security evidence. The OpenHTJ2K/JPEG2000 testbed already records crash families, replay results, corpus quarantine, progress history, and agent skills. Codex would help mature this into tooling OSS security teams can adapt.

Character count: 499

### Planned API Credit Use

API credits would fund the token-heavy parts of defensive OSS fuzzing: summarizing long run artifacts, generating and critiquing small harness revisions, comparing pre/post-run signals, classifying duplicate crash families, drafting replay/minimization plans, and producing maintainer-readable reports. The goal is reviewable, authorized security automation that preserves meaningful crashes and reduces noisy duplicate rediscovery, not unattended scanning.

Character count: 448

### Additional Context

We are security researchers building this because fuzzing often fails at the maintenance layer: crashes are found, then lost in noisy corpora, weak triage, or unreviewed harness changes. This project aims to turn fuzzing into auditable evidence that helps maintainers improve parser safety, crash handling, and release confidence across OSS.

Character count: 326

## Backup Variants

### More Ecosystem-Focused Variant: Why This Repository Fits

Agentic Fuzzing System contributes to the OSS security ecosystem by making fuzzing results easier for maintainers to trust and act on. It combines target profiling, harness engineering, corpus curation, crash replay, and LLM evidence packets into a bounded workflow. The current JPEG2000/OpenHTJ2K target is a realistic native-code parser testbed. Codex would help turn this research prototype into reusable maintainer automation.

Character count: 430

### More Research-Focused Variant: Why This Repository Fits

Agentic Fuzzing System is an OSS maintainer tool for evidence-driven fuzzing. It uses target profiles, harness engineering, crash replay, corpus quarantine, and LLM handoff packets to make fuzzing results reviewable instead of noisy. The current OpenHTJ2K/JPEG2000 testbed already has concrete artifacts and progress records. Codex would directly support safer harness revisions, triage, and maintainer automation.

Character count: 403

### Shorter Additional Context

This project is defensive and authorization-bound. It exists to help security researchers and OSS maintainers convert fuzzing output into evidence-backed decisions: which crashes matter, which seeds should be preserved, which harness changes are safe, and what should be verified before release.

Character count: 284
