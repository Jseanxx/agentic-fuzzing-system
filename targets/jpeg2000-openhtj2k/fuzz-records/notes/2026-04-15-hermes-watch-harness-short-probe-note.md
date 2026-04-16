# Hermes Watch Upgrade Note — Harness Short Build/Smoke Probe Path

Date: 2026-04-15

## Why this step
The system could already emit recon, profile, harness-draft, and evaluation-draft artifacts. The next step was introducing a very small verified execution loop without jumping into full harness generation or unattended fuzzing. This change adds a strict fail-fast short probe path for the top harness candidate.

## What changed
- Added `scripts/hermes_watch_support/harness_probe.py`
- Added `build_harness_probe_draft(repo_root)`
- Added `run_short_harness_probe(repo_root, probe_runner=...)`
- Added CLI mode: `--run-short-harness-probe`
- Probe run writes:
  - harness probe manifest JSON
  - harness probe markdown artifact
- Output location:
  - `fuzz-records/harness-probes/`

## Current short-probe behavior
This is intentionally conservative:
- starts from the top-ranked evaluation candidate
- infers a build probe command from the detected build system
- looks for exactly one baseline seed from common seed/corpus directories
- only enables smoke execution when a helper script exists (`scripts/run-smoke.sh` or `run-smoke.sh`)
- executes build probe first and skips/halts smoke on build failure

## Important limitation
This is still a narrow execution bridge, not full automatic harness validation.
It does not yet:
- synthesize harness code
- infer callable smoke commands from binaries or APIs automatically
- enforce subprocess timeouts inside the support module itself
- map probe failures back into profile/adapter updates automatically

## Why this matters
This is the first real executed step in the new multi-target artifact pipeline:
- target repo -> recon
- recon -> profile auto-draft
- profile/recon -> harness draft
- harness draft -> evaluation draft
- evaluation draft -> short build/smoke probe

That means the system is no longer only generating plans; it can now execute a tiny fail-fast validation loop for a reviewed top candidate.

## Recommended next step after this
- capture probe outcomes as structured feedback into profile/adapter refinement
- then move to harness skeleton generation only for candidates that pass the short probe cleanly
