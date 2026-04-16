from __future__ import annotations

import json
from pathlib import Path

from .harness_draft import build_harness_candidate_draft, write_harness_candidate_draft


def _candidate_priority(candidate: dict[str, object]) -> int:
    mode = str(candidate.get("recommended_mode") or "")
    stage = str(candidate.get("target_stage") or "")
    score = 0
    if mode == "parse":
        score += 300
    elif mode == "decode":
        score += 200
    elif mode == "deep-decode":
        score += 100
    if stage.startswith("parse"):
        score += 30
    elif stage.startswith("decode"):
        score += 20
    if candidate.get("entrypoint_path"):
        score += 10
    score += int(candidate.get("viability_score") or 0) * 10
    if str(candidate.get("build_viability") or "") == "high":
        score += 25
    if str(candidate.get("smoke_viability") or "") == "high":
        score += 20
    if str(candidate.get("callable_signal") or "") == "likely-callable":
        score += 15
    return score


def select_top_harness_candidates(draft: dict[str, object], *, limit: int = 2) -> list[dict[str, object]]:
    candidates = draft.get("candidates") if isinstance(draft.get("candidates"), list) else []
    normalized = [candidate for candidate in candidates if isinstance(candidate, dict)]
    normalized.sort(key=lambda candidate: (-_candidate_priority(candidate), str(candidate.get("candidate_id") or "")))
    return normalized[:limit]


def _expected_success_signal(candidate: dict[str, object]) -> str:
    mode = str(candidate.get("recommended_mode") or "exploratory-auto-draft")
    if mode == "parse":
        return "candidate parses at least one valid seed without sanitizer or non-zero exit failures"
    if mode == "decode":
        return "candidate decodes a small valid seed and reaches decode-path logging or normal exit"
    if mode == "deep-decode":
        return "candidate survives a valid deep-path seed through the targeted stage without crashing"
    return "candidate can be built and exercised with one manually reviewed valid input"


def _fail_fast_criteria(candidate: dict[str, object]) -> list[str]:
    return [
        "stop if build assumptions cannot be mapped to an existing target binary or library",
        "stop if no valid baseline seed is available for the candidate entrypoint",
        "stop if smoke execution immediately crashes before reaching the intended stage",
        f"stop if candidate remains ambiguous after manual review of {candidate.get('entrypoint_path')}",
    ]


def _execution_plan(candidate: dict[str, object]) -> list[str]:
    entrypoint = candidate.get("entrypoint_path") or "unknown-entrypoint"
    mode = candidate.get("recommended_mode") or "exploratory-auto-draft"
    return [
        f"Review `{entrypoint}` and confirm it is a callable/parser-facing target worth harnessing.",
        f"Map build assumption `{candidate.get('build_assumption')}` to the concrete binary/library build path.",
        f"Select one valid baseline seed for mode `{mode}` and record the expected normal-exit behavior.",
        "Define a minimal smoke command that runs one input under sanitizer instrumentation before fuzzing.",
        "Only if the smoke run is clean, promote the candidate to harness skeleton generation.",
    ]


def build_harness_evaluation_draft(repo_root: Path) -> dict[str, object]:
    harness_draft = build_harness_candidate_draft(repo_root)
    top_candidates = select_top_harness_candidates(harness_draft)
    evaluations: list[dict[str, object]] = []
    for rank, candidate in enumerate(top_candidates, start=1):
        evaluations.append(
            {
                "rank": rank,
                "candidate_id": candidate.get("candidate_id"),
                "entrypoint_path": candidate.get("entrypoint_path"),
                "target_stage": candidate.get("target_stage"),
                "recommended_mode": candidate.get("recommended_mode"),
                "build_assumption": candidate.get("build_assumption"),
                "smoke_seed_assumption": candidate.get("smoke_seed_assumption"),
                "callable_signal": candidate.get("callable_signal"),
                "build_viability": candidate.get("build_viability"),
                "smoke_viability": candidate.get("smoke_viability"),
                "viability_score": candidate.get("viability_score"),
                "expected_success_signal": _expected_success_signal(candidate),
                "fail_fast_criteria": _fail_fast_criteria(candidate),
                "execution_plan": _execution_plan(candidate),
                "notes": list(candidate.get("notes") or []) + [
                    f"viability-aware selection: score={candidate.get('viability_score')} build={candidate.get('build_viability')} smoke={candidate.get('smoke_viability')}",
                    "low-risk evaluation artifact only; do not auto-generate harness code from this alone",
                ],
            }
        )
    return {
        "generated_from_project": harness_draft.get("generated_from_project"),
        "build_system": harness_draft.get("build_system"),
        "source_candidate_count": harness_draft.get("candidate_count"),
        "evaluation_count": len(evaluations),
        "evaluations": evaluations,
        "harness_draft": harness_draft,
    }


def render_harness_evaluation_markdown(
    draft: dict[str, object],
    *,
    harness_manifest_path: str | None = None,
    harness_plan_path: str | None = None,
    draft_profile_path: str | None = None,
    recon_manifest_path: str | None = None,
) -> str:
    lines = [
        "# Harness Candidate Evaluation Draft",
        "",
        f"- project: {draft.get('generated_from_project')}",
        f"- build_system: {draft.get('build_system')}",
        f"- source_candidate_count: {draft.get('source_candidate_count')}",
        f"- evaluation_count: {draft.get('evaluation_count')}",
        f"- harness_manifest_path: {harness_manifest_path}",
        f"- harness_plan_path: {harness_plan_path}",
        f"- draft_profile_path: {draft_profile_path}",
        f"- recon_manifest_path: {recon_manifest_path}",
        "",
        "## Top Candidates",
        "",
    ]
    for evaluation in draft.get("evaluations") or []:
        if not isinstance(evaluation, dict):
            continue
        lines.extend(
            [
                f"### rank-{evaluation.get('rank')}: {evaluation.get('candidate_id')}",
                f"- entrypoint_path: {evaluation.get('entrypoint_path')}",
                f"- target_stage: {evaluation.get('target_stage')}",
                f"- recommended_mode: {evaluation.get('recommended_mode')}",
                f"- build_assumption: {evaluation.get('build_assumption')}",
                f"- smoke_seed_assumption: {evaluation.get('smoke_seed_assumption')}",
                f"- callable_signal: {evaluation.get('callable_signal')}",
                f"- build_viability: {evaluation.get('build_viability')}",
                f"- smoke_viability: {evaluation.get('smoke_viability')}",
                f"- viability_score: {evaluation.get('viability_score')}",
                f"- expected_success_signal: {evaluation.get('expected_success_signal')}",
                "- fail_fast_criteria:",
            ]
        )
        for item in evaluation.get("fail_fast_criteria") or []:
            lines.append(f"  - {item}")
        lines.append("- execution_plan:")
        for step in evaluation.get("execution_plan") or []:
            lines.append(f"  - {step}")
        lines.append("- notes:")
        for note in evaluation.get("notes") or []:
            lines.append(f"  - {note}")
        lines.append("")
    lines.extend(
        [
            "## Low-Risk Execution Policy",
            "",
            "- Do not auto-generate harness code from this artifact alone.",
            "- Require one manually reviewed valid seed before any smoke execution.",
            "- Stop at the first build or smoke ambiguity and feed the result back into recon/profile refinement.",
            "",
        ]
    )
    return "\n".join(lines)


def write_harness_evaluation_draft(repo_root: Path) -> dict[str, object]:
    harness_result = write_harness_candidate_draft(repo_root)
    draft = build_harness_evaluation_draft(repo_root)
    out_dir = repo_root / "fuzz-records" / "harness-evaluations"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_slug = str(draft.get("generated_from_project") or repo_root.name)
    manifest_path = out_dir / f"{project_slug}-harness-evaluation.json"
    plan_path = out_dir / f"{project_slug}-harness-evaluation.md"
    manifest_payload = {
        **draft,
        "harness_manifest_path": harness_result.get("harness_manifest_path"),
        "harness_plan_path": harness_result.get("harness_plan_path"),
        "draft_profile_path": harness_result.get("draft_profile_path"),
        "recon_manifest_path": harness_result.get("recon_manifest_path"),
    }
    manifest_path.write_text(json.dumps(manifest_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    plan_path.write_text(
        render_harness_evaluation_markdown(
            draft,
            harness_manifest_path=str(harness_result.get("harness_manifest_path")),
            harness_plan_path=str(harness_result.get("harness_plan_path")),
            draft_profile_path=str(harness_result.get("draft_profile_path")),
            recon_manifest_path=str(harness_result.get("recon_manifest_path")),
        ),
        encoding="utf-8",
    )
    return {
        "generated_from_project": draft.get("generated_from_project"),
        "evaluation_count": draft.get("evaluation_count"),
        "evaluation_manifest_path": str(manifest_path),
        "evaluation_plan_path": str(plan_path),
        "harness_manifest_path": str(harness_result.get("harness_manifest_path")),
        "harness_plan_path": str(harness_result.get("harness_plan_path")),
        "draft_profile_path": str(harness_result.get("draft_profile_path")),
        "recon_manifest_path": str(harness_result.get("recon_manifest_path")),
    }
