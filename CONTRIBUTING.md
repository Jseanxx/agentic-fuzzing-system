# Contributing

Contributions should make the fuzzing workflow more evidence-driven, reviewable, and useful to maintainers.

## Good Contributions

- improve harness engineering while preserving build/smoke/fuzz evidence
- add target profiles or adapter contracts for new native-code projects
- improve crash replay, deduplication, minimization, or reseeding workflows
- clarify documentation so maintainers can understand why a fuzzing result matters
- add tests that prevent unsafe automation, stale evidence, or misleading reports

## Working Style

Before changing a harness or fuzzing workflow, read:

```text
skills/harness-engineering-loop/SKILL.md
targets/jpeg2000-openhtj2k/fuzz-records/current-status.md
targets/jpeg2000-openhtj2k/fuzz-records/progress-index.md
```

Use the four-stage loop:

1. Diagnose the bottleneck from artifacts.
2. Propose one bounded change.
3. Critique the proposal before applying it.
4. Compare expected and actual post-run signal.

Avoid broad rewrites unless the evidence shows that a local fix cannot address the bottleneck.

## Pull Request Checklist

- Describe the security-maintainer problem the change addresses.
- Link or summarize the evidence that motivated the change.
- Keep harness/corpus changes bounded and reversible.
- Include build, smoke, fuzz, replay, or documentation checks when relevant.
- Call out limitations and remaining risk.

## Safety

Do not contribute exploit instructions, unauthorized testing workflows, or changes that encourage scanning systems without permission. Crash artifacts should be treated as security-relevant research material.
