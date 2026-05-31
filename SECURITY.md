# Security Policy

Agentic Fuzzing System is a defensive security research project. The repository is intended for authorized fuzzing, maintainer automation, crash triage, and evidence-backed harness engineering.

## Scope

In scope:

- issues in this repository's automation, harnesses, documentation, and target-specific workflow
- unsafe handling of crash artifacts or fuzzing evidence
- bugs that could cause misleading triage, unsafe replay guidance, or accidental data exposure

Out of scope:

- testing systems, services, or repositories without authorization
- requests to weaponize crash samples or turn research artifacts into exploit guidance
- reports that only demonstrate behavior in third-party software without a clear maintainer-safe reproduction path

## Reporting

If you believe you found a security-relevant issue in this repository, open a GitHub issue with a minimal description, affected files, and safe reproduction steps. If the report involves sensitive crash material, omit raw payloads from the public issue and describe how to reproduce or share them safely.

## Responsible Use

Use this project only on software you own, maintain, or have explicit permission to test. The goal is to help maintainers preserve meaningful crashes, reduce noisy duplicate rediscovery, and make fuzzing evidence easier to review.

## Disclosure Philosophy

This project favors evidence-first, maintainer-readable reporting:

- preserve the crash lineage
- explain whether the signal is new, duplicated, shallow, or deep
- keep harness and corpus changes bounded
- verify behavior before making claims
- avoid exploit-oriented language unless it is needed for a responsible maintainer report
