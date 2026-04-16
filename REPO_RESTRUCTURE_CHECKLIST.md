# Repository Restructure Checklist

- Date: 2026-04-16
- Goal: convert this repo from a JPEG2000-only working tree into a broader **agentic fuzzing system** repository, with JPEG2000/OpenHTJ2K preserved as a target-specific testbed.

## Scope
- [x] Confirm remote/auth/push path
- [x] Define top-level umbrella structure
- [x] Vendor the new harness-engineering skill into the repo
- [x] Move JPEG2000/OpenHTJ2K target work under a dedicated target folder
- [x] Move loose crash samples into a dedicated organized folder
- [x] Replace the root README with umbrella-project framing
- [x] Add target-level README describing the JPEG2000 testbed role
- [x] Update ignore rules for generated caches/build artifacts
- [x] Double-check git status for accidental junk
- [x] Commit cleanly
- [x] Push to GitHub
- [x] Rename remote repository to match the broader project scope

## Double-checks
- [x] Root README no longer claims the whole repo is only OpenHTJ2K
- [x] JPEG2000-specific materials live under the target folder
- [x] Skill files are accessible in-repo for Codex/non-Hermes workflows
- [x] Loose crash files are no longer floating at repo root
- [x] Generated caches (`__pycache__`, `.pytest_cache`, build dirs) are not staged
- [x] `git status --short` looks intentional before commit
