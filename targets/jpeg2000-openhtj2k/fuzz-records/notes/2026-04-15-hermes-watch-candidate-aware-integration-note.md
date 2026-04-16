# Hermes Watch Upgrade Note — Candidate-Aware Prompt / Bridge / Verification Integration

Date: 2026-04-15

## Why this step
The system could already choose a next candidate from the ranked registry, but that selection did not flow deeply enough into the orchestration prompt, dispatch payload, or verification output. This step threads selected candidate metadata through those paths so the downstream control plane is more candidate-aware.

## What changed
- Extended prompt builders in `scripts/hermes_watch.py`
- Candidate metadata is now included in:
  - refiner subagent prompts
  - refiner cron prompts
  - delegate task request context
  - cronjob request prompt/metadata
  - verification result payloads
- Routing already wrote selected candidate metadata into queue entries; now the later stages can actually consume and expose that context

## Current behavior
This is still conservative and metadata-centric:
- selected candidate context is propagated, not yet deeply reasoned over
- bridge/verification layers can now report which candidate they are acting on
- downstream artifacts are more consistent about candidate identity and chosen entrypoint

## Important limitation
This is not yet candidate-aware execution intelligence.
It does not yet:
- make bridge launch prompts adapt behavior based on candidate debt/state
- make verification policy decisions candidate-aware
- use candidate metadata to alter execution commands or safety limits dynamically
- tie candidate selection directly to crash novelty or coverage value

## Why this matters
This closes an important gap in the control plane. Before this step, candidate selection happened upstream but execution/verification layers were still relatively candidate-blind. Now the selected candidate identity is carried further through the lifecycle, which reduces ambiguity and sets up the next step toward a true candidate-aware scheduler.

## Recommended next step
- make scheduling and verification policy candidate-aware rather than action-only
- then enrich candidate metadata with debt dimensions and use them in selection/execution decisions
